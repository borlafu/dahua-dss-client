"""Dahua DSS HTTP API client - data/service layer (no UI dependencies)"""

import json
import time
from datetime import datetime
from hashlib import md5
from typing import Any, Dict, List, Optional, cast

import requests
import urllib3

from dahua_dss.models import DssDeviceCategory, DssPlaybackRecordType, DssRecordSource, DssRecordType, DssStreamType


class DahuaDSSClient:
    """Client for Dahua DSS HTTP API"""

    SUCCESS_CODE = 1000
    AUTH_ENDPOINT = "/brms/api/v1.0/accounts/authorize"
    LOGOUT_ENDPOINT = "/brms/api/v1.0/accounts/unauthorize"
    AUTH_TOKEN_HEADER = "X-Subject-Token"

    DEVICE_TREE_ENDPOINT = "/brms/api/v1.0/tree/devices"
    LIVE_VIDEO_ENDPOINT = "/brms/api/v1.0/MTS/Video/StartVideo"
    QUERY_RECORDS_ENDPOINT = "/brms/api/v1.0/SS/Record/QueryRecords"

    def __init__(self, host: str, port: int = 443, use_https: bool = True, disable_ssl_verify: bool = False) -> None:
        self.host = host
        self.port = port
        self.protocol = "https" if use_https else "http"
        self.base_url = f"{self.protocol}://{host}:{port}"
        self.session = requests.Session()
        self.session.verify = disable_ssl_verify
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
        self.username: Optional[str] = None
        self.token: Optional[str] = None

    def set_token(self, token: str) -> None:
        self.token = token
        self.session.headers.update({self.AUTH_TOKEN_HEADER: token})

    def clear_token(self) -> None:
        self.token = None
        self.session.headers.pop(self.AUTH_TOKEN_HEADER, None)

    @staticmethod
    def compute_signature(username: str, password: str, realm: str, random_key: str) -> str:
        temp1 = md5(password.encode()).hexdigest()
        temp2 = md5(f"{username}{temp1}".encode()).hexdigest()
        temp3 = md5(temp2.encode()).hexdigest()
        temp4 = md5(f"{username}:{realm}:{temp3}".encode()).hexdigest()
        return md5(f"{temp4}:{random_key}".encode()).hexdigest()

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate to DSS system.

        Returns True if successful, raises requests.exceptions.RequestException on network errors.
        """
        import time

        try:
            response = self.session.post(
                self.base_url + self.AUTH_ENDPOINT, json={"userName": username}, timeout=5
            )
            if response.status_code != 401:
                response.raise_for_status()
                return False

            data = response.json()
            payload = {
                "signature": self.compute_signature(username, password, data["realm"], data["randomKey"]),
                "userName": username,
                "randomKey": data["randomKey"],
            }
            response = self.session.post(self.base_url + self.AUTH_ENDPOINT, json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()

            # code 2004 = "user already logged in" (stale session on server).
            # The session expires after `duration` seconds (typically 30s). Wait and retry once.
            if data.get("code") == 2004:
                time.sleep(31)
                return self.login(username, password)

            if "token" not in data:
                return False

            self.username = username
            self.set_token(data["token"])
            return True

        except (requests.exceptions.RequestException, KeyError):
            return False

    def logout(self) -> bool:
        """Logout and end session. Returns True if successful."""
        if not self.token:
            return False
        try:
            response = self.session.post(self.base_url + self.LOGOUT_ENDPOINT, json={}, timeout=5)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
        finally:
            self.clear_token()

    def get_device_tree(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get the complete device tree with video-capable devices.

        Returns list of devices or None on error.
        """
        if not self.token:
            return None

        try:
            payload: Dict[str, Any] = {
                "categories": [DssDeviceCategory.Encoder],
                "containVirtualDevice": "1",
                "resourceTypes": [],
            }
            response = self.session.post(self.base_url + self.DEVICE_TREE_ENDPOINT, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()

            with open("device_tree.json", "w") as f:
                json.dump(data, f, indent=2)

            return data.get("data", {}).get("devices") if "data" in data and "devices" in data["data"] else None

        except requests.exceptions.RequestException:
            return None

    def get_live_stream_url(self, channel_id: str, stream_type: DssStreamType = DssStreamType.Main) -> Optional[str]:
        """
        Get live RTSP stream URL for a channel.

        Returns URL string or None on error.
        """
        if not self.token:
            return None

        try:
            payload: Dict[str, Any] = {
                "data": {
                    "streamType": str(stream_type),
                    "channelId": channel_id,
                    "dataType": "1",
                }
            }
            response = self.session.post(self.base_url + self.LIVE_VIDEO_ENDPOINT, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()

            with open(f"live_stream_{channel_id}_{stream_type}.json", "w") as f:
                json.dump(data, f, indent=2)

            if "data" not in data or data.get("code") != self.SUCCESS_CODE:
                return None
            return f"{data['data']['url']}?token={data['data']['token']}"

        except requests.exceptions.RequestException:
            return None

    def get_live_stream_hls_url(self, channel_id: str, stream_type: DssStreamType = DssStreamType.Main) -> Optional[str]:
        """Get live HLS stream URL for a channel."""
        if not self.token:
            return None

        try:
            url = f"{self.base_url}/brms/api/v1.1/video/live/channel/{channel_id}/hls?protocol=http&streamType={stream_type}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            with open(f"live_stream_hls_{channel_id}_{stream_type}.json", "w") as f:
                json.dump(data, f, indent=2)

            if "data" not in data or data.get("code") != self.SUCCESS_CODE:
                return None
            return str(data["data"]["streamUrl"])

        except requests.exceptions.RequestException:
            return None

    PLAYBACK_ENDPOINT = "/brms/api/v1.0/SS/Playback/StartPlaybackByTime"

    def get_playback_stream_url(
        self,
        channel_id: str,
        start_time: str,
        end_time: str,
        stream_type: DssStreamType = DssStreamType.Main,
        record_source: DssRecordSource = DssRecordSource.Center,
        stream_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get playback RTSP stream URL for a recorded time range.

        Args:
            channel_id: Channel code from device tree
            start_time / end_time: "YYYY-MM-DD HH:MM:SS"
            stream_type: 1=Main stream, 2=Sub stream
            record_source: 2=Device, 3=Center
            stream_id: Stream ID from search_recordings result. If None, auto-fetched.

        Returns:
            RTSP URL string (with token appended) or None on error.
        """
        if not self.token:
            return None

        # streamId is required by the API — auto-fetch from the first matching recording
        if stream_id is None:
            recordings = self.search_recordings(channel_id, start_time, end_time, stream_type, record_source)
            if not recordings:
                # fallback: try the other source
                other_source = DssRecordSource.Device if record_source == DssRecordSource.Center else DssRecordSource.Center
                recordings = self.search_recordings(channel_id, start_time, end_time, stream_type, other_source)
                if recordings:
                    record_source = other_source
            stream_id = recordings[0]["streamId"] if recordings else ""

        try:
            start_ts = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timestamp())
            end_ts = int(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timestamp())

            payload: Dict[str, Any] = {
                "data": {
                    "channelId": channel_id,
                    "startTime": str(start_ts),
                    "endTime": str(end_ts),
                    "streamType": stream_type,
                    "recordType": DssPlaybackRecordType.General,
                    "recordSource": record_source,
                    "streamId": stream_id,
                }
            }
            response = self.session.post(
                self.base_url + self.PLAYBACK_ENDPOINT, json=payload, timeout=15
            )
            response.raise_for_status()
            data = response.json()

            if "data" not in data or data.get("code") != self.SUCCESS_CODE:
                return None
            return f"{data['data']['url']}?token={data['data']['token']}"

        except requests.exceptions.RequestException:
            return None

    def search_recordings(
        self, channel_id: str, start_time: str, end_time: str, stream_type: DssStreamType = DssStreamType.Main, record_source: DssRecordSource = DssRecordSource.Center
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for available recordings in a time period.

        Args:
            start_time / end_time: "YYYY-MM-DD HH:MM:SS"
            stream_type: Main or Sub stream
            record_source: Device or Center

        Returns list of recording dicts or None on error.
        """
        if not self.token:
            return None

        try:
            start_ts = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timestamp())
            end_ts = int(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timestamp())

            payload: Dict[str, Any] = {
                "data": {
                    "endTime": end_ts,
                    "startTime": start_ts,
                    "channelId": channel_id,
                    "streamType": stream_type,
                    "recordType": DssRecordType.All,
                    "recordSource": record_source,
                }
            }
            response = self.session.post(self.base_url + self.QUERY_RECORDS_ENDPOINT, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()

            with open(f"recordings_{channel_id}_{start_time}_{end_time}_{stream_type}_{record_source}.json", "w") as f:
                json.dump(data, f, indent=2)

            if "data" not in data or data.get("code") != self.SUCCESS_CODE:
                return None
            return cast(List[Dict[str, Any]], data["data"]["records"]) if "records" in data["data"] else []

        except requests.exceptions.RequestException:
            return None
