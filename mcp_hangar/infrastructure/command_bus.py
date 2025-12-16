"""
Command Bus - dispatches commands to their handlers.

Commands represent intent to change the system state.
Each command has exactly one handler.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Optional, Type

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Command(ABC):
    """Base class for all commands.

    Commands are immutable and represent a request to perform an action.
    They should be named in imperative form (StartProvider, not ProviderStarted).
    """

    pass


@dataclass(frozen=True)
class StartProviderCommand(Command):
    """Command to start a provider."""

    provider_id: str


@dataclass(frozen=True)
class StopProviderCommand(Command):
    """Command to stop a provider."""

    provider_id: str
    reason: str = "user_request"


@dataclass(frozen=True)
class InvokeToolCommand(Command):
    """Command to invoke a tool on a provider."""

    provider_id: str
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0


@dataclass(frozen=True)
class HealthCheckCommand(Command):
    """Command to perform health check on a provider."""

    provider_id: str


@dataclass(frozen=True)
class ShutdownIdleProvidersCommand(Command):
    """Command to shutdown all idle providers."""

    pass


class CommandHandler(ABC):
    """Base class for command handlers."""

    @abstractmethod
    def handle(self, command: Command) -> Any:
        """Handle the command and return result."""
        pass


class CommandBus:
    """
    Dispatches commands to their registered handlers.

    Each command type can have exactly one handler.
    The bus is responsible for routing commands to the appropriate handler.
    """

    def __init__(self):
        self._handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, command_type: Type[Command], handler: CommandHandler) -> None:
        """
        Register a handler for a command type.

        Args:
            command_type: The type of command to handle
            handler: The handler instance

        Raises:
            ValueError: If a handler is already registered for this command type
        """
        if command_type in self._handlers:
            raise ValueError(f"Handler already registered for {command_type.__name__}")
        self._handlers[command_type] = handler
        logger.debug(f"Registered handler for {command_type.__name__}")

    def unregister(self, command_type: Type[Command]) -> bool:
        """
        Unregister a handler for a command type.

        Returns:
            True if handler was removed, False if not found
        """
        if command_type in self._handlers:
            del self._handlers[command_type]
            return True
        return False

    def send(self, command: Command) -> Any:
        """
        Send a command to its handler.

        Args:
            command: The command to execute

        Returns:
            The result from the handler

        Raises:
            ValueError: If no handler is registered for this command type
        """
        command_type = type(command)
        handler = self._handlers.get(command_type)

        if handler is None:
            raise ValueError(f"No handler registered for {command_type.__name__}")

        logger.debug(f"Dispatching {command_type.__name__}")
        return handler.handle(command)

    def has_handler(self, command_type: Type[Command]) -> bool:
        """Check if a handler is registered for the command type."""
        return command_type in self._handlers


# Global command bus instance
_command_bus: Optional[CommandBus] = None


def get_command_bus() -> CommandBus:
    """Get the global command bus instance."""
    global _command_bus
    if _command_bus is None:
        _command_bus = CommandBus()
    return _command_bus


def reset_command_bus() -> None:
    """Reset the global command bus (for testing)."""
    global _command_bus
    _command_bus = None
