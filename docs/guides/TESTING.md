# Testing

## Quick Start

```bash
uv sync --extra dev
uv run pytest tests/ -v -m "not slow"
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# By marker
pytest tests/ -m unit
pytest tests/ -m integration
pytest tests/ -m docker

# Coverage
pytest tests/ -m "not slow" --cov=mcp_hangar --cov-report=html
```

### Markers

| Marker | Description |
|--------|-------------|
| `unit` | Fast, isolated |
| `integration` | Multiple components |
| `slow` | Long-running |
| `docker` | Requires container runtime |

## Container Tests

```bash
# Build images first
podman build -t localhost/mcp-sqlite -f docker/Dockerfile.sqlite .

# Prepare data directory
mkdir -p data && chmod 777 data

# Run tests
pytest tests/feature/ -v
```

## Manual Testing

### Subprocess Provider

```yaml
# config.yaml
providers:
  math:
    mode: subprocess
    command: [python, tests/mock_provider.py]
```

```bash
python -m mcp_hangar.server
```

### Test via Python

```python
from mcp_hangar.provider_manager import ProviderManager
from mcp_hangar.models import ProviderSpec

spec = ProviderSpec(
    provider_id="test",
    mode="subprocess",
    command=["python", "tests/mock_provider.py"]
)

mgr = ProviderManager(spec)
mgr.ensure_ready()

result = mgr.invoke_tool("add", {"a": 5, "b": 3})
print(result)  # {"result": 8}

mgr.shutdown()
```

### Test Provider Directly

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python tests/mock_provider.py
```

## Common Issues

### Provider won't start

```bash
# Test directly
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python tests/mock_provider.py
```

### Permission denied (container)

```yaml
providers:
  memory:
    mode: container
    read_only: false
    volumes:
      - "./data:/app/data:rw"
```

### Tests hang

```bash
pytest tests/ -v --timeout=60
```

