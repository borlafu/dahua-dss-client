"""Tests for dahua_dss/cli.py presentation layer"""

from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from dahua_dss.cli import (
    display_device_table,
    display_device_tree,
    display_recordings,
    get_default_time_range,
    main,
)

# ---------------------------------------------------------------------------
# get_default_time_range
# ---------------------------------------------------------------------------


def test_get_default_time_range_format() -> None:
    start, end = get_default_time_range()
    datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    datetime.strptime(end, "%Y-%m-%d %H:%M:%S")


def test_get_default_time_range_24h_gap() -> None:
    start, end = get_default_time_range()
    delta = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") - datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    assert delta == timedelta(hours=24)


# ---------------------------------------------------------------------------
# display_device_tree
# ---------------------------------------------------------------------------

DEVICE_ONLINE = {
    "name": "Cam1",
    "status": "1",
    "category": "IPC",
    "type": "IPC",
    "code": "DEV001",
    "sourceType": "1",
    "deviceModelStr": "X",
    "model": "Y",
    "orgCode": "ORG1",
    "units": [],
}
DEVICE_OFFLINE = {**DEVICE_ONLINE, "status": "0", "name": "Cam2"}
DEVICE_WITH_CHANNELS = {
    **DEVICE_ONLINE,
    "units": [
        {
            "unitType": "Video",
            "unitSeq": "0",
            "assistStream": "0",
            "zeroChnEncode": "0",
            "streamType": "1",
            "channels": [{"channelName": "Ch1", "channelCode": "CH001", "channelSeq": "0", "status": "1"}],
        }
    ],
}


def test_display_device_tree_empty(capsys: pytest.CaptureFixture) -> None:
    with patch("dahua_dss.cli.console") as mock_console:
        display_device_tree([])
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0][0]
        assert "No devices found" in args


def test_display_device_tree_online_offline() -> None:
    with patch("dahua_dss.cli.console"), patch("builtins.open", mock_open()):
        # Should not raise
        display_device_tree([DEVICE_ONLINE, DEVICE_OFFLINE])


def test_display_device_tree_writes_file() -> None:
    m = mock_open()
    with patch("dahua_dss.cli.console"), patch("builtins.open", m):
        display_device_tree([DEVICE_ONLINE])
    m.assert_called_once_with("device_tree.txt", "w")


def test_display_device_tree_with_channels() -> None:
    with patch("dahua_dss.cli.console"), patch("builtins.open", mock_open()):
        display_device_tree([DEVICE_WITH_CHANNELS])


# ---------------------------------------------------------------------------
# display_device_table
# ---------------------------------------------------------------------------


def test_display_device_table_empty() -> None:
    with patch("dahua_dss.cli.console") as mock_console:
        display_device_table([])
        args = mock_console.print.call_args[0][0]
        assert "No devices found" in args


def test_display_device_table_channel_count() -> None:
    device = {
        **DEVICE_ONLINE,
        "units": [
            {"channels": [{"c": 1}, {"c": 2}]},
            {"channels": [{"c": 3}]},
        ],
    }
    with patch("dahua_dss.cli.console") as mock_console:
        display_device_table([device])
        # Table was printed — just verify no exception and console.print called
        assert mock_console.print.called


# ---------------------------------------------------------------------------
# display_recordings
# ---------------------------------------------------------------------------

RECORDING = {
    "channelId": "CH001",
    "streamType": "1",
    "recordSource": "2",
    "recordType": "Regular",
    "startTime": "1700000000",
    "endTime": "1700003600",
    "fileLength": str(10 * 1024 * 1024),
    "recordName": "rec1",
}


def test_display_recordings_empty() -> None:
    with patch("dahua_dss.cli.console") as mock_console:
        display_recordings([])
        args = mock_console.print.call_args[0][0]
        assert "No recordings found" in args


def test_display_recordings_renders_without_error() -> None:
    with patch("dahua_dss.cli.console"):
        display_recordings([RECORDING])


def test_display_recordings_missing_file_length() -> None:
    rec = {k: v for k, v in RECORDING.items() if k != "fileLength"}
    with patch("dahua_dss.cli.console"):
        display_recordings([rec])  # should not raise


