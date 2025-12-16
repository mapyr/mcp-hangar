"""Registry server with FastMCP integration, CQRS, security hardening, and structured logging."""

import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
import yaml

from .application.commands import register_all_handlers as register_command_handlers
from .application.event_handlers import (
    AlertEventHandler,
    AuditEventHandler,
    LoggingEventHandler,
    MetricsEventHandler,
)
from .application.mcp.tooling import (
    chain_validators,
    key_global,
    key_registry_invoke,
    mcp_tool_wrapper,
)
from .application.queries import register_all_handlers as register_query_handlers
from .bootstrap.runtime import create_runtime
from .domain.exceptions import RateLimitExceeded
from .domain.model import Provider
from .domain.security.input_validator import (
    validate_arguments,
    validate_provider_id,
    validate_timeout,
    validate_tool_name,
)
from .domain.security.sanitizer import sanitize_log_message
from .gc import BackgroundWorker
from .infrastructure.command_bus import (
    InvokeToolCommand,
    StartProviderCommand,
    StopProviderCommand,
)
from .infrastructure.query_bus import (
    GetProviderQuery,
    GetProviderToolsQuery,
    ListProvidersQuery,
)


# Structured JSON logging to stderr
class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "message": sanitize_log_message(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(level=logging.INFO):
    """Set up structured JSON logging to stderr."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Remove any existing handlers
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


# Initialize MCP server
mcp = FastMCP("mcp-registry")

# Runtime wiring (no module-level singletons)
_RUNTIME = create_runtime()

# Convenience bindings used throughout this module
PROVIDER_REPOSITORY = _RUNTIME.repository
EVENT_BUS = _RUNTIME.event_bus
COMMAND_BUS = _RUNTIME.command_bus
QUERY_BUS = _RUNTIME.query_bus
RATE_LIMIT_CONFIG = _RUNTIME.rate_limit_config
RATE_LIMITER = _RUNTIME.rate_limiter
INPUT_VALIDATOR = _RUNTIME.input_validator
SECURITY_HANDLER = _RUNTIME.security_handler


# Backward compatibility: PROVIDERS dict backed by repository
class ProviderDict:
    """Dictionary-like wrapper around provider repository for backward compatibility."""

    def __init__(self, repository):
        self._repo = repository

    def __getitem__(self, key):
        provider = self._repo.get(key)
        if provider is None:
            raise KeyError(key)
        return provider

    def __setitem__(self, key, value):
        self._repo.add(key, value)

    def __contains__(self, key):
        return self._repo.exists(key)

    def get(self, key, default=None):
        return self._repo.get(key) or default

    def items(self):
        return self._repo.get_all().items()

    def keys(self):
        return self._repo.get_all_ids()

    def values(self):
        return self._repo.get_all().values()


PROVIDERS = ProviderDict(PROVIDER_REPOSITORY)


def _check_rate_limit(key: str = "global") -> None:
    """Check rate limit and raise exception if exceeded."""
    result = RATE_LIMITER.consume(key)
    if not result.allowed:
        SECURITY_HANDLER.log_rate_limit_exceeded(
            limit=result.limit,
            window_seconds=int(1.0 / RATE_LIMIT_CONFIG.requests_per_second),
        )
        raise RateLimitExceeded(
            limit=result.limit,
            window_seconds=int(1.0 / RATE_LIMIT_CONFIG.requests_per_second),
        )


def _tool_error_mapper(exc: Exception) -> dict:
    """Map exceptions to a stable MCP tool error payload."""
    # Keep payload minimal and stable for clients; preserve type for debugging.
    return {
        "error": str(exc) or "unknown error",
        "type": type(exc).__name__,
        "details": {},
    }


def _tool_error_hook(exc: Exception, context: dict) -> None:
    """Best-effort hook for logging/security telemetry on tool failures.

    NOTE: SecurityEventHandler does not expose a dedicated `log_tool_error` API.
    We map tool failures onto an existing, stable API (`log_validation_failed`)
    to avoid crashing the tool execution path.
    """
    try:
        SECURITY_HANDLER.log_validation_failed(
            field="tool",
            message=f"{type(exc).__name__}: {str(exc) or 'unknown error'}",
            provider_id=context.get("provider_id"),
            value=context.get("provider_id"),
        )
    except Exception:
        # Security handler logging must never break the tool call path.
        pass


def _validate_provider_id(provider: str) -> None:
    """Validate provider ID and raise exception if invalid."""
    result = validate_provider_id(provider)
    if not result.valid:
        SECURITY_HANDLER.log_validation_failed(
            field="provider",
            message=(
                result.errors[0].message if result.errors else "Invalid provider ID"
            ),
            provider_id=provider,
        )
        raise ValueError(
            f"invalid_provider_id: {result.errors[0].message if result.errors else 'validation failed'}"
        )


def _validate_tool_name_input(tool: str) -> None:
    """Validate tool name and raise exception if invalid."""
    result = validate_tool_name(tool)
    if not result.valid:
        SECURITY_HANDLER.log_validation_failed(
            field="tool",
            message=result.errors[0].message if result.errors else "Invalid tool name",
        )
        raise ValueError(
            f"invalid_tool_name: {result.errors[0].message if result.errors else 'validation failed'}"
        )


def _validate_arguments_input(arguments: dict) -> None:
    """Validate tool arguments and raise exception if invalid."""
    result = validate_arguments(arguments)
    if not result.valid:
        SECURITY_HANDLER.log_validation_failed(
            field="arguments",
            message=result.errors[0].message if result.errors else "Invalid arguments",
        )
        raise ValueError(
            f"invalid_arguments: {result.errors[0].message if result.errors else 'validation failed'}"
        )


def _validate_timeout_input(timeout: float) -> None:
    """Validate timeout and raise exception if invalid."""
    result = validate_timeout(timeout)
    if not result.valid:
        SECURITY_HANDLER.log_validation_failed(
            field="timeout",
            message=result.errors[0].message if result.errors else "Invalid timeout",
        )
        raise ValueError(
            f"invalid_timeout: {result.errors[0].message if result.errors else 'validation failed'}"
        )


@mcp.tool(name="registry_list")
@mcp_tool_wrapper(
    tool_name="registry_list",
    rate_limit_key=key_global,
    check_rate_limit=lambda key: _check_rate_limit("registry_list"),
    validate=None,
    error_mapper=lambda exc: _tool_error_mapper(exc),
    on_error=_tool_error_hook,
)
def registry_list(state_filter: Optional[str] = None) -> dict:
    """
    List all providers with status and metadata.

    Args:
        state_filter: Optional filter by state (cold, ready, degraded, dead)

    Returns:
        Dictionary with 'providers' key containing list of provider info
    """
    query = ListProvidersQuery(state_filter=state_filter)
    summaries = QUERY_BUS.execute(query)
    return {"providers": [s.to_dict() for s in summaries]}


@mcp.tool(name="registry_start")
@mcp_tool_wrapper(
    tool_name="registry_start",
    rate_limit_key=lambda provider: f"registry_start:{provider}",
    check_rate_limit=_check_rate_limit,
    validate=_validate_provider_id,
    error_mapper=lambda exc: _tool_error_mapper(exc),
    on_error=lambda exc, ctx: _tool_error_hook(exc, ctx),
)
def registry_start(provider: str) -> dict:
    """
    Explicitly start a provider and discover tools.

    Args:
        provider: Provider ID to start

    Returns:
        Dictionary with provider state and tools

    Raises:
        ValueError: If provider ID is unknown or invalid
    """
    if provider not in PROVIDERS:
        raise ValueError(f"unknown_provider: {provider}")

    command = StartProviderCommand(provider_id=provider)
    return COMMAND_BUS.send(command)


@mcp.tool(name="registry_stop")
@mcp_tool_wrapper(
    tool_name="registry_stop",
    rate_limit_key=lambda provider: f"registry_stop:{provider}",
    check_rate_limit=_check_rate_limit,
    validate=_validate_provider_id,
    error_mapper=lambda exc: _tool_error_mapper(exc),
    on_error=lambda exc, ctx: _tool_error_hook(exc, ctx),
)
def registry_stop(provider: str) -> dict:
    """
    Explicitly stop a provider.

    Args:
        provider: Provider ID to stop

    Returns:
        Confirmation dictionary

    Raises:
        ValueError: If provider ID is unknown or invalid
    """
    if provider not in PROVIDERS:
        raise ValueError(f"unknown_provider: {provider}")

    command = StopProviderCommand(provider_id=provider)
    return COMMAND_BUS.send(command)


@mcp.tool(name="registry_tools")
@mcp_tool_wrapper(
    tool_name="registry_tools",
    rate_limit_key=lambda provider: f"registry_tools:{provider}",
    check_rate_limit=_check_rate_limit,
    validate=_validate_provider_id,
    error_mapper=lambda exc: _tool_error_mapper(exc),
    on_error=lambda exc, ctx: _tool_error_hook(exc, ctx),
)
def registry_tools(provider: str) -> dict:
    """
    Get detailed tool schemas for a provider.

    Args:
        provider: Provider ID

    Returns:
        Dictionary with provider ID and list of tool schemas

    Raises:
        ValueError: If provider ID is unknown or invalid
    """
    if provider not in PROVIDERS:
        raise ValueError(f"unknown_provider: {provider}")

    # Ensure provider is ready first
    COMMAND_BUS.send(StartProviderCommand(provider_id=provider))

    # Then query tools
    query = GetProviderToolsQuery(provider_id=provider)
    tools = QUERY_BUS.execute(query)
    return {"provider": provider, "tools": [t.to_dict() for t in tools]}


@mcp.tool(name="registry_invoke")
@mcp_tool_wrapper(
    tool_name="registry_invoke",
    rate_limit_key=key_registry_invoke,
    check_rate_limit=_check_rate_limit,
    validate=chain_validators(
        lambda provider, tool, arguments, timeout=30.0: _validate_provider_id(provider),
        lambda provider, tool, arguments, timeout=30.0: _validate_tool_name_input(tool),
        lambda provider, tool, arguments, timeout=30.0: _validate_arguments_input(
            arguments
        ),
        lambda provider, tool, arguments, timeout=30.0: _validate_timeout_input(
            timeout
        ),
    ),
    error_mapper=lambda exc: _tool_error_mapper(exc),
    on_error=lambda exc, ctx: _tool_error_hook(exc, ctx),
)
def registry_invoke(
    provider: str, tool: str, arguments: dict, timeout: float = 30.0
) -> dict:
    """
    Invoke a tool on a provider.

    Args:
        provider: Provider ID
        tool: Tool name
        arguments: Tool arguments
        timeout: Timeout in seconds (default: 30.0)

    Returns:
        Tool result

    Raises:
        ValueError: If provider ID is unknown or inputs are invalid
    """
    if provider not in PROVIDERS:
        raise ValueError(f"unknown_provider: {provider}")

    command = InvokeToolCommand(
        provider_id=provider,
        tool_name=tool,
        arguments=arguments,
        timeout=timeout,
    )
    return COMMAND_BUS.send(command)


@mcp.tool(name="registry_details")
@mcp_tool_wrapper(
    tool_name="registry_details",
    rate_limit_key=lambda provider: f"registry_details:{provider}",
    check_rate_limit=_check_rate_limit,
    validate=_validate_provider_id,
    error_mapper=lambda exc: _tool_error_mapper(exc),
    on_error=lambda exc, ctx: _tool_error_hook(exc, ctx),
)
def registry_details(provider: str) -> dict:
    """
    Get detailed information about a provider.

    Args:
        provider: Provider ID

    Returns:
        Dictionary with full provider details

    Raises:
        ValueError: If provider ID is unknown or invalid
    """
    if provider not in PROVIDERS:
        raise ValueError(f"unknown_provider: {provider}")

    query = GetProviderQuery(provider_id=provider)
    details = QUERY_BUS.execute(query)
    return details.to_dict()


@mcp.tool(name="registry_health")
@mcp_tool_wrapper(
    tool_name="registry_health",
    rate_limit_key=key_global,
    check_rate_limit=lambda key: _check_rate_limit("registry_health"),
    validate=None,
    error_mapper=lambda exc: _tool_error_mapper(exc),
    on_error=_tool_error_hook,
)
def registry_health() -> dict:
    """
    Get registry health status including security metrics.

    Returns:
        Dictionary with health information
    """
    # Get rate limiter stats
    rate_limit_stats = RATE_LIMITER.get_stats()

    # Get provider counts by state
    providers = list(PROVIDERS.values())
    state_counts = {}
    for p in providers:
        state = str(p.state)
        state_counts[state] = state_counts.get(state, 0) + 1

    return {
        "status": "healthy",
        "providers": {
            "total": len(providers),
            "by_state": state_counts,
        },
        "security": {
            "rate_limiting": rate_limit_stats,
        },
    }


def load_config_from_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    if not config or "providers" not in config:
        raise ValueError(
            f"Invalid configuration: missing 'providers' section in {config_path}"
        )

    return config


def load_config(config: Dict[str, Any]) -> None:
    """
    Load provider configuration.

    Creates Provider aggregates directly.

    Args:
        config: Dictionary mapping provider IDs to provider spec dictionaries
    """
    for provider_id, spec_dict in config.items():
        # Validate provider ID
        result = validate_provider_id(provider_id)
        if not result.valid:
            logger = logging.getLogger(__name__)
            logger.warning(f"Skipping provider with invalid ID: {provider_id}")
            continue

        # Resolve user if set to "current"
        user = spec_dict.get("user")
        if user == "current":
            import os

            user = f"{os.getuid()}:{os.getgid()}"

        provider = Provider(
            provider_id=provider_id,
            mode=spec_dict.get("mode", "subprocess"),
            command=spec_dict.get("command"),
            image=spec_dict.get("image"),
            endpoint=spec_dict.get("endpoint"),
            env=spec_dict.get("env", {}),
            idle_ttl_s=spec_dict.get("idle_ttl_s", 300),
            health_check_interval_s=spec_dict.get("health_check_interval_s", 60),
            max_consecutive_failures=spec_dict.get("max_consecutive_failures", 3),
            # Container-specific options
            volumes=spec_dict.get("volumes", []),
            build=spec_dict.get("build"),
            resources=spec_dict.get("resources", {"memory": "512m", "cpu": "1.0"}),
            network=spec_dict.get("network", "none"),
            read_only=spec_dict.get("read_only", True),
            user=user,
            description=spec_dict.get("description"),
        )
        PROVIDERS[provider_id] = provider


def main():
    """Main entry point for the registry server."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Registry Server")
    parser.add_argument("--http", action="store_true", help="Run HTTP server mode")
    parser.add_argument(
        "--host", type=str, default=None, help="HTTP server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="HTTP server port (default: 8000)"
    )
    args = parser.parse_args()

    # Get settings from environment or args
    http_mode = args.http or os.getenv("MCP_MODE", "stdio") == "http"
    http_host = args.host or os.getenv("MCP_HTTP_HOST", "0.0.0.0")
    http_port = args.port or int(os.getenv("MCP_HTTP_PORT", "8000"))

    setup_logging(level=logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info(f"mcp_registry_starting mode={'http' if http_mode else 'stdio'}")

    # Ensure data directory exists for persistent storage (volumes)
    data_dir = Path("./data")
    if not data_dir.exists():
        try:
            data_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
            logger.info(f"Created data directory: {data_dir.absolute()}")
        except OSError as e:
            logger.warning(f"Could not create data directory: {e}")

    # Initialize runtime dependencies (repository, buses, security plumbing)
    runtime = create_runtime()

    # Use the runtime repository for provider storage (keep PROVIDERS/PROVIDER_REPOSITORY consistent)
    global PROVIDER_REPOSITORY, PROVIDERS
    PROVIDER_REPOSITORY = runtime.repository
    PROVIDERS = ProviderDict(PROVIDER_REPOSITORY)

    # Initialize event bus and register handlers
    event_bus = runtime.event_bus

    # Register logging handler (logs all events)
    logging_handler = LoggingEventHandler()
    event_bus.subscribe_to_all(logging_handler.handle)

    # Register metrics handler (collects metrics from events)
    metrics_handler = MetricsEventHandler()
    event_bus.subscribe_to_all(metrics_handler.handle)

    # Register alert handler (sends alerts for critical events)
    alert_handler = AlertEventHandler()
    event_bus.subscribe_to_all(alert_handler.handle)

    # Register audit handler (records all events)
    audit_handler = AuditEventHandler()
    event_bus.subscribe_to_all(audit_handler.handle)

    # Register security handler (monitors for security events)
    security_handler = runtime.security_handler
    event_bus.subscribe_to_all(security_handler.handle)

    logger.info("event_handlers_registered: logging, metrics, alert, audit, security")

    # Initialize CQRS - register command and query handlers
    command_bus = runtime.command_bus
    query_bus = runtime.query_bus

    register_command_handlers(command_bus, PROVIDER_REPOSITORY, event_bus)
    register_query_handlers(query_bus, PROVIDER_REPOSITORY)

    logger.info("cqrs_handlers_registered")

    # Log security configuration
    logger.info(
        f"security_config: rate_limit_rps={runtime.rate_limit_config.requests_per_second}, "
        f"burst_size={runtime.rate_limit_config.burst_size}"
    )

    # Load configuration from file or use default example config
    config_path = os.getenv("MCP_CONFIG", "config.yaml")

    if Path(config_path).exists():
        logger.info(f"loading_config_from_file: {config_path}")
        try:
            full_config = load_config_from_file(config_path)
            provider_config = full_config.get("providers", {})
            load_config(provider_config)
        except Exception as e:
            logger.error(f"config_load_failed: {e}")
            raise
    else:
        logger.info("using_default_config: no config.yaml found")
        # Example configuration - in production, create config.yaml
        example_config = {
            "math_subprocess": {
                "mode": "subprocess",
                "command": ["python", "-m", "examples.provider_math.server"],
                "idle_ttl_s": 180,
            },
            # Uncomment to test Docker mode:
            # "math_docker": {
            #     "mode": "docker",
            #     "image": "mcp-math:latest",
            #     "idle_ttl_s": 300
            # }
        }
        load_config(example_config)

    # Start background workers
    gc_worker = BackgroundWorker(PROVIDERS, interval_s=30, task="gc")
    gc_worker.start()

    health_worker = BackgroundWorker(PROVIDERS, interval_s=60, task="health_check")
    health_worker.start()

    logger.info(f"mcp_registry_ready: providers={list(PROVIDERS.keys())}")
    # Also print to stderr with flush for Docker detection
    print(
        f"mcp_registry_ready: providers={list(PROVIDERS.keys())}",
        file=sys.stderr,
        flush=True,
    )

    # Choose server mode based on arguments/environment
    if http_mode:
        # HTTP Server Mode using FastMCP
        logger.info(f"Starting HTTP server on {http_host}:{http_port}")
        from .fastmcp_server import run_fastmcp_server, setup_fastmcp_server

        # Setup FastMCP server with registry function references
        setup_fastmcp_server(
            registry_list_fn=registry_list,
            registry_start_fn=registry_start,
            registry_stop_fn=registry_stop,
            registry_tools_fn=registry_tools,
            registry_invoke_fn=registry_invoke,
            registry_details_fn=registry_details,
            registry_health_fn=registry_health,
        )

        # Run FastMCP server (blocking)
        run_fastmcp_server()
    else:
        # Stdio Mode (default)
        logger.info("Starting stdio server (FastMCP)")
        try:
            mcp.run()
        except Exception as e:
            logger.error(f"mcp_server_error: {e}")
            # Keep the process alive for Docker health checks
            import time

            while True:
                time.sleep(60)


if __name__ == "__main__":
    main()
