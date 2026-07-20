import importlib.metadata
import json as _json
import logging
import os
from unittest import mock

import httpx
import pytest

from anaconda_mcp.telemetry import (
    KNOWN_DISTRIBUTION_SURFACES,
    MetricData,
    MetricNames,
    SnakeEyes,
    _base_dimensions,
    _detect_distribution_surface,
    _emit_tool_metrics,
    _get_conda_meta_version,
    _get_package_version,
    _otel_user_attrs,
    _read_installer,
    emit_event,
    resolve_distribution_surface,
)
from conftest import BASE_DIMENSION_KEYS, TEST_USER_ID


@pytest.fixture
def mocked_response():
    return httpx.Response(status_code=200)


@pytest.fixture
def mock_make_request(mocked_response):
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes._make_request") as m:
        m.return_value = mocked_response
        yield m


def test_known_distribution_surfaces_is_exactly_the_supported_set():
    """The enum is exactly the 6 supported surfaces - no more, no less. Guards
    against silently re-adding distro/miniconda or any other unsupported value."""
    assert KNOWN_DISTRIBUTION_SURFACES == frozenset({"pip", "uvx", "conda", "ana", "mcpb", "unknown"})


def test_snake_eyes_send_metric(mock_make_request):
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    was_sent = SnakeEyes()._send(metric, bearer_token="fake-token")
    assert was_sent is True
    assert mock_make_request.call_count == 1
    assert mock_make_request.call_args[0][0] == "api/snake-eyes/record"


def test_snake_eyes_send_anonymous_metric_when_no_auth_token(mock_make_request):
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    was_sent = SnakeEyes()._send(metric)
    assert was_sent is True
    assert mock_make_request.call_count == 1
    assert mock_make_request.call_args[0][0] == "api/snake-eyes/note"


def test_snake_eyes_send_metrics_off_suppresses(mock_make_request):
    with mock.patch("anaconda_mcp.telemetry.settings") as mock_settings:
        mock_settings.send_metrics = False
        metric = MetricData(
            event=MetricNames.START_SERVER.value,
            event_params={},
        )
        was_sent = SnakeEyes()._send(metric)
        assert was_sent is False
        assert mock_make_request.call_count == 0


def test_snake_eyes_send_returns_false_on_non_2xx(mock_make_request):
    mock_make_request.return_value = httpx.Response(status_code=500)
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    was_sent = SnakeEyes()._send(metric)
    assert was_sent is False


def test_snake_eyes_send_handles_timeout():
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes._make_request") as m:
        m.side_effect = httpx.TimeoutException("timed out")
        metric = MetricData(
            event=MetricNames.START_SERVER.value,
            event_params={},
        )
        was_sent = SnakeEyes()._send(metric)
        assert was_sent is False


def test_snake_eyes_send_handles_network_error():
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes._make_request") as m:
        m.side_effect = httpx.NetworkError("connection refused")
        metric = MetricData(
            event=MetricNames.START_SERVER.value,
            event_params={},
        )
        was_sent = SnakeEyes()._send(metric)
        assert was_sent is False


def test_snake_eyes_send_fires_on_background_thread(mock_make_request):
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    with mock.patch("anaconda_mcp.telemetry.threading.Thread") as mock_thread:
        mock_instance = mock.MagicMock()
        mock_thread.return_value = mock_instance

        SnakeEyes().send(metric, bearer_token="fake-token")

        mock_thread.assert_called_once()
        assert mock_thread.call_args[1]["daemon"] is True
        mock_instance.start.assert_called_once()


def test_snake_eyes_send_blocking_calls_directly(mock_make_request):
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    SnakeEyes().send(metric, bearer_token="fake-token", blocking=True)

    assert mock_make_request.call_count == 1
    assert mock_make_request.call_args[0][0] == "api/snake-eyes/record"


def test_otel_user_attrs_authenticated():
    assert _otel_user_attrs() == {"user.id": TEST_USER_ID}


def test_otel_user_attrs_no_token():
    import anaconda_mcp.auth

    anaconda_mcp.auth._reset_user_id_cache()
    with mock.patch("anaconda_mcp.auth.get_auth_token", return_value=None):
        assert _otel_user_attrs() == {}


