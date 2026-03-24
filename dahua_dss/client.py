"""Dahua DSS HTTP API client - data/service layer (no UI dependencies)"""

import json
from datetime import datetime
from hashlib import md5
from typing import Any, Dict, List, Optional, cast

import requests
import urllib3


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
                "categories": ["1"],
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

    def get_live_stream_url(self, channel_id: str, stream_type: int = 1) -> Optional[str]:
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

    def get_live_stream_hls_url(self, channel_id: str, stream_type: int = 1) -> Optional[str]:
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

    def get_playback_stream_url(
        self, channel_id: str, start_time: str, end_time: str, stream_type: int = 0
    ) -> Optional[str]:
        if not self.token:
            return None
        raise NotImplementedError("Playback stream URL retrieval not implemented yet.")

    def search_recordings(
        self, channel_id: str, start_time: str, end_time: str, stream_type: int = 1, record_source: int = 3
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for available recordings in a time period.

        Args:
            start_time / end_time: "YYYY-MM-DD HH:MM:SS"
            stream_type: 1=Main, 2=Sub
            record_source: 2=Device, 3=Center

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
                    "streamType": str(stream_type),
                    "recordType": "0",
                    "recordSource": str(record_source),
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
