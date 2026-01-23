# Changelog

All notable changes to this package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-01-24

### Added
- Enhanced `ProviderStartError` with diagnostic information:
  - `stderr`: Captured process stderr output
  - `exit_code`: Process exit code for failed starts
  - `suggestion`: Actionable suggestions based on error patterns
  - `get_user_message()`: Human-readable error message method
- Automatic error pattern detection with suggestions for:
  - Python errors (ModuleNotFoundError, ImportError, SyntaxError)
  - Permission and file errors
  - Network/connection errors
  - Docker/Podman container issues
  - Memory/resource errors
  - Common exit codes (1, 2, 126, 127, 137, 139)

## [0.3.0] - 2026-01-21

### Added
- Facade API: `Hangar` class for simplified provider management
- HangarConfig Builder with fluent API
- RichToolInvocationError with detailed diagnostics
- Error categorization (user_error, provider_error, infra_error)

### Improved
- Thread-safe lock hierarchy with `HierarchicalLockManager`

## [0.2.3] - 2026-01-20

### Fixed
- Improved error diagnostics for provider startup failures
- `StdioClient` now captures stderr when process dies
- `Provider._handle_start_failure()` receives actual exception

## [0.2.2] - 2026-01-19

### Fixed
- Re-enable mypy type checking with gradual adoption
- Configure mypy with relaxed settings

## [0.2.1] - 2026-01-18

### Fixed
- Add missing `ToolSchema` export in `models.py`
- Fix Python lint errors

## [0.2.0] - 2026-01-18

### Added
- Monorepo structure with packages/core for Python code
- CQRS + Event Sourcing architecture
- Provider state machine with COLD -> INITIALIZING -> READY -> DEGRADED -> DEAD transitions
- Health monitoring with circuit breakers
- Prometheus metrics at /metrics
- Structured JSON logging via structlog
- Authentication & Authorization (API Key, JWT/OIDC, RBAC)

### Changed
- Restructured from flat layout to packages/core/

## [0.1.0] - 2025-01-01

### Added
- Initial release
- Basic provider management
- MCP protocol support
