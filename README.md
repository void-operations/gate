# Deployment Automation and Version Management System

One-click deployment and version tracking system for developers. Deploy software to target PCs with a single button, automatically record all deployment history, and track software version changes on each PC in real-time.

## Overview

This project provides a Master-Agent architecture for automated software deployment and version management. It enables developers to deploy software to Windows PCs and manage firmware files with minimal effort while maintaining a complete audit trail of all deployments.

### Key Features

- **One-click deployment**: Deploy software to target PCs with a single button
- **Deployment history tracking**: Automatically record and track all deployment activities
- **Version monitoring**: Real-time tracking of software version changes on each PC
- **Firmware deployment**: Support for Windows executables and firmware files
- **Cross-platform**: Windows and macOS (Intel/Apple Silicon) support

### Architecture

- **Master**: Python-based web server + web frontend (Agent management and monitoring)
  - Deployed on Linux using Docker and Docker Compose
  - Provides Agent build artifacts for download
  - Follows Clean Architecture principles
- **Agent**: C# based client (Windows/macOS executables)
  - Auto-registration with Master and heartbeat transmission
  - Performs deployment tasks and reports status

## Quick Start

### Prerequisites

**Development Environment:**
- macOS 14+ (development environment)
- Cursor IDE (recommended) or any other IDE
- Git, GitHub

**Master:**
- Python 3.8+
- Node.js 18+ and npm
- Docker & Docker Compose (for production deployment)

**Agent:**
- .NET 8.0 SDK
- Windows or macOS (build environment)

### Running Master Server

```bash
# Deploy Master
python deploy-master.py --version 1.0.0

# Run Master server
cd master/backend
python main.py

# Run frontend in development mode (separate terminal)
cd master/frontend
npm run dev
```

Master runs at `http://localhost:8000`.

### Building and Running Agent

```bash
# Build Agent for all platforms
python deploy-agent.py --version 1.0.0

# Or build for specific platform
python deploy-agent.py --version 1.0.0 --platform windows

# Run Agent
# Windows:
dist/agent-windows/Agent.exe

# macOS:
dist/agent-macos-x64/Agent        # Intel Mac
dist/agent-macos-arm64/Agent      # Apple Silicon
```

## Tutorial

### Project Structure

```
3project/
├── master/                 # Master server and frontend
│   ├── backend/            # Python FastAPI server
│   │   ├── main.py
│   │   └── requirements.txt
│   └── frontend/           # Web frontend (Vite)
│       ├── src/
│       ├── index.html
│       └── package.json
├── agent/                  # C# Agent client
│   ├── Program.cs
│   ├── Agent.csproj
│   └── appsettings.json
├── scripts/                # Build scripts
│   ├── build-agent.sh      # Agent build for Mac/Linux
│   ├── build-agent.bat     # Agent build for Windows
│   └── init.ps1            # Project initialization
├── config/                 # Configuration files
│   └── config.example.json # Configuration example
├── dist/                   # Build output (gitignore)
├── .github/                # GitHub Actions
│   └── workflows/
│       └── ci.yml         # CI/CD workflow
├── deploy.py              # Unified deployment script
├── deploy-master.py       # Master-only deployment
├── deploy-agent.py        # Agent-only deployment
├── version.py             # Version management utility
├── VERSION                # Current version file
├── LICENSE                # MIT License
└── requirements.txt       # Python dependencies
```

### Master API Endpoints

- `GET /api/agents` - List all agents
- `GET /api/agents/{id}` - Get specific agent
- `POST /api/agents/register` - Register agent / heartbeat
- `DELETE /api/agents/{id}` - Unregister agent
- `GET /api/health` - Health check

### Agent Configuration

Configure Agent in `agent/appsettings.json`:

```json
{
  "MasterUrl": "http://localhost:8000",
  "AgentName": "",
  "HeartbeatInterval": 10000,
  "Version": "1.0.0"
}
```

### Version Management

The project uses automatic version management system.

**Version Tagging Rule:** `{deployment-stage}-{date}-{number}`

Examples:
- `production-20250115-001`
- `staging-20250115-002`
- `development-20250115-001`

**Usage:**
```bash
# Check current version
cat VERSION

# Manually update version
python -c "from version import VersionManager; vm = VersionManager(); vm.update_version('1.0.0')"

# Auto-increment version
python -c "from version import VersionManager; vm = VersionManager(); vm.increment_version('patch')"
```

### Development Workflow

**Local Deployment:**
1. Update version using `version.py`
2. Deploy Master using `deploy-master.py`
3. Build Agent using `deploy-agent.py`
4. Git tags are automatically created

**Production Deployment (Docker):**
Master is deployed on Linux using Docker and Docker Compose:

```bash
# Deploy Master with Docker Compose (to be implemented)
docker-compose up -d
```

Agent build artifacts are deployed together and can be downloaded from Master server.

### CI/CD (GitHub Actions)

The project uses GitHub Actions for automated builds and deployments.

**Triggers:**
- Push events on `main`, `master`, `develop` branches
- Pull requests to `main`/`master` branches

**Current Workflow:**
1. Master Backend: Python linting and testing
2. Master Frontend: Node.js build and artifact storage
3. Agent Windows: Windows x64 executable build
4. Agent macOS: macOS x64/ARM64 executable build

**Build Artifacts:**
- Agent executables (Windows, macOS x64, macOS ARM64)
- Master Frontend build artifacts
- Stored as GitHub Actions artifacts (downloadable)

Workflow file: `.github/workflows/ci.yml`

**Future Plans (to be added per requirements):**
1. Upload build artifacts to Master automatically
2. Master-Agent integration tests
3. Deployment pipeline automation

### Development Principles

**Architecture:**
- **Clean Architecture**: All code strictly follows Clean Architecture principles
- **Layer Separation**: Clear separation of domain, application, and infrastructure layers

**Testing:**
- **Unit tests required**: Always write unit tests when adding functions
- **Mock usage**: Use mocks for testing external system integrations
- **Test coverage**: Maintain test coverage for core logic

**Note:** This project is currently a personal development project, so there is no code review process in place.

## Important Notes

**Core features mentioned in requirements (please add detailed documentation):**
- One-click deployment workflow
- Deployment history and audit trail
- Version tracking per PC
- Firmware file deployment support
- Material Design theme for frontend (please add implementation details)

**Additional details to be added:**
- Detailed deployment procedures
- Configuration options
- Troubleshooting guide
- API documentation
- Agent capabilities and extensions

## License

Copyright (c) 2025 codingbridge.blog

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
