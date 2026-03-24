#!/usr/bin/env python3
"""
Dahua DSS Video Management System - Interactive API Client with Rich UI

This script provides an interactive interface to:
1. Authenticate to Dahua DSS
2. Get the device tree with video-capable devices
3. Obtain live video stream URLs
4. Obtain recorded video stream URLs for specific times
"""

import argparse
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

import requests
import urllib3
from dotenv import load_dotenv
from rich import box
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.tree import Tree

# Try to load .env file if it exists (silent fail if not found)
load_dotenv()

DEFAULT_DSS_HOST = os.getenv("DSS_HOST", "lnkuu-84-199-49-194.a.free.pinggy.link")  # "ocsquantum.a.pinggy.link"
DEFAULT_DSS_USER = os.getenv("DSS_USER", "monitor")
DEFAULT_DSS_PORT = os.getenv("DSS_PORT", "443")
DEFAULT_DSS_USE_HTTPS = os.getenv("DSS_USE_HTTPS", "true").lower() in ("true", "1", "yes")
DEFAULT_DSS_PASSWORD = os.getenv("DSS_PASSWORD", "")

# Initialize Rich console
console = Console()
logging.captureWarnings(True)


class DahuaDSSClient:
    """Client for Dahua DSS HTTP API"""

    SUCCESS_CODE = 1000
    AUTH_ENDPOINT = "/brms/api/v1.0/accounts/authorize"
    TOKEN_KEEPALIVE_ENDPOINT = "/brms/api/v1.0/accounts/keepalive"
    TOKEN_REFRESH_ENDPOINT = "/brms/api/v1.0/accounts/updateToken"
    LOGOUT_ENDPOINT = "/brms/api/v1.0/accounts/unauthorize"
    AUTH_TOKEN_HEADER = "X-Subject-Token"

    DEVICE_TREE_ENDPOINT = "/brms/api/v1.0/tree/devices"
    LIVE_VIDEO_ENDPOINT = "/brms/api/v1.0/MTS/Video/StartVideo"
    QUERY_RECORDS_ENDPOINT = "/brms/api/v1.0/SS/Record/QueryRecords"

    def __init__(self, host: str, port: int = 443, use_https: bool = True, disable_ssl_verify: bool = False) -> None:
        """
        Initialize DSS client

        Args:
            host: DSS server IP or hostname
            port: DSS server port (default 8088)
            use_https: Use HTTPS instead of HTTP
        """
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
        """
        Set authentication token directly

        Args:
            token: DSS authentication token
        """
        self.token = token
        self.session.headers.update({self.AUTH_TOKEN_HEADER: self.token})
        console.print(f"[green]✓[/green] Using token={token}", style="bold")

    def clear_token(self) -> None:
        self.token = None
        self.session.headers.pop(self.AUTH_TOKEN_HEADER, None)

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate to DSS system

        Args:
            username: DSS username
            password: DSS password

        Returns:
            True if authentication successful
        """
        payload = {
            "userName": username,
            # "ipAddress": "",
            # "clientType": "WINPC_V2"
        }

        try:
            # console.print(f"[dim]Auth1 request: {payload}[/dim]")
            response = self.session.post(self.base_url + self.AUTH_ENDPOINT, json=payload, timeout=5)
            # console.print(f"[dim]Auth1 response: {response.status_code} \n {response.text}[/dim]")
            if response.status_code != 401:
                console.print(f"[red]✗[/red] Unexpected response during authentication: {response}", style="bold")
                response.raise_for_status()
                return False
            data = response.json()

            payload = {
                # "mac": "",
                # "deviceSN": "",
                "signature": self.compute_signature(username, password, data["realm"], data["randomKey"]),
                "userName": username,
                "randomKey": data["randomKey"],
                # "publicKey": "",
                # "ipAddress": "",
                # "clientType": "WINPC_V2",
                # "userType": "0",
                # "secretKey": "",
                # "secretVector": "",
                # "loginType": "1",
            }
            # console.print(f"[dim]Auth2 request: {payload}[/dim]")
            response = self.session.post(self.base_url + self.AUTH_ENDPOINT, json=payload, timeout=5)
            response.raise_for_status()
            # console.print(f"[dim]Auth2 response: {response.status_code} \n {response.text}[/dim]")
            data = response.json()

            if "token" not in data:
                console.print("[red]✗[/red] No token received from server", style="bold")
                return False

            self.username = username
            self.set_token(data["token"])
            console.print(f"[green]✓[/green] Authentication successful. Welcome, [bold]{username}[/bold]!")
            return True

        except (requests.exceptions.RequestException, KeyError) as e:
            console.print(f"[red]✗[/red] Authentication failed: {e}", style="bold")
            return False

    def compute_signature(self, username: str, password: str, realm: str, random_key: str) -> str:
        """Compute authentication signature"""
        from hashlib import md5

        temp1 = md5(password.encode()).hexdigest()
        temp2 = md5(f"{username}{temp1}".encode()).hexdigest()
        temp3 = md5(temp2.encode()).hexdigest()
        temp4 = md5(f"{username}:{realm}:{temp3}".encode()).hexdigest()
        return md5(f"{temp4}:{random_key}".encode()).hexdigest()

    def logout(self) -> None:
        """Logout and end session"""
        if not self.token:
            console.print("[yellow] Not logged in![/yellow]")
            return

        try:
            response = self.session.post(self.base_url + self.LOGOUT_ENDPOINT, json={}, timeout=5)
            response.raise_for_status()
            console.print(f"[green]✓[/green] Logged out successfully: {response.text}", style="bold")
        except Exception as e:
            console.print(f"[red]✗[/red] Error logging out: {e}", style="bold")
        finally:
            self.clear_token()

    def get_device_tree(self) -> Optional[List[Dict[str, str]]]:
        """
        Get the complete device tree with video-capable devices

        Returns:
            List of devices with channel information
        """
        if not self.token:
            console.print("[red]✗[/red] Not authenticated. Please login first.", style="bold")
            return None

        try:
            payload: dict[str, Any] = {
                "categories": ["1"],  # Encoders
                "containVirtualDevice": "1",  # Include virtual devices
                "resourceTypes": [],  # All resources (1 = video resources)
            }
            response = self.session.post(self.base_url + self.DEVICE_TREE_ENDPOINT, json=payload, timeout=15)
            response.raise_for_status()
            # console.print(f"[dim]Devices: {response.text}[/dim]")

            data = response.json()
            # save data to file\
            with open("device_tree.json", "w") as f:
                json.dump(data, f, indent=2)

            return data.get("data", {}).get("devices") if "data" in data and "devices" in data["data"] else None

        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗[/red] Request error: {e}", style="bold")
            return None

    def display_device_tree(self, devices: List[Dict]) -> None:
        """
        Display device tree in a beautiful tree format

        Args:
            devices: List of devices from get_device_tree()
        """
        if not devices:
            console.print("[yellow]No devices found.[/yellow]")
            return

        # Create a tree structure
        tree = Tree("📹 [bold cyan] Devices[/bold cyan]", guide_style="bright_blue")

        for device in devices:
            device_code = device.get("code", "Unknown")
            device_name = device.get("name", "Unnamed")
            device_category = device.get("category", "Unknown")
            device_type = device.get("type", "Unknown")
            status = device.get("status", "Unknown")
            source_type = "Platform" if device.get("sourceType") == "1" else "Third-Party"

            # Status color
            status_color = "green" if status == "1" else "red"
            status_label = f"[{status_color}]{"Online" if status == "1" else "Offline"}[/{status_color}]"

            # Add device node
            device_label = f"[bold]{device_name}[/bold] [dim]({device_category}/{device_type})[/dim] - {status_label}"
            device_node = tree.add(f"🖥️  {device_label}")
            device_node.add(f"[dim]Code: {device_code}[/dim]")
            device_node.add(f"[dim]Source Type: {source_type}[/dim]")
            device_node.add(
                f"[dim]Model: {device.get('deviceModelStr', 'Unknown')} ({device.get('model', 'Unknown')})[/dim]"
            )
            device_node.add(f"[dim]Org Code: {device.get('orgCode', 'Unknown')}[/dim]")

            # Add units
            units = device.get("units", [])
            units_node = device_node.add(f"📊 [cyan]Units ({len(units)})[/cyan]")
            for unit in units:
                unit_type = unit.get("unitType", "Unnamed")
                unit_seq = unit.get("unitSeq", "Unknown")
                unit_assist_stream = unit.get("assistStream", "Unknown")
                unit_zero_chn_encode = unit.get("zeroChnEncode", "Unknown")
                unit_stream_type = unit.get("streamType", "Unknown")
                unit_node = units_node.add(
                    f"[bold]{unit_type}[/bold] [dim](Seq: {unit_seq}, AssistStream: {unit_assist_stream}, ZeroChnEncode: {unit_zero_chn_encode}, StreamType: {unit_stream_type})[/dim]"
                )

                channels = unit.get("channels", [])
                if channels:
                    channels_node = unit_node.add(f"📡 [cyan]Channels ({len(channels)})[/cyan]")
                    for channel in channels:
                        ch_name = channel.get("channelName", "Unknown")
                        ch_seq = channel.get("channelSeq", "Unnamed")
                        ch_code = channel.get("channelCode", "Unknown")
                        ch_status = "Online" if channel.get("status") == "1" else "Offline"
                        ch_status_color = "green" if channel.get("status") == "1" else "red"
                        ch_status_label = f"[{ch_status_color}]{ch_status}[/{ch_status_color}]"

                        channels_node.add(
                            f"[bold]{ch_name}[/bold] ({ch_code}) [dim](seq: {ch_seq})[/dim] - {ch_status_label}"
                        )

        console.print()
        console.print(tree)
        console.print()
        # Save tree data to file
        with open("device_tree.txt", "w") as f:
            rprint(tree, file=f)

    def display_device_table(self, devices: List[Dict]) -> None:
        """
        Display devices in a table format

        Args:
            devices: List of devices from get_device_tree()
        """
        if not devices:
            console.print("[yellow]No devices found.[/yellow]")
            return

        table = Table(title="📹 Devices", box=box.ROUNDED, show_header=True, header_style="bold cyan")

        table.add_column("#", style="dim", width=4)
        table.add_column("Device Name", style="bold")
        table.add_column("Device ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status", justify="center")
        table.add_column("Units", justify="center", style="green")
        table.add_column("Channels", justify="center", style="green")

        for idx, device in enumerate(devices, 1):
            device_id = device.get("code", "Unknown")
            device_name = device.get("name", "Unnamed")
            device_type = device.get("category", "Unknown")
            status = device.get("status", "Unknown")
            units = str(len(device.get("units", [])))
            channels = str(sum(len(unit.get("channels", [])) for unit in device.get("units", [])))

            # Status color
            if status == "1":
                status_display = "[green]●[/green] Online"
            else:
                status_display = "[red]●[/red] Offline"

            table.add_row(str(idx), device_name, device_id, device_type, status_display, units, channels)

        console.print()
        console.print(table)
        console.print()

    def get_live_stream_hls_url(self, channel_id: str, stream_type: int = 1) -> Optional[str]:
        """
        Get live video stream URL for a channel

        Args:
            channel_id: Channel ID from device tree
            stream_type: 1=Main stream, 2=Sub stream. In multi-screen mode, the value range is 0-1024

        Returns:
            RTSP URL for live stream
        """
        if not self.token:
            console.print("[red]✗[/red] Not authenticated. Please login first.", style="bold")
            return None

        try:
            url = f"{self.base_url}/brms/api/v1.1/video/live/channel/{channel_id}/hls?protocol=http&streamType={stream_type}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            console.print(f"[dim]Response: {response.text}[/dim]")

            data = response.json()
            # save data to file
            with open(f"live_stream_hls_{channel_id}_{stream_type}.json", "w") as f:
                json.dump(data, f, indent=2)

            if "data" not in data or data.get("code") != self.SUCCESS_CODE:
                console.print(f"[red]✗[/red] Error ({data['code']}): {data['desc']}", style="bold")
                return None
            return f"{data['data']['streamUrl']}"
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗[/red] Request error: {e}", style="bold")
            return None

    def get_live_stream_url(self, channel_id: str, stream_type: int = 1) -> Optional[str]:
        """
        Get live video stream URL for a channel

        Args:
            channel_id: Channel ID from device tree
            stream_type: 1=Main stream, 2=Sub stream. In multi-screen mode, the value range is 0-1024

        Returns:
            RTSP URL for live stream
        """
        if not self.token:
            console.print("[red]✗[/red] Not authenticated. Please login first.", style="bold")
            return None

        try:
            payload: dict[str, dict] = {
                "data": {
                    "streamType": str(stream_type),
                    # "trackId": "",
                    "channelId": channel_id,
                    # "keyCode": "",
                    "dataType": "1",  # Video stream
                    # "enableRtsps": "0",
                    # "enableMulticast": "0",
                    # "fakeSdp": "0",
                }
            }
            response = self.session.post(self.base_url + self.LIVE_VIDEO_ENDPOINT, json=payload, timeout=15)
            response.raise_for_status()
            console.print(f"[dim]Response: {response.text}[/dim]")

            data = response.json()
            # save data to file
            with open(f"live_stream_{channel_id}_{stream_type}.json", "w") as f:
                json.dump(data, f, indent=2)

            if "data" not in data or data.get("code") != self.SUCCESS_CODE:
                console.print(f"[red]✗[/red] Error ({data['code']}): {data['desc']}", style="bold")
                return None
            return f"{data['data']['url']}?token={data['data']['token']}"
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗[/red] Request error: {e}", style="bold")
            return None

    def get_playback_stream_url(
        self, channel_id: str, start_time: str, end_time: str, stream_type: int = 0
    ) -> Optional[str]:
        if not self.token:
            console.print("[red]✗[/red] Not authenticated. Please login first.", style="bold")
            return None

        raise NotImplementedError("Playback stream URL retrieval not implemented yet.")

    def search_recordings(
        self, channel_id: str, start_time: str, end_time: str, stream_type: int = 1, record_source: int = 3
    ) -> Optional[List[Dict]]:
        """
        Search for available recordings in a time period

        Args:
            channel_id: Channel ID from device tree
            start_time: Start time in format "YYYY-MM-DD HH:MM:SS"
            end_time: End time in format "YYYY-MM-DD HH:MM:SS"
            stream_type: 1=Main stream, 2=Sub stream. In multi-screen mode, the value range is 0-1024
            record_source: 2=Device, 3=Center

        Returns:
            List of recording segments
        """
        if not self.token:
            console.print("[red]✗[/red] Not authenticated. Please login first.", style="bold")
            return None

        try:
            # transform time to timestamp in seconds
            start_timestamp = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timestamp())
            end_timestamp = int(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timestamp())

            payload: dict[str, dict] = {
                "data": {
                    "endTime": end_timestamp,
                    "startTime": start_timestamp,
                    "channelId": channel_id,
                    "streamType": str(stream_type),  # 1: Main stream, 2: Sub stream
                    # Recording type:
                    # 0: All
                    # 1: Manual recording
                    # 2: Alarm recording
                    # 3: Dynamic monitoring
                    # 4: Video loss
                    # 5: Video tampering
                    # 6: Scheduled recording
                    # 7: All-weather recording
                    # 8: File recording conversion
                    "recordType": "0",
                    "recordSource": str(record_source),  # 2: Device, 3: Center
                    # "page": "",
                    # "session": ""
                }
            }
            response = self.session.post(self.base_url + self.QUERY_RECORDS_ENDPOINT, json=payload, timeout=15)
            response.raise_for_status()
            console.print(f"[dim]Response: {response.text}[/dim]")

            data = response.json()
            # save data to file
            with open(f"recordings_{channel_id}_{start_time}_{end_time}_{stream_type}_{record_source}.json", "w") as f:
                json.dump(data, f, indent=2)

            if "data" not in data or data.get("code") != self.SUCCESS_CODE:
                console.print(f"[red]✗[/red] Error ({data['code']}): {data['desc']}", style="bold")
                return None
            return cast(List[Dict], data["data"]["records"]) if "records" in data["data"] else []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗[/red] Request error: {e}", style="bold")
            return None

    def display_recordings(self, recordings: List[Dict]) -> None:
        """
        Display recordings in a table format

        Args:
            recordings: List of recordings from search_recordings()
        """
        if not recordings:
            console.print("[yellow]No recordings found.[/yellow]")
            return

        table = Table(show_header=True, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Channel Id", style="magenta")
        table.add_column("Type", style="magenta")
        table.add_column("Source", style="magenta")
        table.add_column("Recording", style="cyan")
        table.add_column("Start Time", style="cyan")
        table.add_column("End Time", style="cyan")
        table.add_column("Record Name", style="green")
        table.add_column("Size (MB)", style="green")
        table.add_column("Duration (s)", style="green")
        # table.add_column("Plan Id", style="yellow")
        # table.add_column("Storage Id", style="yellow")
        # table.add_column("Disk Id", style="yellow")
        # table.add_column("Stream Id", style="yellow")

        for recording in recordings:
            start_time = datetime.fromtimestamp(int(recording["startTime"]))
            end_time = datetime.fromtimestamp(int(recording["endTime"]))
            duration = int(recording["endTime"]) - int(recording["startTime"])
            size_mb = int(recording.get("fileLength", 0)) / (1024 * 1024) if "fileLength" in recording else 0
            table.add_row(
                recording.get("channelId", "N/A"),
                "Main" if recording.get("streamType") == "1" else recording.get("streamType", "N/A"),
                "Device" if recording.get("recordSource") == "2" else "Center",
                recording.get("recordType", "N/A"),
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S"),
                recording.get("recordName", "N/A"),
                f"{size_mb:.2f}",
                str(duration),
                # recording.get("planId", "N/A"),
                # recording.get("storageSvcId", "N/A"),
                # recording.get("diskId", "N/A"),
                # recording.get("streamId", "N/A"),
            )

        console.print(table)


def show_banner() -> None:
    """Display application banner"""
    console.print(
        Panel(
            "DAHUA DSS VIDEO MANAGEMENT SYSTEM",
            style="bold blue",
            box=box.ROUNDED,
            padding=(1, 4),
            title_align="center",
            expand=False,
        )
    )


def show_menu() -> None:
    """Display main menu"""
    menu_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))

    menu_table.add_column("Option", style="cyan bold", width=3)
    menu_table.add_column("Description", style="white")

    menu_table.add_row("1", "📋 Get device tree (list all video-capable devices)")
    menu_table.add_row("2", "🔴 Get live stream URL")
    menu_table.add_row("3", "🔍 Search recordings")
    menu_table.add_row("4", "▶️  Get playback stream URL")
    menu_table.add_row("5", "🚪 Logout and exit")

    console.print()
    console.print(Panel(menu_table, title="[bold]MAIN MENU[/bold]", border_style="green"))
    console.print()


def get_default_time_range() -> tuple[str, str]:
    """
    Get default start and end times for the previous 24 hours

    Returns:
        Tuple of (start_time, end_time) in format "YYYY-MM-DD HH:MM:SS"
    """
    now = datetime.now()
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    return start_time, end_time


def main() -> None:
    """Main interactive interface"""

    argparser = argparse.ArgumentParser(description="Dahua DSS Video Management System - Interactive API Client")
    argparser.add_argument("-t", "--token", help="Dahua DSS authentication token", default=None)
    args = argparser.parse_args()

    # Get default time range for previous 24 hours
    default_start_time, default_end_time = get_default_time_range()

    show_banner()

    # Get connection details
    console.print("[bold cyan]Connection Setup[/bold cyan]")
    console.print()

    # Use defaults from .env file if available, otherwise prompt
    host = Prompt.ask("Enter DSS server IP/hostname", default=DEFAULT_DSS_HOST)
    use_https = Confirm.ask("Use HTTPS?", default=DEFAULT_DSS_USE_HTTPS)
    port = Prompt.ask("Enter DSS server port", default=DEFAULT_DSS_PORT)

    # Create client
    client = DahuaDSSClient(host, int(port), use_https)

    console.print()
    console.print("[bold cyan]Authentication[/bold cyan]")
    console.print()

    # Login - use password from .env if available, otherwise prompt
    if not args.token:
        username = Prompt.ask("Username", default=DEFAULT_DSS_USER)
        if DEFAULT_DSS_PASSWORD:
            password = DEFAULT_DSS_PASSWORD
            console.print("[dim]Using password from .env file[/dim]")
        else:
            password = Prompt.ask("Password", password=True)
        if not client.login(username, password):
            return
    else:
        client.set_token(args.token)
    console.print()

    devices = None

    try:
        while True:
            show_menu()

            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"], default="1")

            if choice == "1":
                # Get and display device tree
                devices = client.get_device_tree()
                if devices:
                    view_choice = Prompt.ask("\nView as", choices=["tree", "table"], default="tree")

                    if view_choice == "tree":
                        client.display_device_tree(devices)
                    else:
                        client.display_device_table(devices)

            elif choice == "2":
                # Get live stream
                console.print()
                channel_id = Prompt.ask("Enter Channel ID")
                stream_type = Prompt.ask("Stream type", choices=["0", "1", "2"], default="1")

                stream_names = {"1": "Main Stream", "2": "Sub Stream", "0": "Other"}

                rtsp_url = client.get_live_stream_url(channel_id, int(stream_type))
                if rtsp_url:
                    console.print()
                    stream_panel = f"""
