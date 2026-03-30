# Docker Setup for QObserva

This directory contains Docker configuration for running the complete QObserva stack (collector + UI) in a containerized environment.

## Overview

The Docker setup provides a **fully containerized alternative** to native mode:
- **Collector**: FastAPI service using uvicorn directly (recommended production approach)
- **UI**: React dashboard served via Vite dev server

Both services run in separate containers and communicate via Docker networking.

## Why Uvicorn Directly?

1. **Production Best Practice**: Using `uvicorn` directly gives explicit control over the ASGI server
2. **Better Performance**: Direct invocation avoids CLI overhead
3. **Standard Pattern**: This is the standard way to run FastAPI apps in Docker
4. **Reliability**: Avoids potential entry point resolution issues in containers

## Alternative: CLI Command

When installed via pip (including PyPI), users can also use the CLI command:

```bash
qobserva-collector serve --host 0.0.0.0 --port 8080
```

This works fine for:
- Local development
- Native installations
- Testing

But for Docker/production, using `uvicorn` directly is preferred.

## Files

- `collector.Dockerfile`: Docker image for the collector service
- `ui.Dockerfile`: Docker image for the React UI
- `docker-compose.yml`: Docker Compose configuration (orchestrates both services)

## Usage

### Build and Run with Docker Compose

```bash
# Build images (collector + UI)
docker-compose build

# Start services (both collector + UI)
docker-compose up -d

# Check logs
docker-compose logs          # Both services
docker-compose logs collector  # Collector only
docker-compose logs ui       # UI only

# Stop services
docker-compose down
```

### Using Makefile (from project root)

```bash
make docker-build    # Build images (collector + UI)
make docker-up       # Start services (collector + UI)
make docker-down     # Stop services
make docker-test     # Full test (build + run + health check)
```

### Using Python CLI

```bash
# Start everything (same as native mode, but containerized)
python -m qobserva_local.cli up --mode docker

# Stop everything
python -m qobserva_local.cli down --mode docker
```

## Configuration

**Services:**
- **Collector**: Port `8080` (API)
- **UI**: Port `3000` (React dashboard)

**Data Persistence:**
- Data is persisted in Docker volume (`qobserva_data`)
- UI source code is mounted for hot-reload during development

**Environment Variables:**
- `QOBSERVA_DATA_DIR`: Data directory (default: `/data` in container)
- `VITE_API_URL`: API URL for UI (set automatically in Docker)

## Health Checks

**Collector Health:**
```bash
curl http://localhost:8080/v1/health
```

Expected response:
```json
{"status":"ok","version":"0.1.0"}
```

**UI Accessibility:**
```bash
curl http://localhost:3000
```

Should return HTML (React app).

**Access in Browser:**
- **Collector API:** http://localhost:8080
- **React UI:** http://localhost:3000

## Notes

- **Collector**: Uses Python 3.12 for best SDK compatibility
- **UI**: Uses Node 20 for React/Vite
- **Development**: UI source is mounted for hot-reload
- **Production Considerations**:
  - Run as non-root users
  - Add SSL/TLS termination
  - Implement authentication
  - Set resource limits
  - Build production UI bundle (not dev server)
  - Use production-grade reverse proxy (nginx, traefik, etc.)

## Comparison: Native vs Docker

Both modes provide the same functionality:

| Feature | Native Mode | Docker Mode |
|---------|-------------|-------------|
| **Command** | `python -m qobserva_local.cli up` | `python -m qobserva_local.cli up --mode docker` |
| **Collector** | Native Python process | Docker container |
| **UI** | Native npm/vite | Docker container |
| **Isolation** | System-level | Container-level |
| **Setup** | Requires Python + Node | Requires Docker |
| **Use Case** | Development, simple setup | Production, isolation, consistency |