def test_otel_user_attrs_backstop_on_exception():
    """Backstop: if resolve_user_id raises, _otel_user_attrs returns {} (no user.id key)."""
    with mock.patch("anaconda_mcp.telemetry.resolve_user_id", side_effect=RuntimeError("boom")):
        assert _otel_user_attrs() == {}


def test_emit_tool_metrics_omits_user_id():
    """Authenticated → user.id is deliberately OMITTED from both metrics to avoid
    per-account cardinality explosion; tool label remains."""
    with (
        mock.patch("anaconda_mcp.telemetry._otel_count") as mock_count,
        mock.patch("anaconda_mcp.telemetry._otel_histogram") as mock_hist,
    ):
        _emit_tool_metrics("mytool", 12.5, is_error=False)

    assert mock_count.call_count == 1
    assert mock_hist.call_count == 1

    count_attrs = mock_count.call_args.kwargs["attributes"]
    hist_attrs = mock_hist.call_args.kwargs["attributes"]

    for attrs in (count_attrs, hist_attrs):
        assert "user.id" not in attrs
        assert "user.id.status" not in attrs
        assert attrs["tool"] == "mytool"
        assert "is_error" not in attrs


def test_emit_tool_metrics_omits_user_id_when_anonymous():
    """Anonymous (no token) → user.id key ABSENT from both metrics; tool/is_error still present."""
    import anaconda_mcp.auth

    anaconda_mcp.auth._reset_user_id_cache()
    with (
        mock.patch("anaconda_mcp.auth.get_auth_token", return_value=None),
        mock.patch("anaconda_mcp.telemetry._otel_count") as mock_count,
        mock.patch("anaconda_mcp.telemetry._otel_histogram") as mock_hist,
    ):
        _emit_tool_metrics("mytool", 5.0, is_error=True)

    assert mock_count.call_count == 1
    assert mock_hist.call_count == 1

    count_attrs = mock_count.call_args.kwargs["attributes"]
    hist_attrs = mock_hist.call_args.kwargs["attributes"]

    for attrs in (count_attrs, hist_attrs):
        assert "user.id" not in attrs
        assert "user.id.status" not in attrs
        assert attrs["tool"] == "mytool"
        assert attrs["is_error"] is True


def test_emit_tool_metrics_includes_distribution_surface():
    """distribution_surface is present on both metrics and is always a member of the
    closed KNOWN_DISTRIBUTION_SURFACES enum (never an arbitrary/un-coerced string).
    install_id/user_id remain absent - the metric label set stays limited to
    tool/is_error/distribution_surface."""
    with (
        mock.patch("anaconda_mcp.telemetry._otel_count") as mock_count,
        mock.patch("anaconda_mcp.telemetry._otel_histogram") as mock_hist,
    ):
        _emit_tool_metrics("mytool", 12.5, is_error=False)

    count_attrs = mock_count.call_args.kwargs["attributes"]
    hist_attrs = mock_hist.call_args.kwargs["attributes"]

    for attrs in (count_attrs, hist_attrs):
        assert attrs["distribution_surface"] in KNOWN_DISTRIBUTION_SURFACES
        assert "install_id" not in attrs
        assert "user_id" not in attrs
        assert "user.id" not in attrs


def test_emit_tool_metrics_distribution_surface_is_coerced_never_raw(monkeypatch):
    """An unrecognized ANACONDA_MCP_DISTRIBUTION_SURFACE value never reaches the metric
    label as-is — only the resolver's already-coerced "unknown" fallback does."""
    monkeypatch.setenv("ANACONDA_MCP_DISTRIBUTION_SURFACE", "bogus-surface-xyz")
    with (
        mock.patch("anaconda_mcp.telemetry._otel_count") as mock_count,
        mock.patch("anaconda_mcp.telemetry._otel_histogram") as mock_hist,
    ):
        _emit_tool_metrics("mytool", 12.5, is_error=False)

    count_attrs = mock_count.call_args.kwargs["attributes"]
    hist_attrs = mock_hist.call_args.kwargs["attributes"]

    for attrs in (count_attrs, hist_attrs):
        assert attrs["distribution_surface"] == "unknown"


