import pytest
from unittest.mock import MagicMock
from app.actions.configurations import AuthenticateConfig, SyncEventsConfig

@pytest.fixture
def source_event_categories():
    return [
        {
            'id': 'ef230385-5afc-40d1-ad07-c811f6da2b3c',
            'value': 'analyzer_cat',
            'display': 'Analyzers',
            'is_active': True,
            'ordernum': 1.0,
            'flag': 'system',
            'permissions': ['create', 'delete', 'read', 'update']
        }
    ]

@pytest.fixture
def destination_event_categories():
    return [
        {
            'id': 'ef230385-5afc-40d1-ad07-c811f6da2b3c',
            'value': 'from_analyzer_cat',
            'display': 'From-Analyzers',
            'is_active': True,
            'ordernum': 1.0,
            'flag': 'system',
            'permissions': ['create', 'delete', 'read', 'update']
        }
    ]

@pytest.fixture
def modified_event_categories():
    return [
        {
            'id': 'ef230385-5afc-40d1-ad07-c811f6da2b3c',
            'value': 'analyzer_cat',
            'display': 'Changed!',
            'is_active': True,
            'ordernum': 1.0,
            'flag': 'system',
            'permissions': ['create', 'delete', 'read', 'update']
        }
    ]

@pytest.fixture
def sample_action_config():
    return SyncEventsConfig(source_system_abbr = "from",
                     source_system_name = "From",
                     matching_states = None,
                     prepend_system_to_event_titles = True,
                     create_schema = True,
                     update_schema = True,
                     prepend_system_to_categories = True,
                     prepend_system_to_event_types = True,
                     delete_unmatched_events = True,
                     within_featuregroups = None,
                     matching_priorities = None,
                     matching_detail_values = None,
                     days_to_sync = 1
                     )

@pytest.fixture
def sample_auth_config():
    return AuthenticateConfig(
        dest_server = "https://destination.pamdas.org",
        dest_token = "somefaketoken",
        source_server = "https://source.pamdas.org",
        source_token = "someotherfaketoken"
    )

@pytest.fixture
def empty_response():
    return []

@pytest.fixture
def sample_event_type():
    return {
        'id': '6c90e5f5-ae8e-4e7f-a8dd-26e5d2909a74',
        'has_events_assigned': True,
        'icon': 'accident_rep',
        'value': 'accident_rep',
        'display': 'Accident',
        'ordernum': 1.0,
        'is_collection': False,
        'category': {'id': '007a45d3-2aba-4ed1-b3fc-e09fc0ad41f8',
        'value': 'security',
        'display': 'Security',
        'is_active': True,
        'ordernum': 1.0,
        'flag': 'user',
        'permissions': ['create', 'delete', 'read', 'update']},
        'icon_id': 'accident_rep',
        'is_active': True,
        'default_priority': 300,
        'default_state': 'new',
        'geometry_type': 'Point',
        'resolve_time': None,
        'auto_resolve': False,
        'url': 'https://easterisland.pamdas.org/api/v1.0/activity/events/eventtypes/6c90e5f5-ae8e-4e7f-a8dd-26e5d2909a74'}

@pytest.fixture
def sample_event_schema():
    return {
        'schema': {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'title': 'EventType Test Data',
            'type': 'object',
            'properties': {
                'type_accident': {
                    'type': 'string',
                    'title': 'Type',
                    'required': 'true'},
                'number_people_involved': {
                    'type': 'number',
                    'title': 'Number of people involved',
                    'minimum': 0},
                'animals_involved': {'type': 'string', 'title': 'Animals involved'},
                'hospitalisation': {'type': 'string',
                    'title': 'Type of species',
                    'enum': [],
                    'enumNames': {}
                }
            },
            'id': 'https://easterisland.pamdas.org/api/v1.0/activity/events/schema/eventtype/accident_rep',
            'icon_id': 'accident_rep',
            'image_url': 'https://easterisland.pamdas.org/static/accident-black.svg'
        },
        'definition': [
            {'key': 'type_accident', 'htmlClass': 'col-lg-6'},
            {'key': 'number_people_involved', 'htmlClass': 'col-lg-6'},
            {'key': 'animals_involved', 'htmlClass': 'col-lg-6'},
            {'key': 'hospitalisation', 'htmlClass': 'col-lg-6'}]
    }

