import logging
import dateparser
from datetime import datetime, timezone, timedelta
from app.services.action_scheduler import crontab_schedule
from app.services.activity_logger import activity_logger
from app.services.state import IntegrationStateManager
from gundi_core.schemas.v2 import Integration
from erclient import ERClient
from .er_syncer import er_syncer
from app.actions.configurations import AuthenticateConfig, SyncEventsConfig
from app.services.errors import ConfigurationNotFound
from app.services.utils import find_config_for_action

logger = logging.getLogger(__name__)
state_manager = IntegrationStateManager()

async def action_auth(integration:Integration, action_config: AuthenticateConfig):
    logger.info(f"Executing auth action with integration {integration} and action_config {action_config}...")

    try:
        erclient = ERClient(service_root = action_config.source_server, token = action_config.source_token.get_secret_value())
        erclient.get_me()

        ERClient(service_root = action_config.dest_server, token = action_config.dest_token.get_secret_value())
        erclient.get_me()
        return {"valid_credentials": True}
    
    except erclient.ERClientException as e:
        return {"valid_credentials": False, "status_code": e.response.status_code}


@activity_logger()
@crontab_schedule("*/15 * * * *") # Run every 15 minutes
async def action_sync_events(integration:Integration, action_config: SyncEventsConfig):
    now = datetime.now(tz=timezone.utc)

    auth_config = _get_auth_config(integration)
    syncer = er_syncer(auth_config, action_config)

    state = await state_manager.get_state(integration.id, "sync_events")
    load_since = state.get('last_run')
    load_since = dateparser.parse(load_since) if load_since else now - timedelta(days=action_config.days_to_sync)

    results = syncer.sync(start_date = load_since)
    await state_manager.set_state(integration_id=integration.id, action_id="sync_events", state={"last_run": now})
    return results


def _get_auth_config(integration):
    # Look for the login credentials, needed for any action
    auth_config = find_config_for_action(
        configurations=integration.configurations,
        action_id="auth"
    )
    if not auth_config:
        raise ConfigurationNotFound(
            f"Authentication settings for integration {str(integration.id)} "
            f"are missing. Please fix the integration setup in the portal."
        )
    return AuthenticateConfig.parse_obj(auth_config.data)
