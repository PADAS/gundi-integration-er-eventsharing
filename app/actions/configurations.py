import pydantic
from app.services.utils import FieldWithUIOptions, GlobalUISchemaOptions
from .core import AuthActionConfiguration, PullActionConfiguration, ExecutableActionMixin


class EarthRangerAuthConfig(AuthActionConfiguration, ExecutableActionMixin):
    earthranger_host: str = pydantic.Field(..., title = "EarthRanger Host", description = "The host of the EarthRanger API.")
    earthranger_token: pydantic.SecretStr = pydantic.Field(..., title = "EarthRanger Auth Token", description = "A long-lived Auth Token for EarthRanger API access.")

    ui_global_options: GlobalUISchemaOptions = GlobalUISchemaOptions(
        order=[
            "earthranger_host",
            "earthranger_token",
        ],
    )

class DirectSyncConfig(PullActionConfiguration):
    some_property: str = pydantic.Field(..., title = "Some Property", description = "Some Property")