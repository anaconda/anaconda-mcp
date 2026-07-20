import enum
import functools
import importlib.metadata
import json
import logging
import os
import platform
import sys
import threading
from typing import Any

import httpx
from anaconda_cli_base.telemetry import count as _otel_count
from anaconda_cli_base.telemetry import histogram as _otel_histogram
from anaconda_cli_base.telemetry import log_event
from pydantic import BaseModel

from anaconda_mcp.auth import get_auth_token, resolve_user_id
from anaconda_mcp.config import settings
from anaconda_mcp.mcp_state import get_or_create_install_id

logger = logging.getLogger(__name__)


KNOWN_DISTRIBUTION_SURFACES = frozenset({"pip", "uvx", "conda", "ana", "mcpb", "unknown"})


def _read_installer(package_name: str) -> str | None:
    """Read the dist-info INSTALLER file for `package_name`. Total: never raises."""
    try:
        text = importlib.metadata.distribution(package_name).read_text("INSTALLER")
    except Exception:
        return None
    if not text:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lower()
    return None


def _has_conda_meta_record(package_name: str) -> bool:
    """True iff a conda-meta record in sys.prefix has this exact package name.

    Uses the filename as a cheap pre-filter only; the actual match is against
    the record's own JSON "name" field (conda-authoritative), so a package like
    "anaconda-mcp-extras" never false-matches "anaconda-mcp" regardless of
    hyphens in versions/builds. Never raises.
    """
    conda_meta_dir = os.path.join(sys.prefix, "conda-meta")
    try:
        entries = os.listdir(conda_meta_dir)
    except OSError:
        return False
    prefix = f"{package_name}-"
    for entry in entries:
        if not (entry.startswith(prefix) and entry.endswith(".json")):
            continue
        try:
            with open(os.path.join(conda_meta_dir, entry), encoding="utf-8") as f:
                record = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(record, dict) and record.get("name") == package_name:
            return True
    return False


@functools.cache
def _detect_distribution_surface() -> str:
    """Auto-detect the surface when ANACONDA_MCP_DISTRIBUTION_SURFACE is unset.

    Precedence: conda-meta record first (this package's conda recipe installs
    via pip internally, so a conda install ALSO carries INSTALLER="pip" -
    conda-meta must win or conda installs get misreported as pip), then the
    dist-info INSTALLER file (pip->pip, uv->uvx), else "unknown". Memoized -
    this is called on every tool invocation via _emit_tool_metrics, so it must
    not repeat filesystem/metadata I/O per call. Never raises (each branch is
    already total; this function itself doesn't need its own try/except).
    """
    if _has_conda_meta_record("anaconda-mcp"):
        logger.debug("Detected distribution surface 'conda' via conda-meta record")
        return "conda"
    installer = _read_installer("anaconda-mcp")
    if installer == "pip":
        logger.debug("Detected distribution surface 'pip' via INSTALLER=%r", installer)
        return "pip"
    if installer == "uv":
        logger.debug("Detected distribution surface 'uvx' via INSTALLER=%r", installer)
        return "uvx"
    logger.debug("Could not detect distribution surface (installer=%r); defaulting to 'unknown'", installer)
    return "unknown"


def resolve_distribution_surface() -> str:
    """Return which distribution surface this server is running through.

    Read from the ``ANACONDA_MCP_DISTRIBUTION_SURFACE`` environment variable
    (set by launchers such as the MCPB bundle). A recognized value wins
    outright; a set-but-unrecognized value coerces to ``"unknown"``; an
    unset/empty value falls through to runtime auto-detection via
    ``_detect_distribution_surface()``. Total: never raises.
    """
    try:
        candidate = os.environ.get("ANACONDA_MCP_DISTRIBUTION_SURFACE", "")
        if candidate:
            if candidate in KNOWN_DISTRIBUTION_SURFACES:
                return candidate
            logger.debug("Unrecognized distribution surface %r; coercing to 'unknown'", candidate)
            return "unknown"
        return _detect_distribution_surface()
    except Exception:
        return "unknown"


SCHEMA_VERSION = "1"


