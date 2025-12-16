"""Domain model - Aggregates and entities."""

# Re-export ProviderState from value_objects for convenience
from ..value_objects import ProviderState
from .aggregate import AggregateRoot
from .event_sourced_provider import EventSourcedProvider, ProviderSnapshot
from .health_tracker import HealthTracker
from .provider import Provider
from .tool_catalog import ToolCatalog, ToolSchema

__all__ = [
    "AggregateRoot",
    "HealthTracker",
    "ToolCatalog",
    "ToolSchema",
    "Provider",
    "ProviderState",
    "EventSourcedProvider",
    "ProviderSnapshot",
]
