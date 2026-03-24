# Setup and Installation Guide

## Prerequisites

- Python 3.13 or higher
- Poetry (recommended) or pip
- Docker (optional, for containerized deployment)
- Git

## Method 1: Poetry (Recommended)

### 1. Install Poetry

```bash
# On Linux/macOS
curl -sSL https://install.python-poetry.org | python3 -

# On Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

### 2. Clone and Install

```bash
# Clone the repository
git clone https://github.com/borlafu/dahua-dss-client.git
cd dahua-dss-client

# Install dependencies
poetry install

# Verify installation
poetry run dahua-dss --help
```

### 3. Run the Application

```bash
# Option 1: Using poetry run
poetry run dahua-dss

# Option 2: Activate virtual environment
poetry shell
dahua-dss
```

## Method 2: pip

### 1. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 2. Install from PyPI

```bash
pip install dahua-dss-client
```

### 3. Install from Source

```bash
# Clone repository
git clone https://github.com/borlafu/dahua-dss-client.git
cd dahua-dss-client

# Install
pip install -e .
```

## Method 3: Docker

### 1. Build from Source

```bash
# Clone repository
git clone https://github.com/borlafu/dahua-dss-client.git
cd dahua-dss-client

# Build image
docker build -t dahua-dss-client:latest .

# Run container
docker run -it --rm dahua-dss-client:latest
```

### 2. Using Docker Compose

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env

# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
DSS_HOST=192.168.1.100
DSS_PORT=443
DSS_USER=admin
DSS_PASSWORD=your_secure_password
DSS_USE_HTTPS=true
```

## Development Setup

### 1. Install Dependencies

```bash
poetry install
```

### 2. Run Tests

```bash
# All tests with coverage
poetry run pytest

# Specific test file
poetry run pytest tests/test_client.py -v
```

### 3. Code Quality

```bash
# Format code
poetry run black dahua_dss tests

# Sort imports
poetry run isort dahua_dss tests

# Type checking
poetry run mypy dahua_dss
```

## Troubleshooting

### Poetry Command Not Found

Add Poetry to your PATH:

```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"

# Add to ~/.bashrc or ~/.zshrc for persistence
```

### SSL Certificate Errors

```bash
# Use HTTP instead of HTTPS
DSS_USE_HTTPS=false
```

### Docker Permission Denied

```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## Getting Help

- 🐛 Issues: [GitHub Issues](https://github.com/borlafu/dahua-dss-client/issues)
