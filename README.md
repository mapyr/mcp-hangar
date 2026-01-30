# MCP Hangar

[![PyPI](https://img.shields.io/pypi/v/mcp-hangar)](https://pypi.org/project/mcp-hangar/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Parallel MCP tool execution. One interface. 50x faster.**

## The Problem

Your AI agent calls 5 tools sequentially. Each takes 200ms. That's 1 second of waiting.

Hangar runs them in parallel. 200ms total. Same results, 50x faster.

## Quick Start

```bash
curl -sSL https://get.mcp-hangar.io | bash
```

**1. Create config** (`~/.hangar/config.yaml`):

```yaml
providers:
  - id: github
    command: ["uvx", "mcp-server-github"]
  - id: slack
    command: ["uvx", "mcp-server-slack"]
  - id: internal-api
    url: "http://localhost:8080"
```

**2. Add to Claude Code** (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "hangar": {
      "command": "mcp-hangar",
      "args": ["serve"]
    }
  }
}
```

**3. Restart Claude Code.** Done.

## One Interface

```python
hangar_call([
    {"provider": "github", "tool": "search_repos", "arguments": {"query": "mcp"}},
    {"provider": "slack", "tool": "post_message", "arguments": {"channel": "#dev"}},
    {"provider": "internal-api", "tool": "get_status", "arguments": {}}
])
```

Single call. Parallel execution. All results returned together.

## Benchmarks

| Scenario | Sequential | Hangar | Speedup |
|----------|-----------|--------|---------|
| 15 tools, 2 providers | ~20s | 380ms | 50x |
| 50 concurrent requests | ~15s | 1.3s | 10x |
| Cold start + batch | ~5s | <500ms | 10x |

100% success rate. <10ms framework overhead.

## Why It's Fast

**Single-flight cold starts.** When 10 parallel calls hit a cold provider, it initializes once — not 10 times.

**Automatic concurrency.** Configurable parallelism with backpressure. No thundering herd.

**Provider pooling.** Hot providers stay warm. Cold providers spin up on demand, shut down after idle TTL.

## Production Ready

**Lifecycle management.** Lazy loading, health checks, automatic restart, graceful shutdown.

**Circuit breaker.** One failing provider doesn't kill your batch. Automatic isolation and recovery.

**Observability.** Correlation IDs across parallel calls. OpenTelemetry traces, Prometheus metrics.

**Multi-provider.** Subprocess, Docker, remote HTTP — mix them in a single batch call.

## Configuration

```yaml
providers:
  - id: fast-provider
    command: ["python", "fast.py"]
    idle_ttl_s: 300              # Shutdown after 5min idle
    health_check_interval_s: 60  # Check health every minute
    max_consecutive_failures: 3  # Circuit breaker threshold

  - id: docker-provider
    image: my-registry/mcp-server:latest
    network: bridge

  - id: remote-provider
    url: "https://api.example.com/mcp"
```

## Works Everywhere

- **Home lab:** 2 providers, zero config complexity
- **Team setup:** Shared providers, Docker containers
- **Enterprise:** 50+ providers, observability stack, Kubernetes

Same API. Same reliability. Different scale.

## Documentation

- [Getting Started](https://mcp-hangar.io/getting-started/)
- [Configuration Reference](https://mcp-hangar.io/configuration/)
- [Claude Code Integration](https://mcp-hangar.io/guides/claude-code/)
- [Observability Setup](https://mcp-hangar.io/guides/observability/)

## License

MIT — use it, fork it, ship it.

---

[Docs](https://mcp-hangar.io) · [PyPI](https://pypi.org/project/mcp-hangar/) · [GitHub](https://github.com/mapyr/mcp-hangar)
