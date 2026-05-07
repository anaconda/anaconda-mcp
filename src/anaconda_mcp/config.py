import logging
from enum import Enum

from anaconda_cli_base.config import AnacondaBaseSettings
from pydantic import model_validator

logger = logging.getLogger(__name__)


ENV_VAR_PREFIX = "ANACONDA_MCP"


class Environments(Enum):
    production = "production"
    staging = "staging"


class AnacondaDomains(Enum):
    production = "anaconda.com"
    staging = "stage.anaconda.com"


class Settings(AnacondaBaseSettings, plugin_name="mcp"):
    ENVIRONMENT: str = Environments.production.value
    ANACONDA_DOMAIN: str | None = None
    LOG_LEVEL: str = "INFO"
    SERVICE_NAME: str = "anaconda-mcp"
    SEND_METRICS: bool = True
    PYTHON_EXECUTABLE: str | None = None

    @model_validator(mode="after")
    def set_anaconda_domain(self):
        if self.ANACONDA_DOMAIN is not None:
            return self

        env = self.ENVIRONMENT.lower()

        domains_mapping = {
            Environments.production.value: AnacondaDomains.production.value,
            Environments.staging.value: AnacondaDomains.staging.value,
        }
        self.ANACONDA_DOMAIN = domains_mapping.get(env, AnacondaDomains.production.value)
        return self


settings = Settings()
