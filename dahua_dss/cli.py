#!/usr/bin/env python3
"""Dahua DSS CLI - presentation layer only"""

import argparse
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from dotenv import load_dotenv
from rich import box
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.tree import Tree

from dahua_dss.client import DahuaDSSClient

load_dotenv()

DEFAULT_DSS_HOST = os.getenv("DSS_HOST", "lnkuu-84-199-49-194.a.free.pinggy.link")
DEFAULT_DSS_USER = os.getenv("DSS_USER", "monitor")
DEFAULT_DSS_PORT = os.getenv("DSS_PORT", "443")
DEFAULT_DSS_USE_HTTPS = os.getenv("DSS_USE_HTTPS", "true").lower() in ("true", "1", "yes")
DEFAULT_DSS_PASSWORD = os.getenv("DSS_PASSWORD", "")

console = Console()


def display_device_tree(devices: List[Dict]) -> None:
    if not devices:
        console.print("[yellow]No devices found.[/yellow]")
        return

    tree = Tree("📹 [bold cyan] Devices[/bold cyan]", guide_style="bright_blue")

    for device in devices:
        status = device.get("status", "Unknown")
        status_color = "green" if status == "1" else "red"
        status_label = f"[{status_color}]{'Online' if status == '1' else 'Offline'}[/{status_color}]"
        source_type = "Platform" if device.get("sourceType") == "1" else "Third-Party"

        device_label = f"[bold]{device.get('name', 'Unnamed')}[/bold] [dim]({device.get('category', 'Unknown')}/{device.get('type', 'Unknown')})[/dim] - {status_label}"
        device_node = tree.add(f"🖥️  {device_label}")
        device_node.add(f"[dim]Code: {device.get('code', 'Unknown')}[/dim]")
        device_node.add(f"[dim]Source Type: {source_type}[/dim]")
        device_node.add(f"[dim]Model: {device.get('deviceModelStr', 'Unknown')} ({device.get('model', 'Unknown')})[/dim]")
        device_node.add(f"[dim]Org Code: {device.get('orgCode', 'Unknown')}[/dim]")

        units = device.get("units", [])
        units_node = device_node.add(f"📊 [cyan]Units ({len(units)})[/cyan]")
        for unit in units:
            unit_node = units_node.add(
                f"[bold]{unit.get('unitType', 'Unnamed')}[/bold] [dim](Seq: {unit.get('unitSeq', 'Unknown')}, AssistStream: {unit.get('assistStream', 'Unknown')}, ZeroChnEncode: {unit.get('zeroChnEncode', 'Unknown')}, StreamType: {unit.get('streamType', 'Unknown')})[/dim]"
            )
            channels = unit.get("channels", [])
            if channels:
                channels_node = unit_node.add(f"📡 [cyan]Channels ({len(channels)})[/cyan]")
                for channel in channels:
                    ch_status = channel.get("status")
                    ch_status_label = f"[{'green' if ch_status == '1' else 'red'}]{'Online' if ch_status == '1' else 'Offline'}[/{'green' if ch_status == '1' else 'red'}]"
                    channels_node.add(
                        f"[bold]{channel.get('channelName', 'Unknown')}[/bold] ({channel.get('channelCode', 'Unknown')}) [dim](seq: {channel.get('channelSeq', 'Unnamed')})[/dim] - {ch_status_label}"
                    )

    console.print()
    console.print(tree)
    console.print()
    with open("device_tree.txt", "w") as f:
        rprint(tree, file=f)


def display_device_table(devices: List[Dict]) -> None:
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
        status = device.get("status", "Unknown")
        status_display = "[green]●[/green] Online" if status == "1" else "[red]●[/red] Offline"
        table.add_row(
            str(idx),
            device.get("name", "Unnamed"),
            device.get("code", "Unknown"),
            device.get("category", "Unknown"),
            status_display,
            str(len(device.get("units", []))),
            str(sum(len(unit.get("channels", [])) for unit in device.get("units", []))),
        )

    console.print()
    console.print(table)
    console.print()


def display_recordings(recordings: List[Dict]) -> None:
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
        )

    console.print(table)


