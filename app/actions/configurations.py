from enum import IntEnum
from typing import Optional, List, Dict
import pydantic
import re
from .core import SyncActionConfiguration, AuthActionConfiguration, ExecutableActionMixin
from app.services.errors import ConfigurationValidationError

class AuthenticateConfig(AuthActionConfiguration, ExecutableActionMixin):
    dest_token: pydantic.SecretStr = pydantic.Field(..., title = "Destination Token",
                                                       description = "API token for destination EarthRanger site.",
                                                       format = "password")
    dest_server: str = pydantic.Field('', title = "Destination Server",
                                         description = "Servername for destination EarthRanger site.")
    source_token: pydantic.SecretStr = pydantic.Field(..., title = "ER Source Token",
                                                       description = "API token for source EarthRanger site.",
                                                       format = "password")
    source_server:   str = pydantic.Field('', title = "Source Server",
                                         description = "Servername for source EarthRanger site.")
    
    @pydantic.validator("dest_server", "source_server")
    def fill_in_server_defaults(cls, server: str):
        server = re.sub("\/+$", "", server)
        if not(server.startswith("http")):
            server = "https://" + server
        if ("/api/v" not in server):
            server = server + "/api/v1.0"
        return server
        
class PriorityEnum(IntEnum):
    GRAY = 0
    GREEN = 100
    AMBER = 200
    RED = 300

class SyncEventsConfig(SyncActionConfiguration):
    days_to_sync: int = pydantic.Field(1, title = "Default Days to Sync",
        description = "If no previously successful run has occurred, specifies how many days of data to copy from the source to the destination system.")
    source_system_name: str = pydantic.Field(..., title = "Source System Name",
        description = "Name for source system.  Used to provide information about where an event orginated.")
    source_system_abbr: str = pydantic.Field(..., title = "Source System Abbreviation",
        description = "Abbreviation for source system.  Used to annotate events about where an event originated.")
    create_schema: bool = pydantic.Field(True, title = "Create Destination Event Types",
        description = "Whether to create event types and categories in the destination system if they don't already exist.  If false, event types that don't match a destination event type will not be sync'ed.")
    update_schema: bool = pydantic.Field(True, title = "Update Destination Event Types",
        description = "Whether to update event types and categories in the destination system to match the source system.")
    prepend_system_to_categories: bool = pydantic.Field(True, title = "Prepend System to Categories",
        description = "Whether the name of event categories that are created should be prepended with the abbrivation of the source system.")
    prepend_system_to_event_types: bool = pydantic.Field(True, title = "Prepend System to Event Types",
        description = "Whether the name of event types that are created should be prepended with the abbrivation of the source system.")
    prepend_system_to_event_titles: bool = pydantic.Field(True, title = "Prepend System to Event Titles",
        description = "Whether the titles of events that are created should be prepended with the abbrivation of the source system.")
    delete_unmatched_events: bool = pydantic.Field(True, title = "Delete Unmatched Events",
        description = "Whether events in the destination system no longer in the source system should be deleted from the destination system.")
    within_featuregroups: Optional[List[str]] = pydantic.Field(title = "Within Feature Groups",
        description = "If present, only events that are within one of the listed Feature Groups will be copied from the source system to destination system.")
    matching_priorities: Optional[List[str]] = pydantic.Field(title = "Matching Priorities",
        description = "If present, only events matching one of these priorities will be copied from the source to the destination system.")
    matching_states: Optional[List[str]] = pydantic.Field(title = "Matching States",
        description = "If present, only events matching one of these states will be copied from the source to the destination system.")
#    matching_detail_values: Optional[Dict[str, str]] = pydantic.Field(title = "Matching Detail Values",
#        description = "If present, only include events matching these event detail/value pairs.")
    

    @pydantic.validator("source_system_abbr")
    def ensure_keys_are_lowercase(cls, key: str):
        return key.lower()
    
    @pydantic.validator("matching_priorities")
    def convert_priorities_to_strings(cls, values: List):
        try:
            int_values = [int(val) for val in values]
        except ValueError:
            raise ConfigurationValidationError("Invalid value for matching priorities.")
        return int_values