@pytest.fixture
def destination_event_type():
    return {
        'id': '6c90e5f5-ae8e-4e7f-a8dd-26e5d2909a74',
        'has_events_assigned': True,
        'icon': 'accident_rep',
        'value': 'from_accident_rep',
        'display': 'From-Accident',
        'ordernum': 1.0,
        'is_collection': False,
        'category': {'id': '007a45d3-2aba-4ed1-b3fc-e09fc0ad41f8',
        'value': 'security',
        'display': 'Security',
        'is_active': True,
        'ordernum': 1.0,
        'flag': 'user',
        'permissions': ['create', 'delete', 'read', 'update']},
        'icon_id': 'accident_rep',
        'is_active': True,
        'default_priority': 300,
        'default_state': 'new',
        'geometry_type': 'Point',
        'resolve_time': None,
        'auto_resolve': False,
        'url': 'https://easterisland.pamdas.org/api/v1.0/activity/events/eventtypes/6c90e5f5-ae8e-4e7f-a8dd-26e5d2909a74'}

@pytest.fixture
def modified_event_schema():
    return {
        'schema': {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'title': 'EventType Test Data',
            'type': 'object',
            'properties': {
                'changed!': {
                    'type': 'string',
                    'title': 'Type',
                    'required': 'true'},
                'number_people_involved': {
                    'type': 'number',
                    'title': 'Number of people involved',
                    'minimum': 0},
                'animals_involved': {'type': 'string', 'title': 'Animals involved'},
                'hospitalisation': {'type': 'string',
                    'title': 'Type of species',
                    'enum': [],
                    'enumNames': {}
                }
            },
            'id': 'https://easterisland.pamdas.org/api/v1.0/activity/events/schema/eventtype/accident_rep',
            'icon_id': 'accident_rep',
            'image_url': 'https://easterisland.pamdas.org/static/accident-black.svg'
        },
        'definition': [
            {'key': 'type_accident', 'htmlClass': 'col-lg-6'},
            {'key': 'number_people_involved', 'htmlClass': 'col-lg-6'},
            {'key': 'animals_involved', 'htmlClass': 'col-lg-6'},
            {'key': 'hospitalisation', 'htmlClass': 'col-lg-6'}]
    }

@pytest.fixture
def sample_modified_event_type(sample_event_type):
    return {
        'id': '6c90e5f5-ae8e-4e7f-a8dd-26e5d2909a74',
        'has_events_assigned': True,
        'icon': 'accident_rep',
        'value': 'accident_rep',
        'display': 'Accident',
        'ordernum': 1.0,
        'is_collection': False,
        'category': {'id': '007a45d3-2aba-4ed1-b3fc-e09fc0ad41f8',
        'value': 'security',
        'display': 'Changed!',
        'is_active': True,
        'ordernum': 1.0,
        'flag': 'user',
        'permissions': ['create', 'delete', 'read', 'update']},
        'icon_id': 'accident_rep',
        'is_active': True,
        'default_priority': 300,
        'default_state': 'new',
        'geometry_type': 'Point',
        'resolve_time': None,
        'auto_resolve': False,
        'url': 'https://easterisland.pamdas.org/api/v1.0/activity/events/eventtypes/6c90e5f5-ae8e-4e7f-a8dd-26e5d2909a74'}