def test_resolve_distribution_surface_recognized_env_wins(monkeypatch):
    """A recognized env value is returned verbatim; the detector is never invoked
    (short-circuit regression guard)."""
    monkeypatch.setenv("ANACONDA_MCP_DISTRIBUTION_SURFACE", "conda")
    with mock.patch("anaconda_mcp.telemetry._detect_distribution_surface") as mock_detect:
        assert resolve_distribution_surface() == "conda"
        mock_detect.assert_not_called()


def test_resolve_distribution_surface_bogus_env_coerces_to_unknown(monkeypatch):
    """A non-empty, unrecognized env value coerces to 'unknown' without auto-detecting."""
    monkeypatch.setenv("ANACONDA_MCP_DISTRIBUTION_SURFACE", "bogus-surface")
    with mock.patch("anaconda_mcp.telemetry._detect_distribution_surface") as mock_detect:
        assert resolve_distribution_surface() == "unknown"
        mock_detect.assert_not_called()


def test_resolve_distribution_surface_unset_env_falls_through_to_detector(monkeypatch):
    """An unset/empty env value falls through to the (mocked) auto-detector."""
    monkeypatch.delenv("ANACONDA_MCP_DISTRIBUTION_SURFACE", raising=False)
    with mock.patch("anaconda_mcp.telemetry._detect_distribution_surface", return_value="uvx") as mock_detect:
        assert resolve_distribution_surface() == "uvx"
        mock_detect.assert_called_once()


def test_resolve_distribution_surface_debug_logs_rejected_value(monkeypatch, caplog):
    """An unrecognized override is debug-logged with the rejected value before coercion."""
    monkeypatch.setenv("ANACONDA_MCP_DISTRIBUTION_SURFACE", "bogus-surface")
    caplog.set_level(logging.DEBUG)

    resolve_distribution_surface()

    assert "bogus-surface" in caplog.text


def test_surface_env_isolation_fixture_clears_ambient_env():
    """Deterministic proof the autouse fixture clears the ambient env var.

    The autouse `_isolate_distribution_surface` fixture runs its delenv BEFORE this
    test body executes, so ANACONDA_MCP_DISTRIBUTION_SURFACE must already be absent
    here even if the host shell exported a recognized value (e.g. "mcpb") before
    pytest started. We assert directly on os.environ (not monkeypatch, which would
    only prove the test itself can clear it) and then confirm the resolver reaches
    the (patched) detector rather than short-circuiting.
    """
    assert "ANACONDA_MCP_DISTRIBUTION_SURFACE" not in os.environ
    with mock.patch("anaconda_mcp.telemetry._detect_distribution_surface", return_value="conda"):
        assert resolve_distribution_surface() == "conda"


def test_get_conda_meta_version_returns_version_when_record_present(monkeypatch, tmp_path):
    conda_meta = tmp_path / "conda-meta"
    conda_meta.mkdir()
    (conda_meta / "anaconda-mcp-1.0-0.json").write_text(_json.dumps({"name": "anaconda-mcp", "version": "1.0"}))
    monkeypatch.setattr("sys.prefix", str(tmp_path))
    assert _get_conda_meta_version("anaconda-mcp") == "1.0"


