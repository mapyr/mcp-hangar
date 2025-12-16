#!/usr/bin/env python
"""Test all MCP providers."""

import logging
import os

from mcp_hangar.domain.model import Provider

# Set config path
os.environ["MCP_CONFIG"] = "config.yaml"

# Disable logging
logging.basicConfig(level=logging.WARNING)


def _run_provider_check(name, command) -> None:
    """Test a single provider (helper, not a pytest test)."""
    print(f"\n=== Testing {name} provider ===")
    provider = Provider(
        provider_id=name,
        mode="subprocess",
        command=command,
    )

    try:
        provider.ensure_ready()
        tools = provider.get_tool_names()
        print(f"  State: {provider.state}")
        print(f"  Tools ({len(tools)}): {tools}")
        assert tools is not None
    except Exception:
        import traceback

        traceback.print_exc()
        raise
    finally:
        provider.shutdown()


if __name__ == "__main__":
    results = {}

    # Test filesystem
    try:
        _run_provider_check(
            "filesystem",
            ["mcp-server-filesystem", "/Users/marcin.pyrka"],
        )
        results["filesystem"] = True
    except Exception:
        results["filesystem"] = False

    # Test memory
    try:
        _run_provider_check(
            "memory",
            ["mcp-server-memory"],
        )
        results["memory"] = True
    except Exception:
        results["memory"] = False

    # Test fetch
    try:
        _run_provider_check(
            "fetch",
            ["mcp-fetch"],
        )
        results["fetch"] = True
    except Exception:
        results["fetch"] = False

    # Test math (mock)
    try:
        _run_provider_check(
            "math",
            [
                "/Users/marcin.pyrka/PlayBook/mcp-hangar/venv/bin/python",
                "tests/mock_provider.py",
            ],
        )
        results["math"] = True
    except Exception:
        results["math"] = False

    print("\n=== Summary ===")
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