# ---------------------------------------------------------------------------
# main() — integration via mocked client + prompts
# ---------------------------------------------------------------------------


def _mock_client() -> MagicMock:
    client = MagicMock()
    client.login.return_value = True
    client.get_device_tree.return_value = [DEVICE_ONLINE]
    client.get_live_stream_url.return_value = "rtsp://example.com/live"
    client.search_recordings.return_value = [RECORDING]
    client.get_playback_stream_url.return_value = "rtsp://example.com/playback"
    return client


ARGV_EMPTY = patch("sys.argv", ["dahua-dss"])


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_login_failure(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = ["host", "8088", "admin", "pass"]
    client = _mock_client()
    client.login.return_value = False
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", ""):
        main()

    client.login.assert_called_once_with("admin", "pass")
    client.logout.assert_not_called()


@patch("sys.argv", ["dahua-dss", "--token", "mytoken"])
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_token_skips_login(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = ["host", "8088", "5"]
    client = _mock_client()
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"):
        main()

    client.set_token.assert_called_once_with("mytoken")
    client.login.assert_not_called()


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_choice_1_tree(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = ["host", "8088", "user", "1", "tree", "5"]
    client = _mock_client()
    mock_cls.return_value = client

    with (
        patch("dahua_dss.cli.console"),
        patch("builtins.open", mock_open()),
        patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"),
    ):
        main()

    client.get_device_tree.assert_called_once()


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_choice_1_table(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = ["host", "8088", "user", "1", "table", "5"]
    client = _mock_client()
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"):
        main()

    client.get_device_tree.assert_called_once()


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_choice_2_live_stream(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = ["host", "8088", "user", "2", "CH001", "1", "5"]
    client = _mock_client()
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"):
        main()

    client.get_live_stream_url.assert_called_once_with("CH001", 1)


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_choice_2_live_stream_failure(
    mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock
) -> None:
    mock_prompt.side_effect = ["host", "8088", "user", "2", "CH001", "1", "5"]
    client = _mock_client()
    client.get_live_stream_url.return_value = None
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"):
        main()  # should not raise


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_choice_3_search_recordings(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = [
        "host",
        "8088",
        "user",
        "3",
        "CH001",
        "2026-01-01 00:00:00",
        "2026-01-02 00:00:00",
        "5",
    ]
    client = _mock_client()
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"):
        main()

    assert client.search_recordings.call_count == 2
    client.search_recordings.assert_any_call("CH001", "2026-01-01 00:00:00", "2026-01-02 00:00:00", 1, 2)
    client.search_recordings.assert_any_call("CH001", "2026-01-01 00:00:00", "2026-01-02 00:00:00", 1, 3)


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_choice_4_playback(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = [
        "host",
        "8088",
        "user",
        "4",
        "CH001",
        "2026-01-01 00:00:00",
        "2026-01-02 00:00:00",
        "1",
        "3",
        "5",
    ]
    client = _mock_client()
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"):
        main()

    client.get_playback_stream_url.assert_called_once_with(
        "CH001",
        "2026-01-01 00:00:00",
        "2026-01-02 00:00:00",
        stream_type=1,
        record_source=3,
    )


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_choice_5_logout(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = ["host", "8088", "user", "5"]
    client = _mock_client()
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"):
        main()

    client.logout.assert_called_once()


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_keyboard_interrupt(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = ["host", "8088", "user", KeyboardInterrupt]
    client = _mock_client()
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"):
        main()

    client.logout.assert_called_once()


@ARGV_EMPTY
@patch("dahua_dss.cli.DahuaDSSClient")
@patch("dahua_dss.cli.Confirm.ask", return_value=False)
@patch("dahua_dss.cli.Prompt.ask")
def test_main_unexpected_exception(mock_prompt: MagicMock, mock_confirm: MagicMock, mock_cls: MagicMock) -> None:
    mock_prompt.side_effect = ["host", "8088", "user", RuntimeError("boom")]
    client = _mock_client()
    mock_cls.return_value = client

    with patch("dahua_dss.cli.console"), patch("dahua_dss.cli.DEFAULT_DSS_PASSWORD", "secret"):
        main()

    client.logout.assert_called_once()