def test_get_conda_meta_version_returns_none_when_dir_absent(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.prefix", str(tmp_path))
    assert _get_conda_meta_version("anaconda-mcp") is None


def test_get_conda_meta_version_exact_name_rejects_extras_and_matches_real(monkeypatch, tmp_path):
    """conda-meta filename prefix match alone is NOT enough - the record's own
    JSON "name" field must equal the target exactly. A hyphen-ambiguous sibling
    package (anaconda-mcp-extras) must not false-match "anaconda-mcp"."""
    conda_meta = tmp_path / "conda-meta"
    conda_meta.mkdir()
    (conda_meta / "anaconda-mcp-extras-1.0-0.json").write_text(
        _json.dumps({"name": "anaconda-mcp-extras", "version": "1.0"})
    )
    monkeypatch.setattr("sys.prefix", str(tmp_path))
    assert _get_conda_meta_version("anaconda-mcp") is None

    (conda_meta / "anaconda-mcp-9.9-0.json").write_text(_json.dumps({"name": "anaconda-mcp", "version": "9.9"}))
    assert _get_conda_meta_version("anaconda-mcp") == "9.9"


def test_get_conda_meta_version_returns_none_on_non_dict_json(monkeypatch, tmp_path):
    """A valid-but-non-dict JSON payload (e.g. a JSON array) is a miss, not a crash."""
    conda_meta = tmp_path / "conda-meta"
    conda_meta.mkdir()
    (conda_meta / "anaconda-mcp-1.0-0.json").write_text(_json.dumps(["not", "a", "dict"]))
    monkeypatch.setattr("sys.prefix", str(tmp_path))
    assert _get_conda_meta_version("anaconda-mcp") is None


def test_read_installer_pip():
    with mock.patch("importlib.metadata.distribution") as mock_dist:
        mock_dist.return_value.read_text.return_value = "pip\n"
        assert _read_installer("anaconda-mcp") == "pip"


def test_read_installer_uv():
    with mock.patch("importlib.metadata.distribution") as mock_dist:
        mock_dist.return_value.read_text.return_value = "uv\n"
        assert _read_installer("anaconda-mcp") == "uv"


def test_read_installer_returns_none_on_package_not_found():
    with mock.patch(
        "importlib.metadata.distribution",
        side_effect=importlib.metadata.PackageNotFoundError("anaconda-mcp"),
    ):
        assert _read_installer("anaconda-mcp") is None


def test_read_installer_returns_none_on_unexpected_exception():
    """Totality backstop: _read_installer must not depend on the outer
    resolve_distribution_surface() try/except - it is independently total."""
    with mock.patch("importlib.metadata.distribution", side_effect=RuntimeError("boom")):
        assert _read_installer("anaconda-mcp") is None


def test_detect_distribution_surface_unknown_when_installer_metadata_raises():
    """End-to-end totality proof: a non-PackageNotFoundError exception from the
    metadata layer propagates through _read_installer (returns None) and through
    _detect_distribution_surface (returns "unknown"), never raising at either
    layer. This closes the gap where _read_installer's totality was tested in
    isolation but not proven through the full detection chain."""
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value=None),
        mock.patch("importlib.metadata.distribution", side_effect=RuntimeError("boom")),
    ):
        assert _detect_distribution_surface() == "unknown"
    _detect_distribution_surface.cache_clear()


def test_get_package_version_returns_unknown_on_unexpected_exception():
    """Totality backstop: _get_package_version must not depend on any caller's
    own try/except - it is independently total against any metadata-layer
    failure, not just PackageNotFoundError (e.g. corrupt dist-info raising a
    different exception type)."""
    with mock.patch("importlib.metadata.version", side_effect=RuntimeError("boom")):
        assert _get_package_version() == "unknown"


def test_detect_distribution_surface_unknown_when_version_metadata_raises():
    """End-to-end totality proof: with a conda-meta record present, a
    non-PackageNotFoundError exception from _get_package_version() (called to
    compare against the recorded conda-meta version) must not propagate out of
    _detect_distribution_surface - the ambiguous "can't verify" case falls back
    to trusting conda-meta rather than raising."""
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value="1.0.0"),
        mock.patch("importlib.metadata.version", side_effect=RuntimeError("boom")),
    ):
        assert _detect_distribution_surface() == "conda"
    _detect_distribution_surface.cache_clear()


def test_detect_distribution_surface_conda_precedence_over_pip_installer(monkeypatch):
    """The critical precedence test: when BOTH a conda-meta record AND a pip
    INSTALLER are present with MATCHING versions (this repo's own conda recipe
    pip-installs internally, see conda-build/meta.yaml), conda-meta MUST win -
    confirmed-fresh conda-meta beats a coexisting pip INSTALLER."""
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value="1.2.3"),
        mock.patch("anaconda_mcp.telemetry._get_package_version", return_value="1.2.3"),
        mock.patch("anaconda_mcp.telemetry._read_installer", return_value="pip"),
    ):
        assert _detect_distribution_surface() == "conda"
    _detect_distribution_surface.cache_clear()


