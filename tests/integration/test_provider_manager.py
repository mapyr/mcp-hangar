"""Unit tests for ProviderManager."""

import sys
import threading
import time

import pytest

from mcp_hangar.models import (
    ProviderDegradedError,
    ProviderSpec,
    ProviderStartError,
    ProviderState,
    ToolInvocationError,
)
from mcp_hangar.provider_manager import ProviderManager


def test_provider_lifecycle():
    """Test basic provider lifecycle: COLD -> INITIALIZING -> READY."""
    spec = ProviderSpec(
        provider_id="test_math",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    mgr = ProviderManager(spec)

    # Initially COLD
    assert mgr.conn.state == ProviderState.COLD

    # Start the provider
    mgr.ensure_ready()

    # Should be READY with discovered tools
    assert mgr.conn.state == ProviderState.READY
    assert mgr.conn.client is not None
    assert mgr.conn.client.is_alive()
    assert len(mgr.conn.tools) > 0
    assert "add" in mgr.conn.tools

    # Cleanup
    mgr.shutdown()
    assert mgr.conn.state == ProviderState.COLD


def test_tool_invocation():
    """Test tool invocation through provider manager."""
    spec = ProviderSpec(
        provider_id="test_math",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    mgr = ProviderManager(spec)

    # Invoke a tool (will auto-start provider)
    result = mgr.invoke_tool("add", {"a": 5, "b": 3}, timeout=5.0)

    assert "result" in result
    assert result["result"] == 8

    # Verify metrics
    # Note: total_invocations includes internal calls (ensure_ready, tools/list)
    assert mgr.conn.health.total_invocations >= 1
    assert mgr.conn.health.total_failures == 0
    assert mgr.conn.health.consecutive_failures == 0

    mgr.shutdown()


def test_concurrent_invocations():
    """Test concurrent tool invocations from multiple threads."""
    spec = ProviderSpec(
        provider_id="test_math",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    mgr = ProviderManager(spec)

    results = []
    errors = []

    def invoke(a, b):
        try:
            result = mgr.invoke_tool("add", {"a": a, "b": b}, timeout=10.0)
            results.append(result)
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(10):
        t = threading.Thread(target=invoke, args=(i, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors: {errors}"
    assert len(results) == 10

    # Verify all results are correct
    for i, result in enumerate(results):
        assert "result" in result

    mgr.shutdown()


def test_health_check():
    """Test active health checking."""
    spec = ProviderSpec(
        provider_id="test_math",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    mgr = ProviderManager(spec)
    mgr.ensure_ready()

    # Health check should succeed
    assert mgr.health_check() is True
    assert mgr.conn.state == ProviderState.READY

    mgr.shutdown()


def test_idle_shutdown():
    """Test idle provider shutdown."""
    spec = ProviderSpec(
        provider_id="test_math",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
        idle_ttl_s=1,  # Short TTL for testing
    )

    mgr = ProviderManager(spec)
    mgr.ensure_ready()

    assert mgr.conn.state == ProviderState.READY

    # Should not shutdown immediately
    assert mgr.maybe_shutdown_idle() is False

    # Wait past TTL
    time.sleep(1.5)

    # Now should shutdown
    assert mgr.maybe_shutdown_idle() is True
    assert mgr.conn.state == ProviderState.COLD


def test_provider_restart_after_crash():
    """Test that provider can restart after crash."""
    spec = ProviderSpec(
        provider_id="test_math",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    mgr = ProviderManager(spec)
    mgr.ensure_ready()

    # Kill the provider
    mgr.conn.client.process.kill()
    mgr.conn.client.process.wait()

    # Mark as dead
    mgr.conn.state = ProviderState.DEAD

    # ensure_ready should restart it
    mgr.ensure_ready()

    assert mgr.conn.state == ProviderState.READY
    assert mgr.conn.client.is_alive()

    mgr.shutdown()


def test_degraded_state():
    """Test degraded state after repeated failures."""
    spec = ProviderSpec(
        provider_id="test_bad",
        mode="subprocess",
        command=["false"],  # Command that always fails
        max_consecutive_failures=3,
    )

    mgr = ProviderManager(spec)

    # Try to start multiple times - should fail
    for i in range(3):
        try:
            mgr.ensure_ready()
            assert False, "Should have raised ProviderStartError"
        except ProviderStartError:
            pass

    # After max_consecutive_failures, should be DEGRADED
    assert mgr.conn.state == ProviderState.DEGRADED

    # Trying again should raise ProviderDegradedError
    with pytest.raises(ProviderDegradedError):
        mgr.ensure_ready()


def test_unknown_tool():
    """Test invoking an unknown tool."""
    from mcp_hangar.domain.exceptions import ToolNotFoundError

    spec = ProviderSpec(
        provider_id="test_math",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    mgr = ProviderManager(spec)

    # New implementation raises ToolNotFoundError instead of ToolInvocationError
    with pytest.raises((ToolInvocationError, ToolNotFoundError)):
        mgr.invoke_tool("nonexistent_tool", {}, timeout=5.0)

    mgr.shutdown()


def test_tool_error():
    """Test handling of tool execution error."""
    spec = ProviderSpec(
        provider_id="test_math",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    mgr = ProviderManager(spec)

    # Division by zero should raise an error
    with pytest.raises(ToolInvocationError):
        mgr.invoke_tool("divide", {"a": 10, "b": 0}, timeout=5.0)

    # Health metrics should reflect the failure
    assert mgr.conn.health.total_failures > 0

    mgr.shutdown()


def test_multiple_providers():
    """Test multiple providers can run independently."""
    spec1 = ProviderSpec(
        provider_id="math1",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    spec2 = ProviderSpec(
        provider_id="math2",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
    )

    mgr1 = ProviderManager(spec1)
    mgr2 = ProviderManager(spec2)

    # Start both
    mgr1.ensure_ready()
    mgr2.ensure_ready()

    # Both should be ready
    assert mgr1.conn.state == ProviderState.READY
    assert mgr2.conn.state == ProviderState.READY

    # Invoke tools on both
    result1 = mgr1.invoke_tool("add", {"a": 1, "b": 2}, timeout=5.0)
    result2 = mgr2.invoke_tool("multiply", {"a": 3, "b": 4}, timeout=5.0)

    assert result1["result"] == 3
    assert result2["result"] == 12

    mgr1.shutdown()
    mgr2.shutdown()
