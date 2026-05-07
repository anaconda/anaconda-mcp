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
    environment: str = Environments.production.value
    anaconda_domain: str | None = None
    log_level: str = "INFO"
    service_name: str = "anaconda-mcp"
    send_metrics: bool = True
    python_executable: str | None = None

    @model_validator(mode="after")
    def set_anaconda_domain(self):
        if self.anaconda_domain is not None:
            return self

        env = self.environment.lower()

        domains_mapping = {
            Environments.production.value: AnacondaDomains.production.value,
            Environments.staging.value: AnacondaDomains.staging.value,
        }
        self.anaconda_domain = domains_mapping.get(env, AnacondaDomains.production.value)
        return self


settings = Settings()
