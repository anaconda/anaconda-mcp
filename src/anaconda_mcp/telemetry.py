import enum
import importlib.metadata
import logging
import platform
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

import httpx
from anaconda_cli_base.telemetry import count as _otel_count
from anaconda_cli_base.telemetry import histogram as _otel_histogram
from anaconda_cli_base.telemetry import log_event
from anaconda_cli_base.telemetry import traced as _otel_traced
from pydantic import BaseModel

from anaconda_mcp.auth import get_auth_token
from anaconda_mcp.config import settings

logger = logging.getLogger(__name__)


class MetricNames(enum.Enum):
    _EVENT_PREFIX = "anaconda_mcp"
    START_SERVER = f"{_EVENT_PREFIX}_start_server"
    LOGIN_COMPLETED = f"{_EVENT_PREFIX}_login_completed"
    TOOL_COMPLETED = f"{_EVENT_PREFIX}_tool_completed"
    ACTIVE_USER_PING = f"{_EVENT_PREFIX}_active_user_ping"
    INSTALL_COMPLETED = f"{_EVENT_PREFIX}_install_completed"
    CONTACT_CONSENT = f"{_EVENT_PREFIX}_contact_consent"


NEW_USER_THRESHOLD_DAYS = 1


class MetricData(BaseModel):
    event: str
    event_params: dict[str, Any]
    service_id: str = settings.service_name
    user_environment: str = settings.environment


PII_KEY_EMAIL = "email"
PII_KEY_UUID = "uuid"
PII_KEY_AAU_CLIENT_ID = "aau_client_id"
_PII_KEYS = (PII_KEY_EMAIL, PII_KEY_UUID, PII_KEY_AAU_CLIENT_ID)


def emit_event(
    event_name: str,
    event_params: dict[str, Any] | None = None,
    *,
    blocking: bool = False,
) -> None:
    """Emit a telemetry event to snake-eyes and OTel.

    Sends the full event payload to snake-eyes (preserves byte-identical
    wire format via SnakeEyes.send) and a sanitized version to OTel via
    log_event. PII keys defined in _PII_KEYS are stripped from the OTel
    attributes; snake-eyes still receives them because that data flows to
    Anaconda's own telemetry backend.

    Args:
        event_name: One of MetricNames.*.value. Used as both the event
            name and human-readable body in OTel.
        event_params: Per-event attributes. Passed verbatim to snake-eyes;
            PII-filtered before reaching OTel.
        blocking: If True, snake-eyes send is synchronous (used by
            INSTALL_COMPLETED to ensure delivery before the setup command
            exits). OTel's log_event is always synchronous and not affected
            by this flag.

    Returns silently if settings.send_metrics is False. Both sinks are
    wrapped in try/except — failure of one never affects the other or the
    caller.
    """
    if not settings.send_metrics:
        return
    params = event_params or {}

    try:
        SnakeEyes().send(
            MetricData(event=event_name, event_params=params),
            bearer_token=get_auth_token(),
            blocking=blocking,
        )
    except Exception:
        logger.debug("snake-eyes emission failed for %s", event_name, exc_info=True)

    try:
        otel_attrs = {k: v for k, v in params.items() if k not in _PII_KEYS}
        log_event(
            event_name,
            event_name=event_name,
            plugin_name="mcp",
            attributes=otel_attrs,
        )
    except Exception:
        logger.debug("OTel log_event failed for %s", event_name, exc_info=True)


def _get_package_version() -> str:
    try:
        return importlib.metadata.version("anaconda-mcp")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


