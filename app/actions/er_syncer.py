import logging
from datetime import datetime, timedelta
from app.actions.configurations import AuthenticateConfig, SyncEventsConfig
from app.services.errors import ConfigurationNotFound, ConfigurationValidationError
from erclient import ERClient, ERClientException
import pytz
import tempfile
import json
import dateparser
from shapely.geometry import shape
from typing import List, Dict

class er_syncer:

    SYNC_FIELDS_EVENTS = ['id', 'location', 'time', 'event_type',
        'priority', 'title', 'state', 'event_details', 'is_collection', 'geometry', 'geojson']
    SYNC_FIELDS_EVENT_TYPES = ['value', 'display', 'ordernum', 'icon_id', 'is_active', 'schema', 'properties',
                               'category', 'is_collection', 'geometry_type']


    def __init__(self, auth_config: AuthenticateConfig, action_config: SyncEventsConfig):
        self.action_config = action_config
        self.auth_config = auth_config

        try:
            self.src_erclient = ERClient(service_root=auth_config.source_server, token = auth_config.source_token.get_secret_value())
        except Exception as e:
            logging.exception(f"Could not log in to source client", e)
            raise e
        
        try:
            self.dest_erclient = ERClient(service_root=auth_config.dest_server, token = auth_config.dest_token.get_secret_value())
        except Exception as e:
            logging.exception(f"Could not log in to destination client", e)
            raise e
        
    def sync(self, start_date):
        logging.info(f"Syncing events since '{start_date}' from '{self.src_erclient.service_root}' to '{self.dest_erclient.service_root}'")

        source_events = self._get_events(since = start_date, erclient = self.src_erclient,
            include_event_types = None, within_featuregroups = self.action_config.within_featuregroups,
            priorities = self.action_config.matching_priorities, state = self.action_config.matching_states)

        event_types_to_sync = []
        events_to_sync = []

        # Create a list of the unique event types that we're going to sync from source
        for event in source_events:
            if(event['event_type'] not in event_types_to_sync):
                event_types_to_sync.append(event['event_type'])
            events_to_sync.append(event)

        logging.info(f"Loaded {len(events_to_sync)} events to consider.")

        if(len(events_to_sync) > 0):
            logging.info(f"Found '{len(events_to_sync)}' events to sync from source site '{self.src_erclient.service_root}'")
            self.dest_event_types = {}
            if(len(event_types_to_sync) > 0):
                if(self.action_config.update_schema or self.action_config.create_schema):
                    logging.info("Syncing event categories...")
                    self.sync_event_categories()
                    logging.info("Syncing event types...")
                    self.dest_event_types = self.sync_event_types(event_types_to_sync)
                else:
                    logging.info("Get destination event types...")
                    self.dest_event_types = self._get_event_types(event_types_to_sync, self.dest_erclient)

                    for et_k in event_types_to_sync:
                        dest_event_type = et_k
                        if(self.prepend_system_to_event_types):
                            dest_event_type = self.action_config.source_system_abbr + "_" + dest_event_type
                        if(dest_event_type not in self.dest_event_types):
                            raise ConfigurationValidationError(f"update_schema is false, but event type {dest_event_type} is missing from destination.")
                        for prop in ["er2er_src_id", "er2er_src_serial_number", "er2er_src_system", "er2er_src_service_root"]:
                            et = self.dest_event_types[dest_event_type]
                            if(prop not in et['schema'].get('schema',{}).get('properties', {})):
                                raise ConfigurationValidationError(
                                    f"update_schema is false, but event type {dest_event_type} is missing required property {prop}")

            logging.info(f"Syncing {len(events_to_sync)} events from source site {self.src_erclient.service_root} to destination site {self.dest_erclient.service_root}. Start date: {start_date}")
            self._sync_events(source_events = events_to_sync, start_date = start_date)

    def sync_event_types(self, event_types_to_sync:List):

        logging.info("Loading event type schemas")
        source_event_types = self._get_event_types(event_types_to_sync, self.src_erclient)

        logging.info(f"Found {len(source_event_types)} event types from source site {self.src_erclient.service_root}")

        # Grab the existing event types that match the source event types, if any
        dest_event_types_to_sync = []
        for event_type in event_types_to_sync:
            dest_event_type = event_type
            if(self.action_config.prepend_system_to_event_types):
                dest_event_type = self.action_config.source_system_abbr + "_" + dest_event_type
            dest_event_type = dest_event_type.lower()

            if(dest_event_type not in dest_event_types_to_sync):
                dest_event_types_to_sync.append(dest_event_type)

        dest_event_types = self._get_event_types(dest_event_types_to_sync, self.dest_erclient)

        logging.info(f"Found {len(dest_event_types)} event types from destination site {self.dest_erclient.service_root}")

        result_types = {}
        for event_type_name, event_type in source_event_types.items():

            if(event_type_name not in event_types_to_sync):
                logging.info(f"Skipping event type {event_type_name} because it's not in the list of event types to sync")
                continue

            new_event_type = self.clean_event_type(event_type)
            try:
                if(new_event_type['value'] in dest_event_types):
                    if(self.action_config.update_schema):
                        dest_event_type = dest_event_types[new_event_type['value']]                        
                        if(not self._compare_schemas(dest_event_type['schema']['schema'], json.loads(new_event_type['schema'])['schema'])):
                            logging.info(f"Updating destination event type {new_event_type['value']} from source event type {event_type_name}")
                            new_event_type['id'] = dest_event_type["id"]
                            result_types[new_event_type['value']] = self.dest_erclient.patch_event_type(new_event_type)
                elif(self.action_config.create_schema):
                    logging.info(f"Creating destination event type {new_event_type['value']} from source event type {event_type_name}")
                    result_types[new_event_type['value']] = self.dest_erclient.post_event_type(new_event_type)
            except ERClientException as e:
                logging.exception(f"Error while creating event type {new_event_type['value']} in destination '{self.dest_erclient.service_root}'.  Exception: {e}. User: {self.dest_erclient.username}. Skipping creation...")
                continue

        return result_types

    @staticmethod
    def _compare_schemas(schema1, schema2):

        for k in schema1.keys():
            if(k in ['id', 'image_url']):
                continue
            if k not in schema2:
                return False
            if(schema1[k] != schema2[k]):
                return False

        for k in schema2.keys():
            if k not in schema1:
                return False            
                    
        return True

    @staticmethod
    def _load_feature_group(feature_group: str, erclient: ERClient):
        objs = list(erclient.get_objects(object=f"spatialfeaturegroup/{feature_group}"))
        return objs[0]

    @staticmethod
    def _get_events(since: datetime, erclient: ERClient, include_event_types: List[str] = [],
                         within_featuregroups: List[str] = [], priorities: List[int] = None,
                         state: List[str] = None):

        filter = {}
        if(since != None):
            tomorrow = datetime.now(tz=pytz.utc) + timedelta(days=1)
            filter = {
                'update_date' : {
                    'lower': since.strftime("%Y-%m-%dT%H:%M:%S%z")
                }
            }

        if(priorities):
            filter['priority'] = priorities

        event_type_ids = er_syncer._get_event_type_ids(erclient, include_event_types)
        if(not event_type_ids):
            event_type_ids = [None] # Ensures that it gets executed for all event types

        containing_shapes = []
        if(within_featuregroups):
            for fg in within_featuregroups:
                logging.info(f"Loading feature group {fg} to filter events.")
                
                try:
                    featuregroup = er_syncer._load_feature_group(fg, erclient)
                except (ERClientException, IndexError) as e:
                    logging.error(f"Could not load feature group {fg}: {e}")
                    raise ConfigurationValidationError(f"Could not load feature group {fg}.\nTroubleshoot by looking for this feature group in the ER system {erclient.service_root}.")
                
                for erfeature in featuregroup.get("features", []):
                    for geojsonfeature in erfeature.get("features", []):
                        if("geometry" in geojsonfeature):
                            polygon = shape(geojsonfeature["geometry"])
                            containing_shapes.append(polygon)

        for event_type_id in event_type_ids:
            if(event_type_id):
                filter['event_type'] = [event_type_id]

            msg = f"Loading events since {since.strftime('%Y-%m-%dT%H:%M:%S%z')} from {erclient.service_root} of type {event_type_id}. "
            if(within_featuregroups):
                msg += f"Restricting events to those within feature groups {within_featuregroups}."
            if(priorities):
                msg += f" Restricting events to priorities {priorities}."
            if(state):
                msg += f" Restricting to states {state}."
            logging.info(msg)
            events = erclient.get_objects_multithreaded(object="activity/events",
                filter = json.dumps(filter),
                include_notes = True,
                state = state,
                include_related_events = False,
                include_files = True,
                include_details = True,
                include_updates = False,
                page_size = 100)

            if(not within_featuregroups):
                yield from events
            else:
                for e in events:
                    if('geojson' not in e) or not e['geojson']:
                        continue
                    event_geom = e['geojson'].get('geometry')
                    if not event_geom:
                        continue
                    event_geom = shape(event_geom)
                    for s in containing_shapes:
                        if s.intersects(event_geom):
                            yield e
                            break

    @staticmethod
    def _get_event_type_ids(erclient, event_types: List[str]) -> List[str]:
        if(not event_types):
            return []

        er_event_types = erclient.get_event_types()

        results = []
        for event_type in er_event_types:
            if(event_type and (event_type.get('value') in event_types)):
                results.append(event_type['id'])

        return results
    
    def sync_event_categories(self):

        source_cats = self._get_event_categories(self.src_erclient)
        logging.info(f"Found {len(source_cats)} event categories from source site {self.src_erclient.service_root}")

        dest_cats = self._get_event_categories(self.dest_erclient)
        logging.info(f"Found {len(dest_cats)} event categories from destination site {self.dest_erclient.service_root}")

        # For all source categories, if the destination category doesn't already exist, create it.
        # If it does already exist, update it.
        for cat in source_cats:
            dest_cat_value = cat
            if(self.action_config.prepend_system_to_categories):
                dest_cat_value = self.action_config.source_system_abbr + "_" + dest_cat_value

            if(dest_cat_value not in dest_cats):
                if(self.action_config.create_schema):
                    new_cat = self.create_dest_category(source_cats[cat])
                    if new_cat:
                        dest_cats[new_cat['value']] = new_cat

            elif(self.action_config.update_schema):
                self.update_dest_category(dest_cats[dest_cat_value], source_cats[cat])

    def create_dest_category(self, cat):
        new_cat = {
            "value": cat['value'],
            "display": cat['display']
        }
        if(self.action_config.prepend_system_to_categories):
            new_cat["value"] = self.action_config.source_system_abbr + "_" + new_cat["value"]
            new_cat["display"] = self.action_config.source_system_name + "-" + new_cat["display"]

        logging.info(f"Creating destination category {new_cat['value']} from source category {cat['value']}")
        new_er_cat = self.dest_erclient.post_event_category(new_cat)
        return new_er_cat

    def update_dest_category(self, dest_cat, src_cat):
        new_cat = {
            "id": dest_cat['id'],
            "value": src_cat['value'],
            "display": src_cat['display']
        }

        if(self.action_config.prepend_system_to_categories):
            new_cat["value"] = self.action_config.source_system_abbr + "_" + new_cat["value"]
            new_cat["display"] = self.action_config.source_system_name + "-" + new_cat["display"]

        if((dest_cat["value"] == new_cat["value"]) and (dest_cat["display"] == new_cat["display"])):
            logging.debug(f"Destination category {dest_cat['value']} hasn't changed.  Skipping.")
            return dest_cat

        logging.info(f"Updating destination category {dest_cat['value']} from source category {src_cat['value']}")
        new_er_cat = self.dest_erclient.patch_event_category(new_cat)
        return new_er_cat

    @staticmethod
    def _get_event_categories(erclient) -> Dict:
        cats = erclient.get_event_categories()
        ret_cats = {}
        for cat in cats:
            ret_cats[cat['value']] = cat
        return ret_cats
    
    @staticmethod
    def get_incident_map(events: List[Dict]) -> Dict[str, List[str]]:
        incident_map = {}
        for event in events:
            if('is_contained_in' not in event):
                continue

            for container in event['is_contained_in']:
                if(container['type'] != 'contains'):
                    continue

                serial = container['related_event']['id']
                if(serial not in incident_map):
                    incident_map[serial] = []

                incident_map[serial].append(event['id'])

        return incident_map

    @staticmethod
    def _get_event_type_schema(event_type_value, erclient):
        return erclient._get(f"activity/events/schema/eventtype/{event_type_value}")

    ## Get all of the event type schema definitions
    @staticmethod
    def _get_event_types(event_types_to_sync: List, erclient:ERClient):

        # Grabs all event types
        er_event_types = erclient.get_event_types()

        # For each event type, also grab the full schema
        er_event_map = {}
        for er_event_type in er_event_types:
            if(er_event_type['value'] in event_types_to_sync):
                er_event_type['schema'] = er_syncer._get_event_type_schema(er_event_type['value'], erclient)
                er_event_map[er_event_type['value']] = er_event_type

        return er_event_map

    def _sync_events(self, *, source_events: List, start_date: datetime):

        dest_events = self._get_events(since = start_date, erclient = self.dest_erclient,
            include_event_types = self.dest_event_types.keys())
        dest_events_sources = self._get_dest_event_sources(dest_events)

        # For each event we're syncing, if the event already exists in the destination
        # system, create it.  Otherwise, if the destination event has not been updated
        # since the last time the source event has been, update the destination event.
        all_source_events = []
        dest_unmatched = dest_events_sources.copy()
        for source_event in source_events:
            # check if "event_details" is None
            if source_event.get('event_details', None) is None:
                source_event['event_details'] = {}

            all_source_events.append(source_event)

            if(source_event['event_details'].get('er2er_src_service_root') == self.dest_erclient.service_root):
                logging.debug(f"Event {source_event['serial_number']} originates from {self.dest_erclient.service_root} event {source_event['event_details'].get('er2er_src_serial_number')}.  Skipping to avoid a loop.")
                continue

            if(source_event['id'] not in dest_events_sources.keys()):
                dest_event = self._lookup_dest_event(src_event = source_event)
                if(dest_event):
                    dest_events_sources[source_event['id']] = dest_event[0]

            if(source_event['id'] not in dest_events_sources.keys()):
                try:
                    new_event = self.create_dest_event(source_event)
                except ERClientException as e:
                    logging.exception(f"Error while creating event {source_event['id']} in destination '{self.dest_erclient.service_root}'.  Exception: {e}. User: {self.dest_erclient.username}. Skipping creation...")
                else:
                    dest_events_sources[new_event['event_details']['er2er_src_id']] = new_event

            else:
                if(source_event['id'] in dest_unmatched):
                    del dest_unmatched[source_event['id']]
                source_event_update_time = dateparser.parse(source_event['updated_at'])
                dest_event_update_time = dateparser.parse(dest_events_sources[source_event['id']]['updated_at'])

                if(dest_event_update_time > source_event_update_time):
                    logging.debug(f"Event {dest_events_sources[source_event['id']]['id']}: Destination has been updated more recently than source. {dest_event_update_time} vs {source_event_update_time}")
                    continue

                self.update_dest_event(dest_events_sources[source_event['id']], source_event)

        ## Now to deal with incidents...
        src_incident_map = self.get_incident_map(all_source_events)
        dest_incident_map = self.get_incident_map(dest_events_sources.values())

        for k, src_events in src_incident_map.items():

            for src_event in reversed(src_events):

                dest_incident = dest_events_sources.get(k)

                if not dest_incident:
                    logging.warning('Destination Incident is not found for src_event %s', src_event)
                    continue

                dest_event = dest_events_sources.get(src_event, None)

                if not dest_event:
                    logging.warning('Destination Event is not found for src_event %s', src_event)
                    continue

                # If this mapping already exists, check it off (remove it from the map)
                if(dest_incident['id'] in dest_incident_map and
                    dest_event['id'] in dest_incident_map[dest_incident['id']]):

                    events = dest_incident_map[dest_incident['id']].copy()
                    events.remove(dest_event['id'])
                    dest_incident_map[dest_incident['id']] = events
                    continue

                # If the mapping doesn't exist, create it
                logging.info(f"Adding destination event {dest_event['id']} to destination incident {dest_incident['id']}")
                self.dest_erclient.add_event_to_incident(dest_event['id'], dest_incident['id'])

        if(self.action_config.delete_unmatched_events):
            # For any events that weren't handled by the create or update, we assume
            # they no longer exist in the source and should be removed here as well
            for dest_event in dest_unmatched.values():
                logging.info(f"Deleting destination event {dest_event['id']} - There is no source match")
                self.dest_erclient.delete_event(dest_event['id'])
                if(dest_event['id'] in dest_incident_map):
                    del dest_incident_map[dest_event['id']]

            # Same with incident associations - If the events are no longer associated
            # in the source, remove the association in the destination.
            for dest_incident_serial in dest_incident_map.keys():
                for dest_event_serial in dest_incident_map[dest_incident_serial]:
                    dest_event = dest_events_sources.get(dest_event_serial, None)
                    dest_incident = dest_events_sources.get(dest_incident_serial, None)
                    if dest_event and dest_incident:
                        logging.info(f"Removing destination event {dest_event['id']} from destination incident {dest_incident['id']} - No such relation exists in the source system")
                        self.dest_erclient.remove_event_from_incident(self, dest_event['id'], dest_incident['id'])
                    else:
                        logging.warning(f"Could not find destination event {dest_event_serial} or destination incident {dest_incident_serial} to remove association")

    def _get_dest_event_sources(self, events: List[Dict]) -> Dict:
        sources = {}

        for event in events:
            id = event['event_details'].get('er2er_src_id', None)
            sys = event['event_details'].get('er2er_src_system', None)
            if(id and (sys == self.action_config.source_system_abbr)):
                sources[id] = event
        return sources

    ## Looks up a specific event in the destination system using an event from the source system
    def _lookup_dest_event(self, *, src_event: Dict):

        ## See if we can find it directly
        events = list(self.dest_erclient.get_events(event_ids=[src_event['id']]))

        if(events):
            logging.debug(f"Found {len(events)} specific event (first: {events[0]['serial_number']}) to match source event {src_event['id']}")

        return events

    ## Converts an event from the source system to a representation appropriate
    ## for the destination system.
    def clean_event(self, event: Dict):

        new_event = dict((k, v) for k, v in event.items() if k in self.SYNC_FIELDS_EVENTS)

        # Add the source system name to the event type
        if(self.action_config.prepend_system_to_event_types):
             new_event['event_type'] = self.action_config.source_system_abbr + "_" + new_event['event_type']
        new_event['event_type'] = new_event['event_type'].lower()

        if (self.action_config.prepend_system_to_event_titles):
            dest_event_type = self.dest_event_types.get(new_event['event_type'])
            if(not dest_event_type):
                ### In theory this shouldn't happen
                logging.error(f"Could not find target destination event type {new_event.get('event_type')}")

            else:
                new_title = None
                if(new_event.get("title")):
                    new_title = self.action_config.source_system_name + "-" + new_event.get("title")
                    if(new_title == dest_event_type.get("display")):
                        new_title = None
                elif(not dest_event_type.get("display","").startswith(self.action_config.source_system_name + "-")):
                    new_title = self.action_config.source_system_name + "-" + dest_event_type.get("display")

                new_event['title'] = new_title

        else:
            # [2023-01-09 JL] Opted not to handle this for now, since it's not really clear what should be done in this
            # case.  We'll just keep the original title.  The scenario that could be confusing is if
            # prepend_system_to_event_types is true, but prepend_system_to_event_titles is false.  If an event doesn't
            # have a title, it'll default to the name of the event type, which in this case will include the system
            # name, despite the setting that it shouldn't prepend the system name.
            pass

        # If no title, remove the value from the dict (otherwise the API fails)
        if(not new_event.get('title')):
            new_event.pop('title', None)

        # Store the source event's serial number so that we can match the new event to
        # the source event in the future
        new_event['event_details']['er2er_src_id'] = event['id']
        new_event['event_details']['er2er_src_serial_number'] = event['serial_number']
        new_event['event_details']['er2er_src_system'] = self.action_config.source_system_abbr
        new_event['event_details']['er2er_src_service_root'] = self.src_erclient.service_root

        return new_event

    def clean_event_type(self, event_type):
        new_event_type = dict((k, v) for k, v in event_type.items() if k in self.SYNC_FIELDS_EVENT_TYPES)
        new_event_type['schema']['schema'] = self.clean_event_schema(schema=new_event_type['schema']['schema'], event_type=new_event_type['value'])
        new_event_type['schema'] = json.dumps(new_event_type['schema'], indent=4)

        # Prepend the name of the system to the event type
        if(self.action_config.prepend_system_to_event_types):
            new_event_type['value'] = self.action_config.source_system_abbr + "_" + new_event_type['value']
            new_event_type['display'] = self.action_config.source_system_name + "-" + new_event_type['display']
        new_event_type['value'] = new_event_type['value'].lower()

        new_event_type['category'] = new_event_type['category']['value']
        if(self.action_config.prepend_system_to_categories):
            new_event_type['category'] = self.action_config.source_system_abbr + "_" + new_event_type['category']

        return new_event_type
    
    def clean_event_schema(self, schema=None, event_type=None):

        schema['properties']['er2er_src_id'] = {
            "type": "string",
            "title": "Event Type Serial Number from Source ER System"
        }

        schema['properties']['er2er_src_system'] = {
            "type": "string",
            "title": "Name of Source ER System"
        }

        schema['properties']['er2er_src_serial_number'] = {
            "type": "string",
            "title": "Serial Number of Source Event"
        }

        schema['properties']['er2er_src_service_root'] = {
            "type": "string",
            "title": "Service Root of Source Event"
        }

        for prop_name, prop in schema['properties'].items():
            if('enumNames' in prop and isinstance(prop['enumNames'], list)):
                logging.warning('Source schema for event type %s has enumNames as a list.  Converting to dict.', event_type)
                prop['enumNames'] = dict( (v,v) for v in prop['enumNames'] )

        schema['readonly'] = True

        return schema



    ## Creates an event in the destination system based on an event from the
    ## source system
    def create_dest_event(self, src_event):
        new_event = self.clean_event(src_event)
        dest_event = self.dest_erclient.post_event(new_event)
        logging.info(f"Created destination event {dest_event['serial_number']} from source event {src_event['serial_number']} ({src_event['id']})")

        self.copy_notes_between_events(src_event, dest_event)
        self.copy_files_between_events(src_event, dest_event)

        return dest_event


    ## For each file attached to the input event from the source system,
    ## download it from the source syste, and upload it to the destination system
    def copy_files_between_events(self, src_event: Dict, dest_event: Dict):

        files = src_event.get("files")
        if(len(files) > 0):
            tmpdir = tempfile.TemporaryDirectory()

            # Loop in reverse order so that the result is in the same temporal order
            for i in range(len(files)-1, -1, -1):
                file = src_event['files'][i]
                logging.info(f"Adding attachment {file['filename']} from source ER event {src_event['id']} to destination ER event {dest_event['id']}")
                tmppath = tmpdir.name + "/" + file['filename']
                result = self.src_erclient.get_file(file['url'])
                open(tmppath, 'wb').write(result.content)
                self.dest_erclient.post_event_file(dest_event['id'], tmppath)

            tmpdir.cleanup()

    ## Removes all of the files from the input destination event
    def remove_files_from_event(self, event):
        files = event.get("files")
        if(len(files) > 0):
            for file in files:
                logging.info(f"Removing attachment {file['filename']} from destination event {event['id']}")
                self.dest_erclient.delete_event_file(event['id'], file['id'])

    ## Copies all of the notes from the source event to the destination event
    def copy_notes_between_events(self, src_event: Dict, dest_event: Dict):

        notes = src_event.get("notes")
        if(len(notes) > 0):
            logging.info(f"Adding notes from source event {src_event['id']} to destination event {dest_event['id']}")
            new_notes = []

            # Loop in reverse order so that the result is in the same temporal order
            for i in range(len(notes)-1, -1, -1):
                new_notes.append(notes[i].get('text'))
            self.dest_erclient.post_event_note(dest_event['id'], new_notes)

    ## Updates a destination event, overwriting all of its attributes, files and
    ## comments with the ones from the source event
    def update_dest_event(self, dest_event, src_event):
        new_event = self.clean_event(src_event)
        new_event['id'] = dest_event['id']

        logging.info(f"Updating destination event {dest_event['id']} from source event {src_event['id']}")
        self.dest_erclient.patch_event(new_event['id'], new_event)

        self.remove_files_from_event(dest_event)
        self.copy_files_between_events(src_event, dest_event)

        self.remove_notes_from_event(dest_event)
        self.copy_notes_between_events(src_event, dest_event)
    
        ## Removes all of the notes from the input destination event
    def remove_notes_from_event(self, event: Dict):

        if(len(event.get("notes", [])) > 0):
            logging.info(f"Removing notes from destination event {event['id']}")

            for note in event.get("notes"):
                self.dest_erclient.delete_event_note(event['id'], note['id'])
