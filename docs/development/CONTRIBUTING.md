# Contributing to MCP Hangar

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- Docker (optional, for container provider tests)

### Installation

```bash
git clone https://github.com/mapyr/mcp-hangar.git
cd mcp-hangar

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -e ".[dev]"
pre-commit install

# Verify installation
pytest tests/ -v -m "not slow"
```

## Project Structure

```
mcp-hangar/
├── mcp_hangar/
│   ├── domain/              # Domain layer (DDD)
│   │   ├── model/           # Aggregates and entities
│   │   ├── services/        # Domain services
│   │   ├── events.py        # Domain events
│   │   ├── exceptions.py    # Domain exceptions
│   │   ├── value_objects.py # Value objects
│   │   └── repository.py    # Repository interfaces
│   ├── application/         # Application layer
│   │   ├── commands/        # CQRS commands
│   │   ├── queries/         # CQRS queries
│   │   ├── event_handlers/  # Event handlers
│   │   ├── sagas/           # Saga patterns
│   │   └── read_models/     # Read models
│   ├── infrastructure/      # Infrastructure layer
│   ├── server.py            # FastMCP server
│   ├── stdio_client.py      # JSON-RPC client
│   └── gc.py                # Background workers
├── tests/
├── examples/
├── docs/
└── pyproject.toml
```

## Code Style

### Formatting

```bash
black mcp_hangar/ tests/ examples/
isort mcp_hangar/ tests/ examples/
ruff check mcp_hangar/ tests/ examples/
ruff check --fix mcp_hangar/ tests/ examples/  # Auto-fix
```

### Pre-commit Hooks

```bash
pre-commit run --all-files
```

### Type Hints

All new code should include type hints:

```python
def invoke_tool(
    self,
    tool_name: str,
    arguments: Dict[str, Any],
    timeout: float = 30.0
) -> Dict[str, Any]:
    ...
```

### Naming Conventions

| Item | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `ProviderManager` |
| Functions/Methods | snake_case | `invoke_tool` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| Private members | _prefix | `_internal_state` |
| Value Objects | PascalCase | `ProviderId` |
| Events | PascalCase + Past tense | `ProviderStarted` |

### Import Order

```python
# Standard library
import json
from typing import Dict, Optional

# Third-party
import pytest

# Local - domain layer
from mcp_hangar.domain.events import ProviderStarted
from mcp_hangar.domain.exceptions import ProviderStartError

# Local - application layer
from mcp_hangar.application.commands import StartProviderCommand

# Local - infrastructure layer
from mcp_hangar.infrastructure.event_bus import get_event_bus
```

## Testing

### Running Tests

```bash
pytest tests/ -v -m "not slow"           # Quick tests
pytest tests/integration/test_provider_manager.py -v  # Specific file
pytest tests/ -m "not slow" --cov=mcp_hangar --cov-report=html
pytest tests/ -v -m unit                 # Unit tests only
pytest tests/ -v -m integration          # Integration tests only
pytest tests/ -v -m docker               # Docker tests only
```

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_value_object_validation():
    ...

@pytest.mark.integration
def test_full_workflow():
    ...

@pytest.mark.slow
def test_stress_performance():
    ...

@pytest.mark.docker
def test_docker_provider():
    ...
```

### Writing Tests

```python
def test_tool_invocation_returns_result():
    # Arrange
    provider = Provider(provider_id="test", mode="subprocess", command=[...])
    
    # Act
    result = provider.invoke_tool("add", {"a": 1, "b": 2})
    
    # Assert
    assert result["result"] == 3
```

### Using Fixtures

```python
@pytest.fixture
def mock_provider():
    spec = ProviderSpec(
        provider_id="test",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"]
    )
    mgr = ProviderManager(spec)
    yield mgr
    mgr.shutdown()
```

Aim for >80% coverage on new code, >90% on critical paths.

## Pull Request Process

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make changes following code style guidelines

3. Add tests for new functionality

4. Run tests and pre-commit:
   ```bash
   pytest tests/ -v -m "not slow"
   pre-commit run --all-files
   ```

5. Update documentation if needed

### PR Description Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] All tests pass locally

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-reviewed the code
- [ ] Added necessary documentation
- [ ] No new warnings
```

### Review Requirements

- All PRs require at least one approval
- CI must pass (tests, linting)
- Coverage should not decrease significantly

## Architecture Guidelines

### Domain-Driven Design

Use Value Objects for validated primitives:
```python
provider_id = ProviderId("my-provider")  # Validated
```

Let Aggregates emit events:
```python
provider.ensure_ready()
events = provider.collect_events()
for event in events:
    event_bus.publish(event)
```

Use Commands for writes, Queries for reads:
```python
command = StartProviderCommand(provider_id="math")
result = command_bus.send(command)

query = ListProvidersQuery(state_filter="ready")
providers = query_bus.execute(query)
```

### Error Handling

Use domain exceptions with context:
```python
from mcp_hangar.domain.exceptions import ProviderStartError

raise ProviderStartError(
    provider_id="my-provider",
    reason="Connection refused",
    details={"host": "localhost", "port": 8080}
)
```

### Logging

Use structured logging:
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"provider_started: {provider_id}, mode={mode}, tools={tools_count}")
```

## Documentation

### Writing Documentation

When adding or modifying features, update the relevant documentation:

1. **API changes**: Update `docs/api/TOOLS_REFERENCE.md`
2. **Configuration changes**: Update `docs/DOCKER_SUPPORT.md` or `README.md`
3. **New features**: Add entries to relevant guides in `docs/guides/`
4. **Architecture changes**: Update `docs/architecture/` documents

### Documentation Style

- Use clear, concise English
- Include code examples where helpful
- Use tables for configuration options and parameters
- Add troubleshooting sections for common issues
- Cross-reference related documents with relative links

### Updating the Changelog

For all user-facing changes, update `CHANGELOG.md`:

```markdown
## [Unreleased]

### Added
- New feature description (#PR_NUMBER)

### Changed
- Modified behavior description (#PR_NUMBER)

### Fixed
- Bug fix description (#PR_NUMBER)

### Security
- Security-related changes (#PR_NUMBER)
```

Follow [Keep a Changelog](https://keepachangelog.com/) format.

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.