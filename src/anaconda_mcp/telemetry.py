import enum
import importlib.metadata
import logging
import platform
import threading
from typing import Any

import httpx
from anaconda_cli_base.telemetry import count as _otel_count
from anaconda_cli_base.telemetry import histogram as _otel_histogram
from anaconda_cli_base.telemetry import log_event
from pydantic import BaseModel

from anaconda_mcp.auth import ANONYMOUS_USER_ID, USER_ID_STATUS_BAD_TOKEN, get_auth_token, resolve_user_id
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
# Exact-name, top-level-only filter (see emit_event): PII nested inside values or
# placed under non-canonical keys (e.g. "user_email") is NOT scrubbed from OTel.
_PII_KEYS = (PII_KEY_EMAIL, PII_KEY_UUID)


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
        # user.id is merged AFTER the PII filter so it always survives, and is
        # OTel-only — the snake-eyes params/MetricData path above is untouched.
        otel_attrs.update(_otel_user_attrs())
        # event_name doubles as the OTLP log body (1st positional) and the event_name kwarg.
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


def _otel_user_attrs() -> dict[str, str]:
    try:
        user_id, status = resolve_user_id()
        return {"user.id": user_id or ANONYMOUS_USER_ID, "user.id.status": status}
    except Exception:
        return {"user.id": ANONYMOUS_USER_ID, "user.id.status": USER_ID_STATUS_BAD_TOKEN}


class _UserContextLogFilter(logging.Filter):
    """Stamp user.id/user.id.status onto every OTel-exported log record.

    The OTel LoggingHandler copies non-reserved record.__dict__ keys to the
    exported log attributes verbatim (dotted keys included). Setting via
    record.__dict__[...] is required — "user.id" is not a valid attribute
    identifier for setattr.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.__dict__.update(_otel_user_attrs())
        return True


def _emit_tool_metrics(tool_name: str, duration_ms: float, *, is_error: bool) -> None:
    try:
        attrs: dict[str, object] = {"tool": tool_name}
        # is_error is recorded only on failures to keep success a single low-cardinality
        # series per tool; dashboards derive success as total minus is_error=true.
        if is_error:
            attrs["is_error"] = True
        attrs.update(_otel_user_attrs())
        _otel_count("mcp_tool_invoked", plugin_name="mcp", attributes=attrs)
        _otel_histogram(
            "mcp_tool_duration_ms",
            plugin_name="mcp",
            value=duration_ms,
            attributes=attrs,
        )
    except Exception:
        logger.debug("OTel tool metrics emission failed", exc_info=True)
