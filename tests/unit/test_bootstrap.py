"""Tests for server/bootstrap.py module.

Tests cover application bootstrapping and dependency injection.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_hangar.server.bootstrap import (
    ApplicationContext,
    bootstrap,
    GC_WORKER_INTERVAL_SECONDS,
    HEALTH_CHECK_INTERVAL_SECONDS,
    _auto_add_volumes,
    _create_background_workers,
    _create_discovery_source,
    _ensure_data_dir,
)


class TestConstants:
    """Tests for module constants."""

    def test_gc_worker_interval(self):
        """GC worker interval should be reasonable."""
        assert GC_WORKER_INTERVAL_SECONDS > 0
        assert GC_WORKER_INTERVAL_SECONDS == 30

    def test_health_check_interval(self):
        """Health check interval should be reasonable."""
        assert HEALTH_CHECK_INTERVAL_SECONDS > 0
        assert HEALTH_CHECK_INTERVAL_SECONDS == 60


class TestApplicationContext:
    """Tests for ApplicationContext dataclass."""

    def test_application_context_creation(self):
        """ApplicationContext should be creatable with minimal args."""
        mock_runtime = MagicMock()
        mock_mcp = MagicMock()

        ctx = ApplicationContext(
            runtime=mock_runtime,
            mcp_server=mock_mcp,
        )

        assert ctx.runtime == mock_runtime
        assert ctx.mcp_server == mock_mcp
        assert ctx.background_workers == []
        assert ctx.discovery_orchestrator is None
        assert ctx.config == {}

    def test_application_context_with_workers(self):
        """ApplicationContext should accept background workers."""
        mock_runtime = MagicMock()
        mock_mcp = MagicMock()
        mock_worker = MagicMock()

        ctx = ApplicationContext(
            runtime=mock_runtime,
            mcp_server=mock_mcp,
            background_workers=[mock_worker],
        )

        assert len(ctx.background_workers) == 1
        assert ctx.background_workers[0] == mock_worker

    def test_application_context_shutdown(self):
        """ApplicationContext.shutdown() should stop all components."""
        mock_runtime = MagicMock()
        mock_mcp = MagicMock()
        mock_worker = MagicMock()
        mock_orchestrator = MagicMock()

        ctx = ApplicationContext(
            runtime=mock_runtime,
            mcp_server=mock_mcp,
            background_workers=[mock_worker],
            discovery_orchestrator=mock_orchestrator,
        )

        # Mock PROVIDERS to be empty
        with patch("mcp_hangar.server.bootstrap.PROVIDERS", {}):
            ctx.shutdown()

        mock_worker.stop.assert_called_once()

    def test_application_context_shutdown_handles_worker_errors(self):
        """ApplicationContext.shutdown() should handle worker errors gracefully."""
        mock_runtime = MagicMock()
        mock_mcp = MagicMock()
        mock_worker = MagicMock()
        mock_worker.stop.side_effect = Exception("Worker error")
        mock_worker.task = "gc"

        ctx = ApplicationContext(
            runtime=mock_runtime,
            mcp_server=mock_mcp,
            background_workers=[mock_worker],
        )

        # Should not raise - errors are logged and ignored
        with patch("mcp_hangar.server.bootstrap.PROVIDERS", {}):
            ctx.shutdown()


class TestEnsureDataDir:
    """Tests for _ensure_data_dir function."""

    def test_creates_data_dir_when_missing(self, tmp_path, monkeypatch):
        """Should create data directory when it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        _ensure_data_dir()

        data_dir = tmp_path / "data"
        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_does_nothing_when_dir_exists(self, tmp_path, monkeypatch):
        """Should not fail when data directory already exists."""
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Should not raise
        _ensure_data_dir()

        assert data_dir.exists()


