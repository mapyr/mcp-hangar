#!/usr/bin/env python3
"""
Simple local test script for MCP Registry.

Usage:
    python test_local.py

This script tests the registry by directly using the ProviderManager
without going through the MCP server protocol.
"""

from pathlib import Path
import sys
import time

# Ensure the project is in path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    print("=" * 60)
    print("🚀 MCP Registry - Local Test")
    print("=" * 60)

    # Import after path setup
    from mcp_hangar.models import ProviderSpec
    from mcp_hangar.provider_manager import ProviderManager

    # Create a math provider configuration using the mock provider (compatible with registry)
    print("\n📦 Creating math provider using mock_provider.py...")
    spec = ProviderSpec(
        provider_id="math_test",
        mode="subprocess",
        command=[sys.executable, "tests/mock_provider.py"],
        idle_ttl_s=300,
        health_check_interval_s=60,
        max_consecutive_failures=3,
    )

    # Create manager
    manager = ProviderManager(spec)
    print(f"   Initial state: {manager.state}")

    # Start the provider
    print("\n🔄 Starting provider...")
    try:
        manager.ensure_ready()
        print(f"   ✅ Provider started! State: {manager.state}")
    except Exception as e:
        print(f"   ❌ Failed to start: {e}")
        return 1

    # Give it a moment to fully initialize
    time.sleep(0.5)

    # Discover tools
    print("\n🔍 Discovering tools...")
    try:
        tools = manager.get_tool_names()
        print(f"   ✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"      - {tool}")
    except Exception as e:
        print(f"   ❌ Failed to discover tools: {e}")
        manager.shutdown()
        return 1

    # Test mathematical operations
    print("\n🧮 Testing math operations...")

    test_cases = [
        ("add", {"a": 5, "b": 3}, "5 + 3"),
        ("subtract", {"a": 10, "b": 4}, "10 - 4"),
        ("multiply", {"a": 7, "b": 6}, "7 × 6"),
        ("divide", {"a": 100, "b": 4}, "100 ÷ 4"),
        ("power", {"base": 2, "exponent": 10}, "2^10"),
    ]

    all_passed = True
    for tool_name, args, description in test_cases:
        try:
            result = manager.invoke_tool(tool_name, args)
            print(f"   ✅ {description} = {result.get('result', result)}")
        except Exception as e:
            print(f"   ❌ {description} failed: {e}")
            all_passed = False

    # Test error handling - division by zero
    print("\n⚠️  Testing error handling (division by zero)...")
    try:
        result = manager.invoke_tool("divide", {"a": 10, "b": 0})
        print(f"   ❌ Should have raised error, got: {result}")
        all_passed = False
    except Exception as e:
        print(f"   ✅ Correctly raised error: {type(e).__name__}")

    # Check health
    print("\n💓 Checking provider health...")
    try:
        manager.health_check()
        print(f"   ✅ Health check passed: alive={manager.is_alive}")
    except Exception as e:
        print(f"   ⚠️  Health check: {e}")

    # Get provider info
    print("\n📊 Provider Status:")
    print(f"   State: {manager.state}")
    print(f"   Alive: {manager.is_alive}")
    print(f"   Tools cached: {len(manager.tools) if manager.tools else 0}")

    # Stop the provider
    print("\n🛑 Stopping provider...")
    try:
        manager.shutdown()
        print(f"   ✅ Provider stopped. Final state: {manager.state}")
    except Exception as e:
        print(f"   ❌ Failed to stop: {e}")

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed!")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