@pytest.fixture
def sample_events():
    return [
        {
            'id': '805beb0b-7b19-4aae-a6f3-73625e54ed87',
            'location': {'latitude': -27.074817163943457, 'longitude': -109.34291883508149},
            'time': '2025-04-16T08:09:04.760000-07:00',
            'event_type': 'carcass_rep',
            'priority': 300,
            'title': 'Test FLB',
            'state': 'new',
            'geojson': {'type': 'Feature',
                'geometry': {'type': 'Point',
                    'coordinates': [-109.34291883508149, -27.074817163943457]},
                'properties': {}
            },
            'event_details': {'carcassrep_sex': 'female', 'carcassrep_species': 'bongo', 'carcassrep_ageofanimal': 'juvenile', 'carcassrep_ageofcarcass': 'within_a_month'}
        },
        {
            'id': 'e5e7c28d-7661-484a-85a2-0e108f49e59c',
            'location': {'latitude': 51.065691, 'longitude': 0.712173},
            'time': '2025-04-16T02:39:43-07:00',
            'event_type': 'snare_rep',
            'priority': 100,
            'title': None,
            'state': 'new',
            'geojson': {'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [0.712173, 51.065691]},
                'properties': {}
            },
            'event_details': {'snarerep_action': 'ambushed', 'snarerep_status': 'set', 'snarerep_comments': 'Running', 'snarerep_numberofsnares': 2},
        },
        {
            'id': '09e0f56e-bf55-4fdd-9b72-38c9770e1f54',
            'location': None,
            'time': '2025-04-15T21:03:02.247245-07:00',
            'event_type': 'incident_collection',
            'priority': 0,
            'title': 'Elephant Poaching',
            'state': 'active',
            'geojson': None,
            'event_details': {},
        },
        {
            'id': 'aef7186c-b2fb-4282-ad5b-c7d8a6a116a5',
            'location': {'latitude': -27.138423, 'longitude': -109.344601},
            'time': '2025-04-15T06:24:17.552340-07:00',
            'event_type': 'inaturalist',
            'priority': 200,
            'title': 'iNaturalist - Pangolin',
            'state': 'resolved',
            'geojson': {'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [-109.344601, -27.138423]},
                'properties': {}
            },
            'event_details': {'captive': 'FALSE', 'inat_id': 41712632.0, 'user_id': 704765.0, 'inat_url': 'https://www.inaturalist.org/observations/41712632',
                'taxon_id': 75083.0, 'place_ids': '68959, 7134, 97392', 'user_name': 'jeslefcourt', 'created_at': '2020-04-08T13:50:00.00Z', 'taxon_name': 'Smutsia temminckii',
                'taxon_rank': 'Species', 'updated_at': '2020-04-08T13:50:00.00Z', 'place_guess': 'Gorongosa National Park', 'quality_grade': 'Research',
                'species_guess': "Temminck's Ground Pangolin", 'taxon_ancestors': '75083, 71921, 43358, 43357, 848324, 848320, 848317, 40151, 355675, 2, 1',
                'location_obscured': 'TRUE', 'taxon_common_name': "Temminck's Ground Pangolin", 'taxon_wikipedia_url': 'https://en.wikipedia.org/wiki/Ground_pangolin',
                'taxon_conservation_status': 'Vulnerable'},
            'files': [{'id': '3c17b152-6ca4-480d-aaa9-019e9d86e1f9',
                'url': 'https://easterisland.pamdas.org/api/v1.0/activity/event/aef7186c-b2fb-4282-ad5b-c7d8a6a116a5/file/3c17b152-6ca4-480d-aaa9-019e9d86e1f9/',
                'images': {'original': 'https://easterisland.pamdas.org/api/v1.0/activity/event/aef7186c-b2fb-4282-ad5b-c7d8a6a116a5/file/3c17b152-6ca4-480d-aaa9-019e9d86e1f9/original/pangolin.jpg',
                'icon': 'https://easterisland.pamdas.org/api/v1.0/activity/event/aef7186c-b2fb-4282-ad5b-c7d8a6a116a5/file/3c17b152-6ca4-480d-aaa9-019e9d86e1f9/icon/pangolin.jpg',
                'thumbnail': 'https://easterisland.pamdas.org/api/v1.0/activity/event/aef7186c-b2fb-4282-ad5b-c7d8a6a116a5/file/3c17b152-6ca4-480d-aaa9-019e9d86e1f9/thumbnail/pangolin.jpg',
                'large': 'https://easterisland.pamdas.org/api/v1.0/activity/event/aef7186c-b2fb-4282-ad5b-c7d8a6a116a5/file/3c17b152-6ca4-480d-aaa9-019e9d86e1f9/large/pangolin.jpg',
                'xlarge': 'https://easterisland.pamdas.org/api/v1.0/activity/event/aef7186c-b2fb-4282-ad5b-c7d8a6a116a5/file/3c17b152-6ca4-480d-aaa9-019e9d86e1f9/xlarge/pangolin.jpg'},
                'filename': 'pangolin.jpg',
                'file_type': 'image',
                'icon_url': 'https://easterisland.pamdas.org/api/v1.0/activity/event/aef7186c-b2fb-4282-ad5b-c7d8a6a116a5/file/3c17b152-6ca4-480d-aaa9-019e9d86e1f9/icon/pangolin.jpg'}],
        }]
    
@pytest.fixture
def sample_featuregroup():
    return {
        "name": "Boundary",
        "features": [{
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "EPSG:4326"}
            },
            "features": [{
                "type": "Feature",
                "properties": {
                    "feature_type": "5e0a5d1a-d7a0-420c-8fc7-2c60f90180d2",
                    "name": "Inner Boundary",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-109.379224,-27.159496],
                                     [-109.311654,-27.159496],
                                     [-109.311654,-27.103030],
                                     [-109.379224,-27.103030]]]
                }
            }]
        }]
    }    

@pytest.fixture
def dummy_erclient():
    mock = MagicMock()
    mock.service_root = "https://dummyersite/api/v1.0"
    return mock