class TestCreateBackgroundWorkers:
    """Tests for _create_background_workers function."""

    def test_creates_two_workers(self):
        """Should create GC and health check workers."""
        with patch("mcp_hangar.server.bootstrap.BackgroundWorker") as MockWorker:
            with patch("mcp_hangar.server.bootstrap.PROVIDERS", {}):
                workers = _create_background_workers()

        assert MockWorker.call_count == 2
        assert len(workers) == 2

    def test_workers_not_started(self):
        """Workers should be created but not started."""
        with patch("mcp_hangar.server.bootstrap.BackgroundWorker") as MockWorker:
            mock_worker = MagicMock()
            MockWorker.return_value = mock_worker

            with patch("mcp_hangar.server.bootstrap.PROVIDERS", {}):
                workers = _create_background_workers()

        # Workers should not have start() called
        mock_worker.start.assert_not_called()

    def test_gc_worker_interval(self):
        """GC worker should use correct interval."""
        with patch("mcp_hangar.server.bootstrap.BackgroundWorker") as MockWorker:
            with patch("mcp_hangar.server.bootstrap.PROVIDERS", {}):
                _create_background_workers()

        # Find the GC worker call
        gc_call = None
        for call in MockWorker.call_args_list:
            if call.kwargs.get("task") == "gc":
                gc_call = call
                break

        assert gc_call is not None
        assert gc_call.kwargs["interval_s"] == GC_WORKER_INTERVAL_SECONDS

    def test_health_worker_interval(self):
        """Health worker should use correct interval."""
        with patch("mcp_hangar.server.bootstrap.BackgroundWorker") as MockWorker:
            with patch("mcp_hangar.server.bootstrap.PROVIDERS", {}):
                _create_background_workers()

        # Find the health worker call
        health_call = None
        for call in MockWorker.call_args_list:
            if call.kwargs.get("task") == "health_check":
                health_call = call
                break

        assert health_call is not None
        assert health_call.kwargs["interval_s"] == HEALTH_CHECK_INTERVAL_SECONDS


class TestAutoAddVolumes:
    """Tests for _auto_add_volumes function."""

    def test_memory_provider_gets_volume(self, tmp_path, monkeypatch):
        """Memory providers should get auto-added volume."""
        monkeypatch.chdir(tmp_path)

        volumes = _auto_add_volumes("memory-provider")

        assert len(volumes) == 1
        assert "memory" in volumes[0]
        assert "/app/data:rw" in volumes[0]

    def test_filesystem_provider_gets_volume(self, tmp_path, monkeypatch):
        """Filesystem providers should get auto-added volume."""
        monkeypatch.chdir(tmp_path)

        volumes = _auto_add_volumes("filesystem-provider")

        assert len(volumes) == 1
        assert "filesystem" in volumes[0]
        assert "/data:rw" in volumes[0]

    def test_other_provider_no_volume(self, tmp_path, monkeypatch):
        """Other providers should not get auto-added volumes."""
        monkeypatch.chdir(tmp_path)

        volumes = _auto_add_volumes("math-provider")

        assert len(volumes) == 0

    def test_case_insensitive_matching(self, tmp_path, monkeypatch):
        """Volume matching should be case-insensitive."""
        monkeypatch.chdir(tmp_path)

        volumes = _auto_add_volumes("MEMORY-PROVIDER")

        assert len(volumes) == 1


class TestCreateDiscoverySource:
    """Tests for _create_discovery_source function."""

    def test_docker_source(self):
        """Should create Docker discovery source."""
        with patch("mcp_hangar.infrastructure.discovery.DockerDiscoverySource") as MockSource:
            source = _create_discovery_source("docker", {"mode": "additive"})

        MockSource.assert_called_once()
        assert source == MockSource.return_value

    def test_filesystem_source(self, tmp_path):
        """Should create filesystem discovery source."""
        with patch("mcp_hangar.infrastructure.discovery.FilesystemDiscoverySource") as MockSource:
            config = {
                "mode": "additive",
                "path": str(tmp_path),
                "pattern": "*.yaml",
            }
            source = _create_discovery_source("filesystem", config)

        MockSource.assert_called_once()
        assert source == MockSource.return_value

    def test_entrypoint_source(self):
        """Should create entrypoint discovery source."""
        with patch("mcp_hangar.infrastructure.discovery.EntrypointDiscoverySource") as MockSource:
            source = _create_discovery_source("entrypoint", {"mode": "additive"})

        MockSource.assert_called_once()
        assert source == MockSource.return_value

    def test_unknown_source_returns_none(self):
        """Unknown source type should return None."""
        source = _create_discovery_source("unknown", {"mode": "additive"})

        assert source is None

    def test_authoritative_mode(self):
        """Should handle authoritative mode correctly."""
        with patch("mcp_hangar.infrastructure.discovery.DockerDiscoverySource") as MockSource:
            _create_discovery_source("docker", {"mode": "authoritative"})

        # Check that mode was passed correctly
        call_kwargs = MockSource.call_args.kwargs
        from mcp_hangar.domain.discovery import DiscoveryMode
        assert call_kwargs["mode"] == DiscoveryMode.AUTHORITATIVE