[bold cyan]Stream Type:[/bold cyan] {stream_names[stream_type]}
[bold cyan]Channel ID:[/bold cyan] {channel_id}

[bold green]RTSP URL:[/bold green]
[yellow]{rtsp_url}[/yellow]

[dim]You can use this URL with VLC, FFmpeg, or other RTSP players:[/dim]
[dim]• VLC: vlc "{rtsp_url}"[/dim]
[dim]• FFmpeg: ffmpeg -i "{rtsp_url}" -c copy output.mp4[/dim]
                    """
                    console.print(
                        Panel(stream_panel.strip(), title="🔴 [bold]Live Stream URL[/bold]", border_style="green")
                    )

            elif choice == "3":
                # Search recordings
                console.print()
                channel_id = Prompt.ask("Enter Channel ID")
                console.print("\n[dim]Enter time range (format: YYYY-MM-DD HH:MM:SS)[/dim]")
                start_time = Prompt.ask("Start time", default=default_start_time)
                end_time = Prompt.ask("End time", default=default_end_time)

                recordings_dvc = client.search_recordings(channel_id, start_time, end_time, 1, 2)
                recordings_ctr = client.search_recordings(channel_id, start_time, end_time, 1, 3)
                if recordings_ctr + recordings_dvc:
                    console.print("[bold blue]Recordings:[/bold blue]")
                    client.display_recordings(recordings_ctr + recordings_dvc)
                if not recordings_dvc and not recordings_ctr:
                    console.print("[yellow]No recordings found for the specified time range.[/yellow]")

            elif choice == "4":
                # Get playback stream
                console.print()
                channel_id = Prompt.ask("Enter Channel ID")
                console.print("\n[dim]Enter playback time range (format: YYYY-MM-DD HH:MM:SS)[/dim]")
                start_time = Prompt.ask("Start time", default=default_start_time)
                end_time = Prompt.ask("End time", default=default_end_time)
                stream_type = Prompt.ask("Stream type", choices=["0", "1"], default="0")

                stream_names = {"0": "Main Stream", "1": "Sub Stream"}

                rtsp_url = client.get_playback_stream_url(channel_id, start_time, end_time, int(stream_type))
                if rtsp_url:
                    console.print()
                    playback_panel = f"""
