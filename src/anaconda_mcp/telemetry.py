import enum
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from anaconda_mcp.auth import get_auth_token
from anaconda_mcp.config import settings

logger = logging.getLogger(__name__)


class MetricNames(enum.Enum):
    _EVENT_PREFIX = "anaconda_mcp"
    EVENT_CREATE_PROJECT = f"{_EVENT_PREFIX}_start_server"
    EVENT_DELETE_PROJECT = f"{_EVENT_PREFIX}_login_completed"


class MetricData(BaseModel):
    event: str
    event_params: dict[str, Any]
    service_id: str = settings.SERVICE_NAME
    user_environment: str = settings.ENVIRONMENT


# TODO: Introduce Anaconda OpenTelemetry when auth is compatible with api-keys or we have a solution in anaconda-auth
class SnakeEyes:
    """Snake eyes client - Sends metrics/logs to Anaconda Snake Eyes"""

    async def _make_request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        bearer_token: str | None = None,
    ) -> httpx.Response:
        headers: dict[str, str] = {"Accept": "application/json"}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        async with httpx.AsyncClient(
            base_url=f"https://{settings.ANACONDA_DOMAIN}",
            headers=headers,
            timeout=httpx.Timeout(3.0),
        ) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            return response

    async def send(self, metric_data: MetricData) -> bool:
        """
        Send metric data to Snake Eyes
        Args:
            metric_data (Dict): JSON containing all the relevant data.

        Returns:
            bool: Boolean indicating success (True) or failure (False).
        """
        if not settings.SEND_METRICS:
            logger.debug("Metrics are OFF. Metrics will not be sent.")
            return False

        bearer_token = get_auth_token()
        logger.info(f"Sending metric: {metric_data}")

        try:
            if bearer_token:
                response = await self._make_request(
                    "api/snake-eyes/record",
                    metric_data.model_dump(),
                    bearer_token,
                )
            else:
                payload = {
                    "service_id": metric_data.service_id,
                    "event": metric_data.event,
                    "event_params": {**metric_data.event_params, "user_environment": metric_data.user_environment},
                }
                response = await self._make_request("api/snake-eyes/note", payload)

            if 199 < response.status_code < 300:
                return True
            return False
        except httpx.TimeoutException:
            logger.warning("Timeout while writing file snake-eyes metrics")
            return False
        except httpx.NetworkError:
            logger.warning("Network error while sending snake-eyes metrics")
            return False
        except Exception:
            logger.warning("Error while sending snake-eyes metrics")
            return False
