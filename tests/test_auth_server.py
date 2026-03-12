from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
import requests

from anaconda_mcp.auth_server import (
    _build_session_for_url,
    _channel_requires_auth,
    _read_conda_channels,
    _resolve_channel_url,
    auth_check_channel,
    auth_status,
    conda_list_channels,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_ACCOUNT = {
    "user": {
        "username": "test-user",
        "email": "test-user@example.com",
        "first_name": "Test",
        "last_name": "User",
    },
    "subscriptions": [
        {
            "id": "some-id",
            "product_code": "security_subscription",
            "expires_at": "2035-01-02T00:00:00Z",
        }
    ],
}


def _make_response(status_code: int) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------------------
# auth_status tests
# ---------------------------------------------------------------------------


class TestAuthStatus:
    def test_returns_unauthenticated_when_no_token(self):
        with patch("anaconda_mcp.auth_server._get_authenticated_client", return_value=None):
            result = auth_status()

        assert result["is_authenticated"] is False
        assert result["user"] is None
        assert result["subscriptions"] == []
        assert result["is_error"] is False

    def test_returns_user_info_when_authenticated(self):
        mock_client = MagicMock()
        mock_client.account = MOCK_ACCOUNT

        with patch("anaconda_mcp.auth_server._get_authenticated_client", return_value=mock_client):
            result = auth_status()

        assert result["is_authenticated"] is True
        assert result["is_error"] is False
        assert result["user"]["username"] == "test-user"
        assert result["user"]["email"] == "test-user@example.com"
        assert result["user"]["first_name"] == "Test"
        assert result["user"]["last_name"] == "User"

    def test_returns_subscriptions_when_authenticated(self):
        mock_client = MagicMock()
        mock_client.account = MOCK_ACCOUNT

        with patch("anaconda_mcp.auth_server._get_authenticated_client", return_value=mock_client):
            result = auth_status()

        assert len(result["subscriptions"]) == 1
        assert result["subscriptions"][0]["product_code"] == "security_subscription"
        assert result["subscriptions"][0]["expires_at"] == "2035-01-02T00:00:00Z"

    def test_returns_empty_subscriptions_when_none_on_account(self):
        mock_client = MagicMock()
        mock_client.account = {"user": MOCK_ACCOUNT["user"], "subscriptions": []}

        with patch("anaconda_mcp.auth_server._get_authenticated_client", return_value=mock_client):
            result = auth_status()

        assert result["subscriptions"] == []

    def test_returns_unauthenticated_on_account_fetch_error(self):
        mock_client = MagicMock()
        type(mock_client).account = mock.PropertyMock(side_effect=Exception("network error"))

        with patch("anaconda_mcp.auth_server._get_authenticated_client", return_value=mock_client):
            result = auth_status()

        assert result["is_authenticated"] is False
        assert result["is_error"] is False


# ---------------------------------------------------------------------------
# _resolve_channel_url tests
# ---------------------------------------------------------------------------


class TestResolveChannelUrl:
    def test_full_https_url_returned_unchanged(self):
        url = "https://repo.anaconda.cloud/repo/main"
        assert _resolve_channel_url(url) == url

    def test_short_name_maps_to_conda_anaconda_org(self):
        assert _resolve_channel_url("conda-forge") == "https://conda.anaconda.org/conda-forge"
        assert _resolve_channel_url("bioconda") == "https://conda.anaconda.org/bioconda"
        assert _resolve_channel_url("my-org/label/dev") == "https://conda.anaconda.org/my-org/label/dev"

    def test_defaults_resolved_from_conda_config(self):
        conda_output = (
            "default_channels:\n  - https://repo.anaconda.cloud/repo/main\n  - https://repo.anaconda.cloud/repo/r\n"
        )
        with patch("anaconda_mcp.auth_server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=conda_output)
            result = _resolve_channel_url("defaults")
        assert result == "https://repo.anaconda.cloud/repo/main"

    def test_defaults_falls_back_when_conda_unavailable(self):
        with patch("anaconda_mcp.auth_server.subprocess.run", side_effect=FileNotFoundError):
            result = _resolve_channel_url("defaults")
        assert result == "https://repo.anaconda.cloud/repo/main"

    def test_defaults_falls_back_when_conda_returns_no_urls(self):
        with patch("anaconda_mcp.auth_server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="default_channels: []\n")
            result = _resolve_channel_url("defaults")
        assert result == "https://repo.anaconda.cloud/repo/main"


# ---------------------------------------------------------------------------
# _build_session_for_url tests
# ---------------------------------------------------------------------------


class TestBuildSessionForUrl:
    def test_repo_anaconda_cloud_uses_bearer_token(self):
        with patch("anaconda_mcp.auth_server._get_repo_cloud_token", return_value="mytoken"):
            session, authenticated = _build_session_for_url("https://repo.anaconda.cloud/repo/main")
        assert authenticated is True
        assert session.headers.get("Authorization") == "Bearer mytoken"

    def test_repo_anaconda_cloud_unauthenticated_when_no_token(self):
        with patch("anaconda_mcp.auth_server._get_repo_cloud_token", return_value=None):
            session, authenticated = _build_session_for_url("https://repo.anaconda.cloud/repo/main")
        assert authenticated is False
        assert "Authorization" not in session.headers

    def test_conda_anaconda_org_uses_plain_session(self):
        session, authenticated = _build_session_for_url("https://conda.anaconda.org/conda-forge")
        assert authenticated is False
        assert isinstance(session, requests.Session)
        assert "Authorization" not in session.headers

    def test_other_hostname_uses_base_client_when_authenticated(self):
        mock_client = MagicMock()
        with patch("anaconda_mcp.auth_server._get_authenticated_client", return_value=mock_client):
            session, authenticated = _build_session_for_url("https://custom.channel.example.com/myorg")
        assert authenticated is True
        assert session is mock_client


# ---------------------------------------------------------------------------
# auth_check_channel tests
# ---------------------------------------------------------------------------

CHANNEL_URL = "https://repo.anaconda.cloud/repo/main"


class TestAuthCheckChannel:
    def _mock_session(self, status_code: int, authenticated: bool = True) -> tuple:
        """Returns (mock_session, mock_build_patch) for use in tests."""
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(status_code)
        return mock_session, authenticated

    def test_returns_accessible_true_on_200(self):
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(200)
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, True)):
            result = auth_check_channel(CHANNEL_URL)
        assert result["accessible"] is True
        assert result["authenticated"] is True
        assert result["is_error"] is False

    def test_returns_accessible_true_on_302(self):
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(302)
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, True)):
            result = auth_check_channel(CHANNEL_URL)
        assert result["accessible"] is True

    def test_returns_401_details_when_not_authenticated(self):
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(401)
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, False)):
            result = auth_check_channel(CHANNEL_URL)
        assert result["accessible"] is False
        assert result["authenticated"] is False
        assert "401" in result["error"]
        assert "anaconda login" in result["error"]
        assert result["is_error"] is False

    def test_returns_403_details_when_authenticated_but_no_access(self):
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(403)
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, True)):
            result = auth_check_channel(CHANNEL_URL)
        assert result["accessible"] is False
        assert result["authenticated"] is True
        assert "403" in result["error"]
        assert result["is_error"] is False

    def test_returns_error_on_network_failure(self):
        mock_session = MagicMock()
        mock_session.head.side_effect = requests.RequestException("connection refused")
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, True)):
            result = auth_check_channel(CHANNEL_URL)
        assert result["accessible"] is False
        assert "Network error" in result["error"]
        assert result["is_error"] is False

    def test_returns_unexpected_status_message(self):
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(500)
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, True)):
            result = auth_check_channel(CHANNEL_URL)
        assert result["accessible"] is False
        assert "500" in result["error"]
        assert result["is_error"] is False

    def test_probe_url_appends_repodata_path(self):
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(200)
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, True)):
            auth_check_channel(CHANNEL_URL)
        call_url = mock_session.head.call_args[0][0]
        assert call_url.endswith("/noarch/repodata.json")

    def test_probe_url_not_modified_when_already_json(self):
        json_url = f"{CHANNEL_URL}/linux-64/repodata.json"
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(200)
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, True)):
            auth_check_channel(json_url)
        call_url = mock_session.head.call_args[0][0]
        assert call_url == json_url

    def test_short_form_channel_name_is_resolved(self):
        """Short-form names are resolved before the probe; the original name is preserved in response."""
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(200)
        with patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, False)):
            result = auth_check_channel("conda-forge")
        # Original name preserved in response
        assert result["channel_url"] == "conda-forge"
        # Probe was made against the resolved URL
        call_url = mock_session.head.call_args[0][0]
        assert "conda.anaconda.org/conda-forge" in call_url

    def test_defaults_short_name_resolves_and_probes_repo_cloud(self):
        """'defaults' resolves to repo.anaconda.cloud via conda config."""
        conda_output = "default_channels:\n  - https://repo.anaconda.cloud/repo/main\n"
        mock_session = MagicMock()
        mock_session.head.return_value = _make_response(200)
        with (
            patch("anaconda_mcp.auth_server.subprocess.run") as mock_conda,
            patch("anaconda_mcp.auth_server._build_session_for_url", return_value=(mock_session, True)),
        ):
            mock_conda.return_value = MagicMock(stdout=conda_output)
            result = auth_check_channel("defaults")
        assert result["channel_url"] == "defaults"
        call_url = mock_session.head.call_args[0][0]
        assert "repo.anaconda.cloud" in call_url


