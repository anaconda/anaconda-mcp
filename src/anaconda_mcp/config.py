import logging
from enum import Enum

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


ENV_VAR_PREFIX = "ANACONDA_MCP"


class Environments(Enum):
    production = "production"
    staging = "staging"


class AnacondaDomains(Enum):
    production = "anaconda.com"
    staging = "stage.anaconda.com"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=f"{ENV_VAR_PREFIX}_",
        env_file=".env",
        extra="allow",
    )
    ANACONDA_DOMAIN: str = "anaconda.com"
    ENVIRONMENT: str = Environments.production.value
    LOG_LEVEL: str = "INFO"
    SERVICE_NAME: str = "anaconda-mcp"
    SEND_METRICS: bool = True
    PYTHON_EXECUTABLE: str | None = None

    @field_validator("ANACONDA_DOMAIN", mode="before")
    @classmethod
    def set_anaconda_domain(cls, v, info):
        if v is not None:
            return v

        env = info.data.get("ENVIRONMENT", "").lower()

        domains_mapping = {
            Environments.production.value: AnacondaDomains.production.value,
            Environments.staging.value: AnacondaDomains.staging.value,
        }
        return domains_mapping.get(env, AnacondaDomains.production.value)


settings = Settings()
