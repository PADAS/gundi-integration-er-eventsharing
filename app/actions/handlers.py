import httpx
import logging
from datetime import datetime, timezone, timedelta
from app.actions.configurations import EarthRangerAuthConfig, DirectSyncConfig
from app.services.activity_logger import activity_logger, log_action_activity
from app.services.action_scheduler import crontab_schedule
from app.services.gundi import send_observations_to_gundi
from app.services.state import IntegrationStateManager
from app.services.errors import ConfigurationNotFound, ConfigurationValidationError
from app.services.utils import find_config_for_action
from gundi_core.schemas.v2 import Integration
from pydantic import BaseModel, parse_obj_as
from typing import List, Optional, Iterable, Generator, Any
from gundi_core.events import (
    LogLevel,
    IntegrationActionCustomLog)


logger = logging.getLogger(__name__)
state_manager = IntegrationStateManager()


def get_auth_config(integration, action_id:str):
    # Look for the login credentials, needed for any action
    auth_config = find_config_for_action(
        configurations=integration.configurations,
        action_id=action_id
    )

    if not auth_config:
        raise ConfigurationNotFound(
            f"Authentication settings for integration {str(integration.id)} and action {action_id} "
            f"are missing. Please fix the integration setup in the portal."
        )
    return EarthRangerAuthConfig.parse_obj(auth_config.data)


async def action_source_auth(integration:Integration, action_config: EarthRangerAuthConfig) -> dict:
    logger.info(f"Executing auth action with integration {integration} and action_config {action_config}...")

    try:
        # Ignore cached credentials, because this action is meant for validating configuration.

        url = f"https://{action_config.earthranger_host}/api/v1.0/user/me"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={'authorization': f'Bearer {action_config.earthranger_token}'})

        response.raise_for_status()

        return {"valid_credentials": response.status_code == 200}

    except httpx.HTTPStatusError as e:
        return {"valid_credentials": False, "status_code": e.response.status_code}


async def action_destination_auth(integration:Integration, action_config: EarthRangerAuthConfig) -> dict:
    logger.info(f"Executing auth action with integration {integration} and action_config {action_config}...")

    try:
        # Ignore cached credentials, because this action is meant for validating configuration.

        url = f"https://{action_config.earthranger_host}/api/v1.0/user/me"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={'authorization': f'Bearer {action_config.earthranger_token}'})

        response.raise_for_status()
        
        return {"valid_credentials": response.status_code == 200}

    except httpx.HTTPStatusError as e:
        return {"valid_credentials": False, "status_code": e.response.status_code}


# We'll come back and enable this crontab decorato later, when we're ready to deploy this in a Gundi Environment.
# @crontab_schedule("*/20 * * * *")
@activity_logger()
async def action_synchronize_events(integration:Integration, action_config: DirectSyncConfig) -> dict:
    logger.info(f"Executing synchronize_events action with integration {integration} and action_config {action_config}...")

    source_auth = get_auth_config(integration, 'source_auth')
    logger.info(f"Destination Auth config: {source_auth}")

    destination_auth = get_auth_config(integration, 'destination_auth')
    logger.info(f"Destination Auth config: {destination_auth}")

    # Add code here to do the synchronization things.

    return {"result": "success"}
