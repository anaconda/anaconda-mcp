import base64
import json
import logging
from unittest import mock

import pytest
from click.testing import CliRunner

from anaconda_mcp.cli import cli
from conftest import TEST_USER_ID, VALID_TEST_JWT

logger = logging.getLogger(__name__)


def _build_jwt(sub: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).rstrip(b"=").decode()
    return f"h.{payload}.s"


def _build_jwt_raw_payload(payload_obj: object) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(payload_obj).encode()).rstrip(b"=").decode()
    return f"h.{payload}.s"


@pytest.fixture
def mock_get_auth_token(mocked_token):
    with mock.patch("anaconda_mcp.auth.get_auth_token") as m:
        m.return_value = mocked_token
        yield m


@pytest.fixture
def mock_serve_command():
    with mock.patch("anaconda_mcp.cli._serve") as m:
        m.return_value = 0
        yield m


@pytest.fixture
def mock_base_client():
    with mock.patch("anaconda_mcp.auth.BaseClient") as m:
        m.return_value.account = {"user": {"created_at": "2020-01-01T00:00:00Z"}}
        yield m


@pytest.fixture
def mock_snake_eyes():
    with mock.patch("anaconda_mcp.auth.SnakeEyes") as m:
        yield m


async def test_cli_gates_on_token_not_found(mock_token_info_load):
    mock_token_info_load.return_value = None

    runner = CliRunner()
    result = runner.invoke(cli, ["clients"])

    assert result.exit_code == 1


async def test_serve_exits_immediately_without_token():
    # Given - no token available
    runner = CliRunner()

    # When - invoke serve with no token (override the autouse fixture)
    with mock.patch("anaconda_mcp.cli.get_auth_token", return_value=None):
        with mock.patch("anaconda_mcp.cli.Path.exists", return_value=True):
            result = runner.invoke(cli, ["serve"])

    # Then - should exit with code 1
    assert result.exit_code == 1


_OTHER_UUID = "11111111-2222-3333-4444-555555555555"


@pytest.mark.parametrize(
    "token, expected",
    [
        (VALID_TEST_JWT, (TEST_USER_ID, "authenticated")),
        (_build_jwt(_OTHER_UUID), (_OTHER_UUID, "authenticated")),
        (None, (None, "no-local-token")),
        ("", (None, "no-local-token")),
        ("garbage", (None, "bad-token")),
        ("a.b", (None, "bad-token")),
        ("....", (None, "bad-token")),
        (_build_jwt_raw_payload({"sub": 123}), (None, "bad-token")),
        (_build_jwt_raw_payload({"sub": None}), (None, "bad-token")),
        (_build_jwt_raw_payload({"not_sub": "x"}), (None, "bad-token")),
        (_build_jwt_raw_payload(["not", "an", "object"]), (None, "bad-token")),
    ],
)
def test_resolve_user_id_branches(token, expected):
    from anaconda_mcp.auth import resolve_user_id

    with mock.patch("anaconda_mcp.auth.get_auth_token", return_value=token):
        assert resolve_user_id() == expected


@pytest.mark.parametrize("token", ["", "a.b", "....", "garbage", "a.!!!.b", "a." + "A" * 5 + ".b"])
def test_resolve_user_id_never_raises(token):
    from anaconda_mcp.auth import resolve_user_id

    with mock.patch("anaconda_mcp.auth.get_auth_token", return_value=token):
        result = resolve_user_id()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] is None or isinstance(result[0], str)
        assert result[1] in {"authenticated", "no-local-token", "bad-token"}


def test_resolve_user_id_caches_authenticated_result():
    import anaconda_mcp.auth
    from anaconda_mcp.auth import resolve_user_id

    anaconda_mcp.auth._reset_user_id_cache()
    fake = mock.Mock(return_value=VALID_TEST_JWT)
    with mock.patch("anaconda_mcp.auth.get_auth_token", fake):
        first = resolve_user_id()
        second = resolve_user_id()

    assert first == (TEST_USER_ID, "authenticated")
    assert second == (TEST_USER_ID, "authenticated")
    assert fake.call_count == 1


def test_resolve_user_id_does_not_cache_no_local_token():
    import anaconda_mcp.auth
    from anaconda_mcp.auth import resolve_user_id

    anaconda_mcp.auth._reset_user_id_cache()
    fake = mock.Mock(return_value=None)
    with mock.patch("anaconda_mcp.auth.get_auth_token", fake):
        first = resolve_user_id()
        second = resolve_user_id()

    assert first == (None, "no-local-token")
    assert second == (None, "no-local-token")
    assert fake.call_count == 2


def test_resolve_user_id_does_not_cache_bad_token():
    import anaconda_mcp.auth
    from anaconda_mcp.auth import resolve_user_id

    anaconda_mcp.auth._reset_user_id_cache()
    fake = mock.Mock(return_value="garbage")
    with mock.patch("anaconda_mcp.auth.get_auth_token", fake):
        first = resolve_user_id()
        second = resolve_user_id()

    assert first == (None, "bad-token")
    assert second == (None, "bad-token")
    assert fake.call_count == 2