# ---------------------------------------------------------------------------
# _channel_requires_auth tests
# ---------------------------------------------------------------------------


class TestChannelRequiresAuth:
    def test_repo_anaconda_cloud_requires_auth(self):
        assert _channel_requires_auth("https://repo.anaconda.cloud/repo/main") is True
        assert _channel_requires_auth("https://repo.anaconda.cloud/repo/r") is True

    def test_conda_anaconda_org_does_not_require_auth(self):
        assert _channel_requires_auth("https://conda.anaconda.org/conda-forge") is False
        assert _channel_requires_auth("https://conda.anaconda.org/bioconda") is False

    def test_embedded_token_url_requires_auth(self):
        assert _channel_requires_auth("https://conda.anaconda.org/t/abc123/anaconda-connector") is True

    def test_community_org_channel_does_not_require_auth(self):
        assert _channel_requires_auth("https://conda.anaconda.org/anaconda-cloud/label/dev") is False


# ---------------------------------------------------------------------------
# _read_conda_channels tests
# ---------------------------------------------------------------------------


class TestReadCondaChannels:
    def test_returns_channels_from_conda_api(self):
        mock_context = MagicMock()
        mock_context.channels = ("conda-forge", "defaults")
        mock_context.default_channels = ("https://repo.anaconda.cloud/repo/main",)

        with (
            patch("anaconda_mcp.auth_server.conda_context", mock_context),
            patch("anaconda_mcp.auth_server.reset_context"),
            patch("anaconda_mcp.auth_server.Channel", type("Channel", (), {})),
        ):
            channels, default_channels = _read_conda_channels()

        assert "conda-forge" in channels
        assert "https://repo.anaconda.cloud/repo/main" in default_channels

    def test_raises_when_reset_context_fails(self):
        with patch("anaconda_mcp.auth_server.reset_context", side_effect=RuntimeError("conda broken")):
            with pytest.raises(RuntimeError):
                _read_conda_channels()