class TestBootstrap:
    """Tests for bootstrap function."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for bootstrap."""
        with patch("mcp_hangar.server.bootstrap._ensure_data_dir") as mock_data_dir, \
             patch("mcp_hangar.server.bootstrap.get_runtime") as mock_get_runtime, \
             patch("mcp_hangar.server.bootstrap.init_context") as mock_init_context, \
             patch("mcp_hangar.server.bootstrap._init_event_handlers") as mock_init_eh, \
             patch("mcp_hangar.server.bootstrap._init_cqrs") as mock_init_cqrs, \
             patch("mcp_hangar.server.bootstrap._init_saga") as mock_init_saga, \
             patch("mcp_hangar.server.bootstrap.load_configuration") as mock_load_config, \
             patch("mcp_hangar.server.bootstrap._init_retry_config") as mock_init_retry, \
             patch("mcp_hangar.server.bootstrap._init_knowledge_base") as mock_init_kb, \
             patch("mcp_hangar.server.bootstrap.FastMCP") as mock_fastmcp, \
             patch("mcp_hangar.server.bootstrap._register_all_tools") as mock_reg_tools, \
             patch("mcp_hangar.server.bootstrap._create_background_workers") as mock_create_workers, \
             patch("mcp_hangar.server.bootstrap.PROVIDERS", MagicMock(keys=lambda: [])), \
             patch("mcp_hangar.server.bootstrap.GROUPS", {}):

            mock_runtime = MagicMock()
            mock_runtime.rate_limit_config.requests_per_second = 10
            mock_runtime.rate_limit_config.burst_size = 100
            mock_get_runtime.return_value = mock_runtime

            mock_load_config.return_value = {"discovery": {"enabled": False}}
            mock_create_workers.return_value = []

            yield {
                "data_dir": mock_data_dir,
                "get_runtime": mock_get_runtime,
                "init_context": mock_init_context,
                "init_eh": mock_init_eh,
                "init_cqrs": mock_init_cqrs,
                "init_saga": mock_init_saga,
                "load_config": mock_load_config,
                "init_retry": mock_init_retry,
                "init_kb": mock_init_kb,
                "fastmcp": mock_fastmcp,
                "reg_tools": mock_reg_tools,
                "create_workers": mock_create_workers,
            }

    def test_bootstrap_returns_application_context(self, mock_dependencies):
        """Bootstrap should return ApplicationContext."""
        ctx = bootstrap()

        assert isinstance(ctx, ApplicationContext)

    def test_bootstrap_calls_init_sequence(self, mock_dependencies):
        """Bootstrap should call init functions in order."""
        bootstrap()

        mock_dependencies["data_dir"].assert_called_once()
        mock_dependencies["get_runtime"].assert_called_once()
        mock_dependencies["init_context"].assert_called_once()
        mock_dependencies["init_eh"].assert_called_once()
        mock_dependencies["init_cqrs"].assert_called_once()
        mock_dependencies["init_saga"].assert_called_once()

    def test_bootstrap_with_config_path(self, mock_dependencies):
        """Bootstrap should pass config path to load_configuration."""
        bootstrap(config_path="/path/to/config.yaml")

        mock_dependencies["load_config"].assert_called_once_with("/path/to/config.yaml")

    def test_bootstrap_with_discovery_disabled(self, mock_dependencies):
        """Bootstrap without discovery should have None orchestrator."""
        ctx = bootstrap()

        assert ctx.discovery_orchestrator is None

    def test_bootstrap_creates_mcp_server(self, mock_dependencies):
        """Bootstrap should create FastMCP server."""
        bootstrap()

        mock_dependencies["fastmcp"].assert_called_once_with("mcp-registry")

    def test_bootstrap_registers_tools(self, mock_dependencies):
        """Bootstrap should register all MCP tools."""
        bootstrap()

        mock_dependencies["reg_tools"].assert_called_once()

    def test_bootstrap_creates_workers(self, mock_dependencies):
        """Bootstrap should create background workers."""
        bootstrap()

        mock_dependencies["create_workers"].assert_called_once()