def test_detect_distribution_surface_falls_back_to_unknown(monkeypatch):
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value=None),
        mock.patch("anaconda_mcp.telemetry._read_installer", return_value=None),
    ):
        assert _detect_distribution_surface() == "unknown"
    _detect_distribution_surface.cache_clear()


def test_detect_distribution_surface_pip_installer_maps_to_pip():
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value=None),
        mock.patch("anaconda_mcp.telemetry._read_installer", return_value="pip"),
    ):
        assert _detect_distribution_surface() == "pip"
    _detect_distribution_surface.cache_clear()


def test_detect_distribution_surface_uv_installer_maps_to_uvx():
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value=None),
        mock.patch("anaconda_mcp.telemetry._read_installer", return_value="uv"),
    ):
        assert _detect_distribution_surface() == "uvx"
    _detect_distribution_surface.cache_clear()


def test_detect_distribution_surface_conda_meta_version_match_confirms_fresh():
    """conda-meta version matches the installed version -> confirmed fresh, "conda" wins."""
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value="2.0.0"),
        mock.patch("anaconda_mcp.telemetry._get_package_version", return_value="2.0.0"),
    ):
        assert _detect_distribution_surface() == "conda"
    _detect_distribution_surface.cache_clear()


def test_detect_distribution_surface_conda_meta_version_mismatch_falls_through_to_installer():
    """conda-meta version DISAGREES with the installed version -> treated as
    stale/drifted (a later pip install overwrote conda-managed files); falls
    through to the real INSTALLER-based detection instead of trusting conda-meta."""
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value="1.0.0"),
        mock.patch("anaconda_mcp.telemetry._get_package_version", return_value="2.0.0"),
        mock.patch("anaconda_mcp.telemetry._read_installer", return_value="pip"),
    ):
        assert _detect_distribution_surface() == "pip"
    _detect_distribution_surface.cache_clear()


def test_detect_distribution_surface_conda_meta_missing_version_field_still_trusts_conda():
    """A matching conda-meta record with no verifiable version (empty string
    sentinel) cannot be proven stale, so we still trust it - unchanged lenient
    behavior for this unusual/corrupted-record case."""
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value=""),
        mock.patch("anaconda_mcp.telemetry._get_package_version", return_value="2.0.0"),
    ):
        assert _detect_distribution_surface() == "conda"
    _detect_distribution_surface.cache_clear()


def test_detect_distribution_surface_conda_meta_present_but_installed_version_unknown_still_trusts_conda():
    """conda-meta has a real version, but the installed version can't be
    determined ("unknown" sentinel from _get_package_version) - can't disprove
    freshness, so we still trust conda-meta."""
    _detect_distribution_surface.cache_clear()
    with (
        mock.patch("anaconda_mcp.telemetry._get_conda_meta_version", return_value="1.0.0"),
        mock.patch("anaconda_mcp.telemetry._get_package_version", return_value="unknown"),
    ):
        assert _detect_distribution_surface() == "conda"
    _detect_distribution_surface.cache_clear()


@pytest.fixture
def fake_conda_environment(monkeypatch, tmp_path):
    """Fakes a real conda install of anaconda-mcp: creates a conda-meta record
    (with a version matching the REAL installed version, so the drift check in
    _detect_distribution_surface confirms freshness) under a fresh sys.prefix so
    the REAL detection chain (_get_conda_meta_version -> _detect_distribution_surface
    -> resolve_distribution_surface) resolves to "conda" without mocking any
    detection internals directly."""
    installed_version = importlib.metadata.version("anaconda-mcp")
    conda_meta = tmp_path / "conda-meta"
    conda_meta.mkdir()
    (conda_meta / f"anaconda-mcp-{installed_version}-0.json").write_text(
        _json.dumps({"name": "anaconda-mcp", "version": installed_version})
    )
    monkeypatch.setattr("sys.prefix", str(tmp_path))
    _detect_distribution_surface.cache_clear()
    yield
    _detect_distribution_surface.cache_clear()


