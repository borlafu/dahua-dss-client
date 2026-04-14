# Dahua DSS Client

A modern, interactive Python client for the Dahua DSS (Data Security Service) Video Management System with a beautiful terminal UI.

![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🔐 **Authentication** - Secure login to Dahua DSS systems
- 📹 **Device Management** - Browse video-capable devices in a tree or table view
- 🔴 **Live Streaming** - Get RTSP/HLS URLs for live video streams
- ▶️ **Playback** - Access recorded video streams for specific time periods
- 🔍 **Recording Search** - Find available recordings with detailed information
- 🎨 **Beautiful UI** - Rich terminal interface with colors, tables, and progress indicators
- 🐳 **Docker Support** - Ready-to-use Docker containers

## Installation

### Using Poetry (Recommended)

```bash
git clone https://github.com/borlafu/dahua-dss-client.git
cd dahua-dss-client
poetry install
poetry run dahua-dss
```

### Using pip

```bash
pip install dahua-dss-client
```

### Using Docker

```bash
docker build -t dahua-dss-client .
docker run -it --rm dahua-dss-client
```

### Using Docker Compose

```bash
cp .env.example .env
# Edit .env with your DSS credentials
docker compose run --rm dahua-dss
```

## Quick Start

### Interactive Mode

```bash
poetry run dahua-dss
# or, if installed via pip:
dahua-dss
```

### Programmatic Usage

```python
from dahua_dss import DahuaDSSClient, DssStreamType, DssRecordSource

client = DahuaDSSClient("192.168.1.100", port=443, use_https=True)

if client.login("admin", "password"):
    # Get devices
    devices = client.get_device_tree()

    # Get live stream URL
    rtsp_url = client.get_live_stream_url("channel_id", stream_type=DssStreamType.Main)

    # Search recordings
    recordings = client.search_recordings(
        "channel_id",
        "2025-11-25 00:00:00",
        "2025-11-25 01:00:00",
        stream_type=DssStreamType.Main,
        record_source=DssRecordSource.Center,
    )

    # Get playback stream URL
    playback_url = client.get_playback_stream_url(
        "channel_id",
        "2025-11-25 00:00:00",
        "2025-11-25 01:00:00",
        stream_type=DssStreamType.Main,
        record_source=DssRecordSource.Center,
    )

    client.logout()
```

## Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
DSS_HOST=192.168.1.100
DSS_PORT=443
DSS_USER=admin
DSS_PASSWORD=your_password
DSS_USE_HTTPS=true
```

### Stream Types

| Enum | Value | Description |
|------|-------|-------------|
| `DssStreamType.Main` | `1` | Main stream — high quality, higher bandwidth |
| `DssStreamType.Sub` | `2` | Sub stream — lower quality, lower bandwidth |

### Record Sources

| Enum | Value | Description |
|------|-------|-------------|
| `DssRecordSource.Device` | `2` | Recording stored on the device |
| `DssRecordSource.Center` | `3` | Recording stored on the DSS server |

## Interactive Usage

When you run the application, you'll be prompted for the DSS server IP/hostname, port (default: 443), HTTPS (default: yes), and credentials.

### Main Menu

1. **Get Device Tree** — lists all video-capable devices and channels in tree or table view
2. **Get Live Stream URL** — returns an RTSP URL for a channel
3. **Search Recordings** — find recordings in a time range with duration and file size
4. **Get Playback Stream URL** — returns an RTSP URL for a recorded time range
5. **Logout and Exit**

## API Reference

```python
class DahuaDSSClient:
    def __init__(self, host: str, port: int = 443, use_https: bool = True, disable_ssl_verify: bool = False)
    def login(self, username: str, password: str) -> bool
    def logout(self) -> bool
    def set_token(self, token: str) -> None
    def get_device_tree(self) -> Optional[List[Dict]]
    def get_live_stream_url(self, channel_id: str, stream_type: DssStreamType = DssStreamType.Main) -> Optional[str]
    def get_live_stream_hls_url(self, channel_id: str, stream_type: DssStreamType = DssStreamType.Main) -> Optional[str]
    def get_playback_stream_url(self, channel_id: str, start_time: str, end_time: str, stream_type: DssStreamType = DssStreamType.Main, record_source: DssRecordSource = DssRecordSource.Center, stream_id: Optional[str] = None) -> Optional[str]
    def search_recordings(self, channel_id: str, start_time: str, end_time: str, stream_type: DssStreamType = DssStreamType.Main, record_source: DssRecordSource = DssRecordSource.Center) -> Optional[List[Dict]]
```

Time parameters use the format `"YYYY-MM-DD HH:MM:SS"`.

## Playing Video Streams

```bash
# VLC
vlc "rtsp://your-stream-url"

# FFmpeg (save to file)
ffmpeg -i "rtsp://your-stream-url" -c copy output.mp4

# FFplay (quick preview)
ffplay "rtsp://your-stream-url"
```

## Development

```bash
# Install with dev dependencies
poetry install

# Run tests
poetry run pytest

# Format code
poetry run black dahua_dss tests
poetry run isort dahua_dss tests

# Type checking
poetry run mypy dahua_dss
```

## Requirements

- Python 3.13+
- requests >= 2.32.5
- urllib3 >= 2.6.3
- rich >= 14.2.0
- python-dotenv >= 1.0.0

## Troubleshooting

**SSL Certificate Errors** — the client disables SSL verification automatically. For production, configure proper certificates on your DSS server.

**Connection Timeout** — check network connectivity to the DSS server.

**Authentication Failed** — verify credentials, API access permissions, and that the DSS server API is enabled.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/my-feature`)
3. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat: add X`, `fix: correct Y`)
4. Push and open a Pull Request

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- Supports Dahua DSS HTTP API v8.7

---

**Note**: This is an unofficial client and is not affiliated with Dahua Technology.