def show_banner() -> None:
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
    now = datetime.now()
    return (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    argparser = argparse.ArgumentParser(description="Dahua DSS Video Management System - Interactive API Client")
    argparser.add_argument("-t", "--token", help="Dahua DSS authentication token", default=None)
    args = argparser.parse_args()

    default_start_time, default_end_time = get_default_time_range()

    show_banner()
    console.print("[bold cyan]Connection Setup[/bold cyan]\n")

    host = Prompt.ask("Enter DSS server IP/hostname", default=DEFAULT_DSS_HOST)
    use_https = Confirm.ask("Use HTTPS?", default=DEFAULT_DSS_USE_HTTPS)
    port = Prompt.ask("Enter DSS server port", default=DEFAULT_DSS_PORT)

    client = DahuaDSSClient(host, int(port), use_https)

    console.print("\n[bold cyan]Authentication[/bold cyan]\n")

    if not args.token:
        username = Prompt.ask("Username", default=DEFAULT_DSS_USER)
        if DEFAULT_DSS_PASSWORD:
            password = DEFAULT_DSS_PASSWORD
            console.print("[dim]Using password from .env file[/dim]")
        else:
            password = Prompt.ask("Password", password=True)
        if not client.login(username, password):
            console.print("[red]✗[/red] Authentication failed.", style="bold")
            return
        console.print(f"[green]✓[/green] Authentication successful. Welcome, [bold]{username}[/bold]!")
    else:
        client.set_token(args.token)
        console.print(f"[green]✓[/green] Using token={args.token}", style="bold")

    console.print()
    devices: Optional[List[Dict]] = None

    try:
        while True:
            show_menu()
            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"], default="1")

            if choice == "1":
                devices = client.get_device_tree()
                if devices:
                    view_choice = Prompt.ask("\nView as", choices=["tree", "table"], default="tree")
                    if view_choice == "tree":
                        display_device_tree(devices)
                    else:
                        display_device_table(devices)
                else:
                    console.print("[yellow]No devices found or not authenticated.[/yellow]")

            elif choice == "2":
                console.print()
                channel_id = Prompt.ask("Enter Channel ID")
                stream_type = Prompt.ask("Stream type", choices=["0", "1", "2"], default="1")
                stream_names = {"1": "Main Stream", "2": "Sub Stream", "0": "Other"}

                rtsp_url = client.get_live_stream_url(channel_id, int(stream_type))
                if rtsp_url:
                    console.print()
                    console.print(Panel(
                        f"[bold cyan]Stream Type:[/bold cyan] {stream_names[stream_type]}\n"
                        f"[bold cyan]Channel ID:[/bold cyan] {channel_id}\n\n"
                        f"[bold green]RTSP URL:[/bold green]\n[yellow]{rtsp_url}[/yellow]\n\n"
                        f'[dim]• VLC: vlc "{rtsp_url}"[/dim]\n'
                        f'[dim]• FFmpeg: ffmpeg -i "{rtsp_url}" -c copy output.mp4[/dim]',
                        title="🔴 [bold]Live Stream URL[/bold]", border_style="green",
                    ))
                else:
                    console.print("[red]✗[/red] Failed to get live stream URL.")

            elif choice == "3":
                console.print()
                channel_id = Prompt.ask("Enter Channel ID")
                console.print("\n[dim]Enter time range (format: YYYY-MM-DD HH:MM:SS)[/dim]")
                start_time = Prompt.ask("Start time", default=default_start_time)
                end_time = Prompt.ask("End time", default=default_end_time)

                recordings_dvc = client.search_recordings(channel_id, start_time, end_time, 1, 2) or []
                recordings_ctr = client.search_recordings(channel_id, start_time, end_time, 1, 3) or []
                all_recordings = recordings_dvc + recordings_ctr
                if all_recordings:
                    console.print("[bold blue]Recordings:[/bold blue]")
                    display_recordings(all_recordings)
                else:
                    console.print("[yellow]No recordings found for the specified time range.[/yellow]")

            elif choice == "4":
                console.print()
                channel_id = Prompt.ask("Enter Channel ID")
                console.print("\n[dim]Enter playback time range (format: YYYY-MM-DD HH:MM:SS)[/dim]")
                start_time = Prompt.ask("Start time", default=default_start_time)
                end_time = Prompt.ask("End time", default=default_end_time)
                stream_type = Prompt.ask("Stream type", choices=["1", "2"], default="1")
                record_source = Prompt.ask("Record source", choices=["2", "3"], default="3",
                                           show_choices=True)
                stream_names = {"1": "Main Stream", "2": "Sub Stream"}
                source_names = {"2": "Device", "3": "Center"}

                rtsp_url = client.get_playback_stream_url(
                    channel_id, start_time, end_time,
                    stream_type=int(stream_type),
                    record_source=int(record_source),
                )
                if rtsp_url:
                    console.print()
                    console.print(Panel(
                        f"[bold cyan]Stream Type:[/bold cyan] {stream_names[stream_type]}\n"
                        f"[bold cyan]Channel ID:[/bold cyan] {channel_id}\n"
                        f"[bold cyan]Source:[/bold cyan] {source_names[record_source]}\n"
                        f"[bold cyan]Time Range:[/bold cyan] {start_time} to {end_time}\n\n"
                        f"[bold green]RTSP URL:[/bold green]\n[yellow]{rtsp_url}[/yellow]\n\n"
                        f'[dim]• VLC: vlc "{rtsp_url}"[/dim]\n'
                        f'[dim]• FFmpeg: ffmpeg -i "{rtsp_url}" -c copy playback.mp4[/dim]',
                        title="▶️  [bold]Playback Stream URL[/bold]", border_style="green",
                    ))
                else:
                    console.print("[red]✗[/red] Failed to get playback stream URL.")

            elif choice == "5":
                console.print()
                client.logout()
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