class SnakeEyes:
    """Snake eyes client - Sends metrics/logs to Anaconda Snake Eyes"""

    def _make_request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        bearer_token: str | None = None,
    ) -> httpx.Response:
        headers: dict[str, str] = {"Accept": "application/json"}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        with httpx.Client(
            base_url=f"https://{settings.anaconda_domain}",
            headers=headers,
            timeout=httpx.Timeout(3.0),
        ) as client:
            response = client.post(endpoint, json=payload)
            return response

    def _send(self, metric_data: MetricData, bearer_token: str | None = None) -> bool:
        if not settings.send_metrics:
            logger.debug("Metrics are OFF. Metrics will not be sent.")
            return False

        logger.debug(f"Sending metric: {metric_data}")

        try:
            is_authenticated = bearer_token is not None
            enriched_params = {
                **metric_data.event_params,
                "user_environment": metric_data.user_environment,
                "is_authenticated": is_authenticated,
                "os_platform": platform.system() or "unknown",
                "os_arch": platform.machine() or "unknown",
                "python_version": platform.python_version(),
                "package_version": _get_package_version(),
            }
            if is_authenticated:
                payload = {
                    **metric_data.model_dump(),
                    "event_params": enriched_params,
                }
                response = self._make_request(
                    "api/snake-eyes/record",
                    payload,
                    bearer_token,
                )
            else:
                payload = {
                    "service_id": metric_data.service_id,
                    "event": metric_data.event,
                    "event_params": enriched_params,
                }
                response = self._make_request("api/snake-eyes/note", payload)

            if 199 < response.status_code < 300:
                return True
            logger.warning("Snake-eyes returned HTTP %s", response.status_code)
            return False
        except httpx.TimeoutException:
            logger.warning("Timeout while sending snake-eyes metrics")
            return False
        except httpx.NetworkError:
            logger.warning("Network error while sending snake-eyes metrics")
            return False
        except Exception:
            logger.warning("Error while sending snake-eyes metrics")
            return False

    def send(self, metric_data: MetricData, bearer_token: str | None = None, blocking: bool = False) -> None:
        # TODO: Remove fire-and-forget thread once OpenTelemetry is integrated — its SDK handles async dispatch natively.
        if blocking:
            self._send(metric_data, bearer_token)
            return
        else:
            thread = threading.Thread(
                target=self._send,
                args=(metric_data, bearer_token),
                daemon=True,
            )
            thread.start()


def _get_client_info(context: Any) -> tuple[str, str]:
    try:
        if context is not None:
            client_params = context.session.client_params
            if client_params is not None:
                return client_params.clientInfo.name, client_params.clientInfo.version
    except Exception:
        pass
    return "unknown", "unknown"


def _emit_tool_metrics(tool_name: str, duration_ms: float, *, is_error: bool) -> None:
    try:
        attrs: dict[str, object] = {"tool": tool_name}
        if is_error:
            attrs["is_error"] = True
        _otel_count("mcp_tool_invoked", plugin_name="mcp", attributes=attrs)
        _otel_histogram(
            "mcp_tool_duration_ms",
            plugin_name="mcp",
            value=duration_ms,
            attributes=attrs,
        )
    except Exception:
        logger.debug("OTel tool metrics emission failed", exc_info=True)


def make_tracked_call_tool(
    original_call_tool: Callable,
    max_tool_call_history: int = 20,
    aau_client_id: str | None = None,
) -> Callable:
    tool_call_history: deque[str] = deque(maxlen=max_tool_call_history)

    async def _tracked(self, name, arguments, context=None, convert_result=False):
        start = time.monotonic()
        is_error = False
        error_description = ""
        captured_exc: BaseException | None = None
        result = None
        try:
            with _otel_traced(
                f"mcp_tool_{name}",
                plugin_name="mcp",
                attributes={"tool": name},
            ) as span:
                try:
                    result = await original_call_tool(
                        self, name, arguments, context=context, convert_result=convert_result
                    )
                except Exception as exc:
                    is_error = True
                    error_description = f"{type(exc).__name__}: {exc}"
                    try:
                        span.add_exception(exc)
                    except Exception:
                        logger.debug("OTel span exception annotation failed", exc_info=True)
                    captured_exc = exc
        finally:
            tool_call_history.append(name)
            if settings.send_metrics:
                client_name, client_version = _get_client_info(context)
                duration_ms = round((time.monotonic() - start) * 1000, 2)
                event_params = {
                    "tool_name": name,
                    "client_name": client_name,
                    "client_version": client_version,
                    "duration_ms": duration_ms,
                    "is_error": is_error,
                    "error_description": error_description,
                    "tool_call_history": ",".join(tool_call_history),
                }
                if aau_client_id is not None:
                    event_params[PII_KEY_AAU_CLIENT_ID] = aau_client_id
                emit_event(MetricNames.TOOL_COMPLETED.value, event_params)
                _emit_tool_metrics(name, duration_ms, is_error=is_error)
        if captured_exc is not None:
            raise captured_exc
        return result

    return _tracked


def make_tracking_hook(
    aau_client_id: str | None = None,
) -> Callable:
    def hook(original_call_tool: Callable) -> Callable:
        return make_tracked_call_tool(original_call_tool, aau_client_id=aau_client_id)

    return hook


def patch_tool_call_tracking(aau_client_id: str | None = None) -> None:
    from anaconda_mcp.tool_hooks import patch_tool_call_hooks

    patch_tool_call_hooks([make_tracking_hook(aau_client_id=aau_client_id)])