# ---------------------------------------------------------------------------
# conda_list_channels tests
# ---------------------------------------------------------------------------


class TestCondaListChannels:
    def _patch_read(self, channels, default_channels):
        return patch(
            "anaconda_mcp.auth_server._read_conda_channels",
            return_value=(channels, default_channels),
        )

    def test_returns_channels_list_with_required_fields(self):
        with self._patch_read(["conda-forge"], ["https://repo.anaconda.cloud/repo/main"]):
            result = conda_list_channels()

        assert result["is_error"] is False
        assert len(result["channels"]) == 2
        for entry in result["channels"]:
            assert "name" in entry
            assert "url" in entry
            assert "source" in entry
            assert "requires_auth" in entry

    def test_channels_source_label(self):
        with self._patch_read(["conda-forge"], ["https://repo.anaconda.cloud/repo/main"]):
            result = conda_list_channels()

        sources = {e["name"]: e["source"] for e in result["channels"]}
        assert sources["conda-forge"] == "channels"
        assert sources["https://repo.anaconda.cloud/repo/main"] == "default_channels"

    def test_repo_cloud_channel_marked_requires_auth(self):
        with self._patch_read([], ["https://repo.anaconda.cloud/repo/main"]):
            result = conda_list_channels()

        entry = result["channels"][0]
        assert entry["requires_auth"] is True

    def test_community_channel_marked_no_auth(self):
        with self._patch_read(["conda-forge"], []):
            result = conda_list_channels()

        entry = result["channels"][0]
        assert entry["requires_auth"] is False
        assert entry["url"] == "https://conda.anaconda.org/conda-forge"

    def test_short_form_name_is_resolved_to_full_url(self):
        with self._patch_read(["my-org"], []):
            result = conda_list_channels()

        entry = result["channels"][0]
        assert entry["name"] == "my-org"
        assert entry["url"] == "https://conda.anaconda.org/my-org"

    def test_embedded_token_channel_marked_requires_auth(self):
        token_url = "https://conda.anaconda.org/t/abc123/anaconda-connector"
        with self._patch_read([token_url], []):
            result = conda_list_channels()

        entry = result["channels"][0]
        assert entry["requires_auth"] is True

    def test_returns_empty_channels_when_conda_unavailable(self):
        with self._patch_read([], []):
            result = conda_list_channels()

        assert result["is_error"] is False
        assert result["channels"] == []

    def test_returns_is_error_true_on_exception(self):
        with patch("anaconda_mcp.auth_server._read_conda_channels", side_effect=RuntimeError("boom")):
            result = conda_list_channels()

        assert result["is_error"] is True
        assert "error" in result