[bold cyan]Stream Type:[/bold cyan] {stream_names[stream_type]}
[bold cyan]Channel ID:[/bold cyan] {channel_id}
[bold cyan]Time Range:[/bold cyan] {start_time} to {end_time}

[bold green]RTSP URL:[/bold green]
[yellow]{rtsp_url}[/yellow]

[dim]You can use this URL with VLC, FFmpeg, or other RTSP players:[/dim]
[dim]• VLC: vlc "{rtsp_url}"[/dim]
[dim]• FFmpeg: ffmpeg -i "{rtsp_url}" -c copy playback.mp4[/dim]
                    """
                    console.print(
                        Panel(playback_panel.strip(), title="▶️  [bold]Playback Stream URL[/bold]", border_style="green")
                    )

            elif choice == "5":
                # Logout and exit
                console.print()
                client.logout()
                console.print()
                console.print(Panel("[bold green]👋 Goodbye![/bold green]", style="green"))
                break

    except KeyboardInterrupt:
        console.print()
        console.print(Panel("[yellow]Interrupted by user[/yellow]", style="yellow"))
        client.logout()
    except Exception as e:
        console.print()
        console.print(Panel(f"[red]✗ Unexpected error: {e}[/red]", style="bold red"))
        client.logout()


if __name__ == "__main__":
    main()
