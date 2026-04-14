"""Tests for DahuaDSSClient service layer"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from dahua_dss.client import DahuaDSSClient


@pytest.fixture
def client() -> DahuaDSSClient:
    return DahuaDSSClient("192.168.1.1", port=8088, use_https=False)


# ---------------------------------------------------------------------------
# compute_signature
# ---------------------------------------------------------------------------


def test_compute_signature_is_deterministic() -> None:
    sig1 = DahuaDSSClient.compute_signature("admin", "pass", "realm", "key")
    sig2 = DahuaDSSClient.compute_signature("admin", "pass", "realm", "key")
    assert sig1 == sig2


def test_compute_signature_differs_on_different_inputs() -> None:
    sig1 = DahuaDSSClient.compute_signature("admin", "pass1", "realm", "key")
    sig2 = DahuaDSSClient.compute_signature("admin", "pass2", "realm", "key")
    assert sig1 != sig2


# ---------------------------------------------------------------------------
# set_token / clear_token
# ---------------------------------------------------------------------------


def test_set_token(client: DahuaDSSClient) -> None:
    client.set_token("abc123")
    assert client.token == "abc123"
    assert client.session.headers[DahuaDSSClient.AUTH_TOKEN_HEADER] == "abc123"


def test_clear_token(client: DahuaDSSClient) -> None:
    client.set_token("abc123")
    client.clear_token()
    assert client.token is None
    assert DahuaDSSClient.AUTH_TOKEN_HEADER not in client.session.headers


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


def _make_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def test_login_success(client: DahuaDSSClient) -> None:
    challenge = {"realm": "dss", "randomKey": "rk1"}
    token_resp = {"token": "tok999"}

    with patch.object(
        client.session,
        "post",
        side_effect=[
            _make_response(401, challenge),
            _make_response(200, token_resp),
        ],
    ):
        result = client.login("admin", "secret")

    assert result is True
    assert client.token == "tok999"
    assert client.username == "admin"


def test_login_no_token_in_response(client: DahuaDSSClient) -> None:
    challenge = {"realm": "dss", "randomKey": "rk1"}

    with patch.object(
        client.session,
        "post",
        side_effect=[
            _make_response(401, challenge),
            _make_response(200, {}),  # no "token" key
        ],
    ):
        result = client.login("admin", "secret")

    assert result is False
    assert client.token is None


def test_login_network_error(client: DahuaDSSClient) -> None:
    with patch.object(client.session, "post", side_effect=requests.exceptions.ConnectionError):
        result = client.login("admin", "secret")

    assert result is False


def test_login_unexpected_first_status(client: DahuaDSSClient) -> None:
    """If first response is not 401, login should return False."""
    resp = _make_response(200, {})
    resp.raise_for_status = MagicMock()

    with patch.object(client.session, "post", return_value=resp):
        result = client.login("admin", "secret")

    assert result is False


def test_login_retries_after_2004(client: DahuaDSSClient) -> None:
    """code 2004 (already logged in) waits for session expiry then retries successfully."""
    challenge = {"realm": "dss", "randomKey": "rk1"}
    already_logged_in = {"code": 2004, "desc": "The user has logged in."}
    token_resp = {"token": "tok_retry"}

    with (
        patch("dahua_dss.client.time.sleep") as mock_sleep,
        patch.object(
            client.session,
            "post",
            side_effect=[
                _make_response(401, challenge),  # login step 1
                _make_response(200, already_logged_in),  # login step 2 → 2004
                _make_response(401, challenge),  # retry login step 1
                _make_response(200, token_resp),  # retry login step 2
            ],
        ),
    ):
        result = client.login("admin", "secret")

    assert result is True
    assert client.token == "tok_retry"
    mock_sleep.assert_called_once_with(31)


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


def test_logout_success(client: DahuaDSSClient) -> None:
    client.set_token("tok")
    resp = _make_response(200, {})
    with patch.object(client.session, "post", return_value=resp):
        result = client.logout()

    assert result is True
    assert client.token is None


def test_logout_not_logged_in(client: DahuaDSSClient) -> None:
    assert client.logout() is False


def test_logout_clears_token_even_on_error(client: DahuaDSSClient) -> None:
    client.set_token("tok")
    with patch.object(client.session, "post", side_effect=requests.exceptions.ConnectionError):
        client.logout()

    assert client.token is None


# ---------------------------------------------------------------------------
# get_device_tree
# ---------------------------------------------------------------------------


def test_get_device_tree_returns_none_when_not_authenticated(client: DahuaDSSClient) -> None:
    assert client.get_device_tree() is None


def test_get_device_tree_success(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    devices = [{"code": "dev1", "name": "Camera 1"}]
    resp = _make_response(200, {"data": {"devices": devices}})

    with patch.object(client.session, "post", return_value=resp):
        result = client.get_device_tree()

    assert result == devices


def test_get_device_tree_missing_devices_key(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    resp = _make_response(200, {"data": {}})

    with patch.object(client.session, "post", return_value=resp):
        result = client.get_device_tree()

    assert result is None


def test_get_device_tree_network_error(client: DahuaDSSClient) -> None:
    client.set_token("tok")
    with patch.object(client.session, "post", side_effect=requests.exceptions.ConnectionError):
        result = client.get_device_tree()

    assert result is None


# ---------------------------------------------------------------------------
# get_live_stream_url
# ---------------------------------------------------------------------------


def test_get_live_stream_url_not_authenticated(client: DahuaDSSClient) -> None:
    assert client.get_live_stream_url("ch1") is None


def test_get_live_stream_url_success(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    resp = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {"url": "rtsp://host/stream", "token": "t1"},
        },
    )

    with patch.object(client.session, "post", return_value=resp):
        url = client.get_live_stream_url("ch1", stream_type=1)

    assert url == "rtsp://host/stream?token=t1"


def test_get_live_stream_url_api_error(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    resp = _make_response(200, {"code": 9999, "desc": "error"})

    with patch.object(client.session, "post", return_value=resp):
        url = client.get_live_stream_url("ch1")

    assert url is None


# ---------------------------------------------------------------------------
# search_recordings
# ---------------------------------------------------------------------------


def test_search_recordings_not_authenticated(client: DahuaDSSClient) -> None:
    assert client.search_recordings("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00") is None


def test_search_recordings_success(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    records = [{"startTime": "1700000000", "endTime": "1700003600"}]
    resp = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {"records": records},
        },
    )

    with patch.object(client.session, "post", return_value=resp):
        result = client.search_recordings("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00")

    assert result == records


def test_search_recordings_empty(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    resp = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {},  # no "records" key
        },
    )

    with patch.object(client.session, "post", return_value=resp):
        result = client.search_recordings("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00")

    assert result == []


def test_search_recordings_api_error(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    resp = _make_response(200, {"code": 9999, "desc": "error"})

    with patch.object(client.session, "post", return_value=resp):
        result = client.search_recordings("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00")

    assert result is None


# ---------------------------------------------------------------------------
# get_playback_stream_url
# ---------------------------------------------------------------------------


def test_get_playback_stream_url_not_authenticated(client: DahuaDSSClient) -> None:
    assert client.get_playback_stream_url("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00") is None


def test_get_playback_stream_url_success(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    # search_recordings returns one record with streamId
    search_resp = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {"records": [{"streamId": "112", "startTime": "1735689600", "endTime": "1735693200"}]},
        },
    )
    playback_resp = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {"url": "rtsp://host/playback", "token": "pb_tok"},
        },
    )

    with patch.object(client.session, "post", side_effect=[search_resp, playback_resp]) as mock_post:
        url = client.get_playback_stream_url(
            "ch1",
            "2025-01-01 00:00:00",
            "2025-01-01 01:00:00",
            stream_type=1,
            record_source=2,
        )

    assert url == "rtsp://host/playback?token=pb_tok"
    playback_body = mock_post.call_args[1]["json"]["data"]
    assert playback_body["streamId"] == "112"
    assert playback_body["channelId"] == "ch1"


def test_get_playback_stream_url_explicit_stream_id(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    """When stream_id is provided explicitly, no search_recordings call is made."""
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    resp = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {"url": "rtsp://host/playback", "token": "pb_tok"},
        },
    )

    with patch.object(client.session, "post", return_value=resp) as mock_post:
        url = client.get_playback_stream_url("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00", stream_id="999")

    assert url == "rtsp://host/playback?token=pb_tok"
    assert mock_post.call_count == 1  # only the playback call, no search
    assert mock_post.call_args[1]["json"]["data"]["streamId"] == "999"


def test_get_playback_stream_url_fallback_source(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    """Falls back to the other record_source when primary returns no recordings."""
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    empty_search = _make_response(200, {"code": DahuaDSSClient.SUCCESS_CODE, "data": {}})
    fallback_search = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {"records": [{"streamId": "77", "startTime": "1735689600", "endTime": "1735693200"}]},
        },
    )
    playback_resp = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {"url": "rtsp://host/pb", "token": "t"},
        },
    )

    with patch.object(client.session, "post", side_effect=[empty_search, fallback_search, playback_resp]):
        url = client.get_playback_stream_url("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00", record_source=3)

    assert url == "rtsp://host/pb?token=t"


def test_get_playback_stream_url_api_error(client: DahuaDSSClient, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client.set_token("tok")
    search_resp = _make_response(
        200,
        {
            "code": DahuaDSSClient.SUCCESS_CODE,
            "data": {"records": [{"streamId": "1", "startTime": "1735689600", "endTime": "1735693200"}]},
        },
    )
    error_resp = _make_response(200, {"code": 9999, "desc": "error"})

    with patch.object(client.session, "post", side_effect=[search_resp, error_resp]):
        url = client.get_playback_stream_url("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00")

    assert url is None


def test_get_playback_stream_url_network_error(client: DahuaDSSClient) -> None:
    client.set_token("tok")
    with patch.object(client.session, "post", side_effect=requests.exceptions.ConnectionError):
        url = client.get_playback_stream_url("ch1", "2025-01-01 00:00:00", "2025-01-01 01:00:00", stream_id="1")

    assert url is None
