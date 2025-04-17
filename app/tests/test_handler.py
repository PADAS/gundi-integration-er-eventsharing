from datetime import datetime, timezone, timedelta
import httpx
import pytest
import json
from erclient import ERClient
from unittest.mock import patch, Mock
from app.actions.handlers import action_auth, action_sync_events
from app.actions.er_syncer import er_syncer

@patch('erclient.ERClient.get_event_categories')
@patch('erclient.ERClient.post_event_category')
def test_creating_destination_event_categories(patchmock: Mock, catmock: Mock, source_event_categories, sample_auth_config, sample_action_config):
    catmock.side_effect = [source_event_categories, []]
    patchmock.side_effect = source_event_categories

    sync = er_syncer(auth_config = sample_auth_config, action_config = sample_action_config)
    sync.sync_event_categories()

    createdcat = patchmock.call_args.args[0]
    assert(createdcat['value'] == 'from_analyzer_cat')
    assert(createdcat['display'] == 'From-Analyzers')

@patch('erclient.ERClient.get_event_categories')
@patch('erclient.ERClient.patch_event_category')
def test_updating_destination_event_categories(patchmock: Mock, catmock: Mock, source_event_categories, destination_event_categories,
                                               modified_event_categories, sample_auth_config, sample_action_config):
    catmock.side_effect = (modified_event_categories, destination_event_categories)
    patchmock.return_value = source_event_categories

    sync = er_syncer(auth_config = sample_auth_config, action_config = sample_action_config)
    sync.sync_event_categories()

    createdcat = patchmock.call_args.args[0]
    assert(createdcat['value'] == 'from_analyzer_cat')
    assert(createdcat['display'] == 'From-Changed!')

@patch('erclient.ERClient.post_event_type')
@patch('erclient.ERClient.get_event_types')
@patch.object(er_syncer, '_get_event_type_schema')
def test_sync_event_types(get_event_schema: Mock, get_event_types: Mock, post_event_type: Mock, sample_event_type, 
                          sample_event_schema, sample_auth_config, sample_action_config):
    
    get_event_types.side_effect = [[sample_event_type], []]
    get_event_schema.return_value = sample_event_schema
    post_event_type.return_value = sample_event_type
    
    sync = er_syncer(auth_config = sample_auth_config, action_config = sample_action_config)
    sync.sync_event_types(['accident_rep'])

    createdtype = post_event_type.call_args.args[0]
    assert(createdtype['value'] == 'from_accident_rep')
    assert(createdtype['display'] == 'From-Accident')

    schema = json.loads(createdtype['schema'])
    for k in ['er2er_src_id', 'er2er_src_system', 'er2er_src_serial_number', 'er2er_src_service_root']:
        assert(k in schema['schema']['properties'])

@patch('erclient.ERClient.patch_event_type')
@patch('erclient.ERClient.get_event_types')
@patch.object(er_syncer, '_get_event_type_schema')
def test_sync_event_types_with_update(get_event_type_schema: Mock, get_event_types: Mock, patch_event_type: Mock, destination_event_type,
                                      sample_event_type, sample_modified_event_type, sample_event_schema, modified_event_schema, sample_auth_config, sample_action_config):
    get_event_type_schema.side_effect = [modified_event_schema, sample_event_schema]
    get_event_types.side_effect = [[sample_event_type], [destination_event_type]]
    patch_event_type.return_value = sample_modified_event_type
    
    sync = er_syncer(auth_config = sample_auth_config, action_config = sample_action_config)
    sync.sync_event_types(['accident_rep'])

    createdtype = patch_event_type.call_args.args[0]
    schema = json.loads(createdtype['schema'])
    assert('changed!' in schema['schema']['properties'])


@patch('erclient.ERClient.post_event_category')
@patch('erclient.ERClient.get_event_categories')
@patch('erclient.ERClient.patch_event_category')
def test_not_updating_destination_event_categories(patchmock: Mock, catmock: Mock, postmock: Mock, source_event_categories, destination_event_categories,
                                               sample_auth_config, sample_action_config):
    catmock.side_effect = (source_event_categories, destination_event_categories)
    patchmock.return_value = source_event_categories

    sync = er_syncer(auth_config = sample_auth_config, action_config = sample_action_config)
    sync.sync_event_categories()

    patchmock.assert_not_called()
    postmock.assert_not_called()

@patch('erclient.ERClient.post_event_type')
@patch('erclient.ERClient.patch_event_type')
@patch('erclient.ERClient.get_event_types')
@patch.object(er_syncer, '_get_event_type_schema')
def test_not_updating_event_types(get_event_type_schema: Mock, get_event_types: Mock, patch_event_type: Mock, post_event_type: Mock, destination_event_type,
                                      sample_event_type, sample_modified_event_type, sample_event_schema, modified_event_schema, sample_auth_config, sample_action_config):
    get_event_type_schema.side_effect = [sample_event_schema, sample_event_schema]
    get_event_types.side_effect = [[sample_event_type], [destination_event_type]]
    patch_event_type.return_value = sample_modified_event_type
    
    sync = er_syncer(auth_config = sample_auth_config, action_config = sample_action_config)
    sync.sync_event_types(['accident_rep'])

    patch_event_type.assert_not_called()
    post_event_type.assert_not_called()


@patch('app.actions.er_syncer.er_syncer._load_feature_group')
@patch('erclient.ERClient.get_objects_multithreaded')
def test_event_filtering(events_mock: Mock, get_fg: Mock, sample_featuregroup, sample_events, sample_auth_config, sample_action_config):
    
    events_mock.return_value = iter(sample_events)
    get_fg.return_value = sample_featuregroup

    sync = er_syncer(auth_config = sample_auth_config, action_config = sample_action_config)
    events = sync._get_events(erclient = ERClient(), since = datetime.now(tz = timezone.utc) - timedelta(days = 1), include_event_types = None, within_featuregroups = None)
    assert(len(list(events)) == 4)

    events_mock.return_value = iter(sample_events)
    events = sync._get_events(erclient = ERClient(), since = datetime.now(tz = timezone.utc) - timedelta(days = 1), include_event_types = None, within_featuregroups = ['feature_group'])
    assert(len(list(events)) == 1)