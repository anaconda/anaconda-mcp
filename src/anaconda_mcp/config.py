import logging
import re
from enum import Enum
from functools import cached_property

from anaconda_cli_base.config import AnacondaBaseSettings
from pydantic import AliasChoices, Field

logger = logging.getLogger(__name__)


ENV_VAR_PREFIX = "ANACONDA_MCP"


class Environments(Enum):
    production = "production"
    staging = "staging"


class AnacondaDomains(Enum):
    production = "anaconda.com"
    staging = "stage.anaconda.com"


ENVIRONMENT_TO_DOMAIN = {
    Environments.production.value: AnacondaDomains.production.value,
    Environments.staging.value: AnacondaDomains.staging.value,
}


class Settings(AnacondaBaseSettings, plugin_name="mcp"):
    environment: str = Field(
        default=Environments.production.value,
        validation_alias=AliasChoices(
            "anaconda_domain",
            "environment",
            "ANACONDA_MCP_ANACONDA_DOMAIN",
            "ANACONDA_MCP_ENVIRONMENT",
        ),
    )
    log_level: str = "INFO"
    service_name: str = "anaconda-mcp"
    send_metrics: bool = True
    python_executable: str | None = None
    accepted_terms: bool | None = None

    @cached_property
    def anaconda_domain(self) -> str:
        if self.environment in ENVIRONMENT_TO_DOMAIN:
            return ENVIRONMENT_TO_DOMAIN[self.environment]
        if re.search(r"[.:]", self.environment):
            return self.environment
        return AnacondaDomains.production.value


settings = Settings()
