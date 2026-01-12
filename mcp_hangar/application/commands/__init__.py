"""Command handlers for CQRS."""

from .commands import (
    Command,
    HealthCheckCommand,
    InvokeToolCommand,
    ShutdownIdleProvidersCommand,
    StartProviderCommand,
    StopProviderCommand,
)
from .handlers import (
    HealthCheckHandler,
    InvokeToolHandler,
    ShutdownIdleProvidersHandler,
    StartProviderHandler,
    StopProviderHandler,
    register_all_handlers,
)

__all__ = [
    # Commands
    "Command",
    "StartProviderCommand",
    "StopProviderCommand",
    "InvokeToolCommand",
    "HealthCheckCommand",
    "ShutdownIdleProvidersCommand",
    # Handlers
    "StartProviderHandler",
    "StopProviderHandler",
    "InvokeToolHandler",
    "HealthCheckHandler",
    "ShutdownIdleProvidersHandler",
    "register_all_handlers",
]