# Ride OTel *events* only, never spans or log records. Keys must not collide
# with `source`/`plugin` (added by anaconda-cli-base) or `user.id`.
@functools.cache
def _base_dimensions() -> dict[str, str]:
    """Foundation telemetry dimensions stamped on every OTel event.

    Cached once per process (dims are process-stable; ``cache_clear()`` to reset,
    test-only). Each dimension resolves under its own try/except, so a single
    failure omits only that key and never raises — never drops the whole event.
    """
    dims: dict[str, str] = {"schema_version": SCHEMA_VERSION}

    try:
        dims["install_id"] = get_or_create_install_id()
    except Exception:
        logger.debug("Failed to resolve install_id dimension", exc_info=True)

    try:
        dims["distribution_surface"] = resolve_distribution_surface()
    except Exception:
        logger.debug("Failed to resolve distribution_surface dimension", exc_info=True)

    try:
        dims["python_version"] = platform.python_version()
    except Exception:
        logger.debug("Failed to resolve python_version dimension", exc_info=True)

    try:
        dims["package_version"] = _get_package_version()
    except Exception:
        logger.debug("Failed to resolve package_version dimension", exc_info=True)

    try:
        dims["user_environment"] = settings.environment
    except Exception:
        logger.debug("Failed to resolve user_environment dimension", exc_info=True)

    return dims


class MetricNames(enum.Enum):
    _EVENT_PREFIX = "anaconda_mcp"
    START_SERVER = f"{_EVENT_PREFIX}_start_server"
    LOGIN_COMPLETED = f"{_EVENT_PREFIX}_login_completed"
    TOOL_COMPLETED = f"{_EVENT_PREFIX}_tool_completed"
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
        # _base_dimensions() fills in default telemetry context but never overrides
        # a caller-supplied event param with the same name.
        for key, value in _base_dimensions().items():
            otel_attrs.setdefault(key, value)
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


# NOTE: sibling services set user.id centrally via ResourceAttributes.user_id, but
# anaconda-cli-base builds the OTel Resource at init and exposes no post-init API to
# set it, so we inject user.id per-signal (here + the span + _UserContextLogFilter).
# Kept OFF tool metrics deliberately: a per-account UUID would explode metric-series
# cardinality (see security review); attribution lives on events/spans/logs instead.
def _otel_user_attrs() -> dict[str, str]:
    """OTel attributes for the authenticated user. Empty dict when unauthenticated
    (schema-conforming: user.id is omitted, never a sentinel; no status field)."""
    try:
        user_id = resolve_user_id()
    except Exception:
        return {}
    return {"user.id": user_id} if user_id else {}


class _UserContextLogFilter(logging.Filter):
    """Stamp user.id onto every OTel-exported log record when authenticated.

    The OTel LoggingHandler copies non-reserved record.__dict__ keys to the
    exported log attributes verbatim (dotted keys included). Setting via
    record.__dict__[...] is required — "user.id" is not a valid attribute
    identifier for setattr. When unauthenticated, ``_otel_user_attrs()``
    returns ``{}`` and the merge is a no-op (schema-conforming: user.id is
    omitted, never a sentinel).

    Keep this user.id-only: adding install_id/base dims would recurse (resolving
    install_id logs, which re-enters this filter) and get_or_create_install_id
    has no re-entrancy guard.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.__dict__.update(_otel_user_attrs())
        return True


# Metric labels must stay low-cardinality: only `tool`, `is_error`, and
# `distribution_surface` (a closed enum). Never add user.id/install_id or other
# per-account/install/package values — they'd explode the metric series.
def _emit_tool_metrics(tool_name: str, duration_ms: float, *, is_error: bool) -> None:
    try:
        attrs: dict[str, object] = {"tool": tool_name}
        # is_error is recorded only on failures to keep success a single low-cardinality
        # series per tool; dashboards derive success as total minus is_error=true.
        if is_error:
            attrs["is_error"] = True
        attrs["distribution_surface"] = resolve_distribution_surface()
        _otel_count("mcp_tool_invoked", plugin_name="mcp", attributes=attrs)
        _otel_histogram(
            "mcp_tool_duration_ms",
            plugin_name="mcp",
            value=duration_ms,
            attributes=attrs,
        )
    except Exception:
        logger.debug("OTel tool metrics emission failed", exc_info=True)
