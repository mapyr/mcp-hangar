"""Unit tests for StdioClient."""

import subprocess
import sys
import threading

import pytest

from mcp_hangar.models import ClientError
from mcp_hangar.stdio_client import StdioClient


class MockEchoServer:
    """Mock server that echoes back JSON-RPC responses."""

    def __init__(self):
        self.process = None

    def start(self):
        """Start the echo server subprocess."""
        # Simple Python script that echoes back responses
        script = """
import sys
import json

while True:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        req = json.loads(line)
        resp = {
            "jsonrpc": "2.0",
            "id": req.get("id"),
            "result": {"echo": req.get("method"), "params": req.get("params")}
        }
        print(json.dumps(resp), flush=True)
    except Exception:
        pass
"""
        self.process = subprocess.Popen(
            [sys.executable, "-c", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return self.process

    def stop(self):
        """Stop the echo server."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)


@pytest.fixture
def echo_server():
    """Fixture providing a mock echo server."""
    server = MockEchoServer()
    process = server.start()
    yield process
    server.stop()


def test_client_basic_call(echo_server):
    """Test basic RPC call and response."""
    client = StdioClient(echo_server)

    response = client.call("test_method", {"arg1": "value1"}, timeout=2.0)

    assert "result" in response
    assert response["result"]["echo"] == "test_method"
    assert response["result"]["params"]["arg1"] == "value1"

    client.close()


def test_client_timeout():
    """Test that timeout works correctly."""
    # Server that never responds
    script = """
import sys
import time
while True:
    line = sys.stdin.readline()
    if not line:
        break
    time.sleep(100)  # Never respond
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    client = StdioClient(process)

    with pytest.raises(TimeoutError):
        client.call("test", {}, timeout=0.5)

    client.close()


def test_client_concurrent_calls(echo_server):
    """Test concurrent calls from multiple threads."""
    client = StdioClient(echo_server)
    results = []
    errors = []

    def make_call(call_id):
        try:
            response = client.call("method", {"id": call_id}, timeout=5.0)
            results.append(response)
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(10):
        t = threading.Thread(target=make_call, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) == 10
    client.close()


def test_client_process_death():
    """Test behavior when process dies."""
    script = """
import sys
import json
# Process a single request then exit
line = sys.stdin.readline()
req = json.loads(line)
resp = {"jsonrpc": "2.0", "id": req["id"], "result": {"ok": True}}
print(json.dumps(resp), flush=True)
sys.exit(0)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    client = StdioClient(process)

    # First call should succeed
    response = client.call("test", {}, timeout=2.0)
    assert "result" in response

    # Wait for process to exit
    process.wait(timeout=2.0)

    # Second call should fail because process is dead
    assert not client.is_alive()

    client.close()


def test_client_closed():
    """Test that calling a closed client raises error."""
    script = "import time; time.sleep(100)"
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    client = StdioClient(process)
    client.close()

    with pytest.raises(ClientError):
        client.call("test", {}, timeout=1.0)


def test_client_context_manager(echo_server):
    """Test client works as context manager."""
    with StdioClient(echo_server) as client:
        response = client.call("test", {}, timeout=2.0)
        assert "result" in response

    # After context, client should be closed
    assert echo_server.poll() is not None  # Process should be terminated
