# Docker/Podman Support

MCP Hangar supports running providers in Docker or Podman containers for better isolation and portability.

> **Quick Navigation:**
> - **Building your own images?** Continue reading this document.
> - **Using existing images from registries?** See [Pre-built Images](PREBUILT_IMAGES.md).

## Features

- **Auto-detection**: Automatically detects `podman` or `docker` (prefers podman for rootless security)
- **Auto-build**: Build images from Dockerfiles on demand
- **Volume mounts**: Mount host directories into containers
- **Resource limits**: Set memory and CPU limits
- **Network isolation**: Control network access per provider
- **Security hardening**: Drop capabilities, read-only filesystems, no-new-privileges

## Configuration

### Basic Container Mode

```yaml
providers:
  filesystem:
    mode: container
    image: mcp-filesystem:latest
    volumes:
      - "${HOME}:/data:ro"
    resources:
      memory: 256m
      cpu: "0.5"
    network: none
```

### Build from Dockerfile

```yaml
providers:
  filesystem:
    mode: container
    build:
      dockerfile: docker/Dockerfile.filesystem
      context: .
      tag: mcp-filesystem:custom
    volumes:
      - "${HOME}:/data:ro"
```

### Pre-Built Images

For using existing images from Docker Hub, GitHub Container Registry, or private registries, see the dedicated [Pre-built Images Guide](PREBUILT_IMAGES.md).

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mode` | string | `subprocess` | `subprocess`, `docker`, `container`, `podman` |
| `image` | string | - | Container image to run |
| `build.dockerfile` | string | - | Path to Dockerfile |
| `build.context` | string | `.` | Build context directory |
| `build.tag` | string | auto | Custom image tag |
| `volumes` | list | `[]` | Volume mounts (`host:container:mode`) |
| `resources.memory` | string | `512m` | Memory limit |
| `resources.cpu` | string | `1.0` | CPU limit |
| `network` | string | `none` | `none`, `bridge`, `host` |
| `env` | dict | `{}` | Environment variables |
| `read_only` | bool | `true` | Read-only root filesystem |
| `user` | string | - | User to run as (`current` for host user) |

## Included Dockerfiles

```
docker/
├── Dockerfile.filesystem   # @modelcontextprotocol/server-filesystem
├── Dockerfile.memory       # @modelcontextprotocol/server-memory
├── Dockerfile.fetch        # @kazuph/mcp-fetch
└── Dockerfile.math         # Python math provider
```

## Usage

### Using Container Config

```bash
MCP_CONFIG=config.container.yaml python -m mcp_hangar.server
```

### Building Images Manually

```bash
podman build -t mcp-filesystem:latest -f docker/Dockerfile.filesystem .
podman build -t mcp-memory:latest -f docker/Dockerfile.memory .
podman build -t mcp-fetch:latest -f docker/Dockerfile.fetch .
podman build -t mcp-math:latest -f docker/Dockerfile.math .
```

### Forcing Specific Runtime

```yaml
providers:
  filesystem:
    mode: podman    # Force podman
    # or
    mode: docker    # Force docker
    # or
    mode: container # Auto-detect (recommended)
```

## Security

Container mode includes multiple security features:

- **Network isolation**: Default `network: none` prevents internet access
- **Read-only filesystem**: Container root is read-only by default
- **Dropped capabilities**: All Linux capabilities are dropped
- **No new privileges**: Prevents privilege escalation
- **Resource limits**: Memory and CPU limits prevent resource abuse
- **Volume validation**: Blocks mounting sensitive paths

### Blocked Mount Paths

These paths cannot be mounted: `/`, `/etc`, `/var`, `/usr`, `/bin`, `/sbin`, `/lib`, `/lib64`, `/boot`, `/root`, `/sys`, `/proc`

## Troubleshooting

### No container runtime found

```bash
# macOS
brew install podman

# Linux
sudo apt install podman
```

### Build fails

Check that Dockerfile exists and context is correct:

```bash
ls -la docker/Dockerfile.filesystem
```

### Container won't start

```bash
podman logs <container_id>
```

### Permission denied on volume mount

Ensure the host path exists and is readable. For podman with SELinux:

```yaml
volumes:
  - "/home/user/data:/data:ro,Z"
```
