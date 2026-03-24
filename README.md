# Dahua DSS Client

A modern, interactive Python client for the Dahua DSS (Data Security Service) Video Management System with a beautiful terminal UI.

![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🔐 **Authentication** - Secure login to Dahua DSS systems
- 📹 **Device Management** - Browse video-capable devices in a tree or table view
- 🔴 **Live Streaming** - Get RTSP URLs for live video streams
- ▶️ **Playback** - Access recorded video streams for specific time periods
- 🔍 **Recording Search** - Find available recordings with detailed information
- 🎨 **Beautiful UI** - Rich terminal interface with colors, tables, and progress indicators
- 🐳 **Docker Support** - Ready-to-use Docker containers

## Installation

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/borlafu/dahua-dss-client.git
cd dahua-dss-client

# Install dependencies
poetry install

# Run the application
poetry run dahua-dss
```

### Using pip

```bash
pip install dahua-dss-client
```

### Using Docker

```bash
# Build the image
docker build -t dahua-dss-client .

# Run interactively
docker run -it --rm dahua-dss-client
```

### Using Docker Compose

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your DSS credentials
nano .env

# Start the service
docker-compose up -d
```

## Quick Start

### Interactive Mode

```bash
# Using Poetry
poetry run dahua-dss

# Using installed package
dahua-dss

# Using Docker
docker run -it --rm dahua-dss-client
```

### Programmatic Usage

```python
from dahua_dss import DahuaDSSClient

# Create client
client = DahuaDSSClient("192.168.1.100", port=8088)

# Login
if client.login("admin", "password"):
    # Get devices
    devices = client.get_device_tree()

    # Get live stream
    rtsp_url = client.get_live_stream_url("channel_id", stream_type=0)

    # Get playback stream
    playback_url = client.get_playback_stream_url(
        "channel_id",
        "2025-11-25 00:00:00",
        "2025-11-25 01:00:00"
    )

    # Logout
    client.logout()
```

## Usage

### 1. Authentication

When you run the application, you'll be prompted for:
- DSS server IP/hostname
- Port (default: 8088)
- Whether to use HTTPS
- Username and password

### 2. Main Menu Options

**Option 1: Get Device Tree**
- Lists all video-capable devices and channels
- Choose between tree view (hierarchical) or table view
- Shows device status, type, and channel information

**Option 2: Get Live Stream URL**
- Select a channel ID from the device tree
- Choose stream type (Main/Sub/Third)
- Receive RTSP URL for live viewing

**Option 3: Search Recordings**
- Enter channel ID and time range
- View available recordings with duration and file size
- See recording segments in a formatted table

**Option 4: Get Playback Stream URL**
- Select channel ID and time range
- Choose stream type
- Receive RTSP URL for playback

**Option 5: Logout and Exit**
- Cleanly terminates the session

## Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
DSS_HOST=192.168.1.100
DSS_PORT=8088
DSS_USERNAME=admin
DSS_PASSWORD=your_password
DSS_USE_HTTPS=false
```

### Stream Types

- **0** - Main Stream (High quality, higher bandwidth)
- **1** - Sub Stream (Lower quality, lower bandwidth)
- **2** - Third Stream (If available)

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Run Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Check formatting
make format-check
```

### Build and Publish

```bash
# Build package
make build

# Publish to PyPI
make publish
```

## Docker

### Build Image

```bash
make docker-build
```

### Run Container

```bash
# Interactive mode
make docker-run

# With docker-compose
make docker-compose-up
```

### Stop Services

```bash
make docker-compose-down
```

## Playing Video Streams

Once you have an RTSP URL, you can play it with various tools:

### VLC Media Player

```bash
vlc "rtsp://your-stream-url"
```

### FFmpeg (Save to file)

```bash
ffmpeg -i "rtsp://your-stream-url" -c copy output.mp4
```

### FFplay (Quick preview)

```bash
ffplay "rtsp://your-stream-url"
```

## API Reference

### DahuaDSSClient

```python
class DahuaDSSClient:
    def __init__(self, host: str, port: int = 8088, use_https: bool = False)
    def login(self, username: str, password: str) -> bool
    def logout(self) -> None
    def get_device_tree(self) -> Optional[List[Dict]]
    def get_live_stream_url(self, channel_id: str, stream_type: int = 0) -> Optional[str]
    def get_playback_stream_url(self, channel_id: str, start_time: str, end_time: str, stream_type: int = 0) -> Optional[str]
    def search_recordings(self, channel_id: str, start_time: str, end_time: str) -> Optional[List[Dict]]
```

## Requirements

- Python 3.9+
- requests >= 2.31.0
- urllib3 >= 2.1.0
- rich >= 13.7.0

## Troubleshooting

### SSL Certificate Errors

If you encounter SSL certificate errors, the client automatically disables SSL verification. For production use, ensure proper SSL certificates are configured on your DSS server.

### Connection Timeout

Increase timeout values in the client initialization or check network connectivity to the DSS server.

### Authentication Failed

- Verify credentials are correct
- Check if the user has API access permissions
- Ensure the DSS server API is enabled

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- Supports Dahua DSS HTTP API v8.7

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Note**: This is an unofficial client and is not affiliated with Dahua Technology.