def test_smoke_emit_event_workflow_with_conda_surface(fake_conda_environment, mock_make_request):
    """End-to-end smoke test: a real fake-conda environment flows through the
    genuine detection chain into both emit_event() sinks, with only the network
    boundaries (SnakeEyes._make_request, log_event) stubbed out - no mocking of
    detection internals, no real network calls."""
    with mock.patch("anaconda_mcp.telemetry.log_event") as mock_log_event:
        emit_event(MetricNames.START_SERVER.value, {"smoke": "test"}, blocking=True)

    # snake-eyes sink: sent, authenticated, event_params present, but NO
    # distribution_surface (by design - that dimension is OTel-only).
    assert mock_make_request.call_count == 1
    snake_eyes_endpoint, snake_eyes_payload, _ = mock_make_request.call_args[0]
    assert snake_eyes_endpoint == "api/snake-eyes/record"
    assert snake_eyes_payload["event_params"]["smoke"] == "test"
    assert "distribution_surface" not in snake_eyes_payload["event_params"]

    # OTel sink: distribution_surface == "conda", derived from the REAL
    # detection chain (fake conda-meta record), not a mocked resolver.
    assert mock_log_event.call_count == 1
    otel_attrs = mock_log_event.call_args.kwargs["attributes"]
    assert otel_attrs["distribution.surface"] == "conda"
    assert otel_attrs["schema_version"] == "1"


def test_smoke_emit_tool_metrics_workflow_with_conda_surface(fake_conda_environment):
    """End-to-end smoke test: fake-conda environment flows through the real
    detection chain into the tool-metrics OTel sink, network boundary stubbed."""
    with (
        mock.patch("anaconda_mcp.telemetry._otel_count") as mock_count,
        mock.patch("anaconda_mcp.telemetry._otel_histogram") as mock_hist,
    ):
        _emit_tool_metrics("smoke_tool", 42.0, is_error=False)

    assert mock_count.call_count == 1
    assert mock_hist.call_count == 1
    for call in (mock_count, mock_hist):
        attrs = call.call_args.kwargs["attributes"]
        assert attrs["distribution_surface"] == "conda"
        assert attrs["tool"] == "smoke_tool"


def test_base_dimensions_happy_path_has_exactly_five_keys():
    """On the happy path, exactly the 5 documented keys are present."""
    result = _base_dimensions()

    assert set(result.keys()) == BASE_DIMENSION_KEYS
    assert result["schema_version"] == "1"


def test_base_dimensions_fault_isolation_on_single_resolver_failure():
    """A single failing resolver omits only its own key; the rest still return."""
    with mock.patch("anaconda_mcp.telemetry.get_or_create_install_id", side_effect=RuntimeError("boom")):
        result = _base_dimensions()

    assert "install.id" not in result
    assert set(result.keys()) == BASE_DIMENSION_KEYS - {"install.id"}


def test_base_dimensions_keys_do_not_collide_with_reserved_names():
    """None of the 5 dimension keys collide with cli-base's `source`/`plugin` or `user.id`."""
    result = _base_dimensions()

    assert not ({"source", "plugin", "user.id"} & set(result.keys()))


def test_emit_event_base_dimensions_are_not_overridable_by_caller_params(mock_make_request):
    """Base dimensions are authoritative: a caller-supplied event_params key
    that collides with a base-dimension name is ignored on the OTel path, not
    silently allowed to override the trusted value (closes a footgun where a
    future caller forwarding untrusted keys could bypass e.g. the closed
    KNOWN_DISTRIBUTION_SURFACES enum via distribution.surface)."""
    with mock.patch("anaconda_mcp.telemetry.log_event") as mock_log_event:
        emit_event(
            MetricNames.START_SERVER.value,
            {"distribution.surface": "totally-untrusted-value"},
            blocking=True,
        )

    otel_attrs = mock_log_event.call_args.kwargs["attributes"]
    assert otel_attrs["distribution.surface"] in KNOWN_DISTRIBUTION_SURFACES
    assert otel_attrs["distribution.surface"] != "totally-untrusted-value"
