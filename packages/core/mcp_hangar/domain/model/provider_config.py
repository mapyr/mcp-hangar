"""Provider configuration dataclass.

Replaces the 21-parameter Provider.__init__() with a structured configuration object.
This follows the Builder pattern and improves code clarity.
"""

from dataclasses import dataclass, field
from typing import Any

from ..value_objects import HealthCheckInterval, IdleTTL, ProviderMode


@dataclass
class SubprocessConfig:
    """Configuration for subprocess mode providers."""

    command: list[str]
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class ContainerResourceConfig:
    """Resource limits for container providers."""

    memory: str = "512m"
    cpu: str = "1.0"


@dataclass
class ContainerConfig:
    """Configuration for container (Docker/Podman) mode providers."""

    image: str
    volumes: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    build: dict[str, str] | None = None
    resources: ContainerResourceConfig = field(default_factory=ContainerResourceConfig)
    network: str = "none"
    read_only: bool = True
    user: str | None = None


@dataclass
class RemoteConfig:
    """Configuration for remote (HTTP) mode providers."""

    endpoint: str
    auth: dict[str, Any] | None = None
    tls: dict[str, Any] | None = None
    http: dict[str, Any] | None = None


@dataclass
class HealthConfig:
    """Health check configuration."""

    check_interval: HealthCheckInterval = field(default_factory=lambda: HealthCheckInterval(60))
    max_consecutive_failures: int = 3


@dataclass
class ProviderConfig:
    """Complete provider configuration.

    Groups all provider parameters into logical sections:
    - Core: provider_id, mode, description
    - Mode-specific: subprocess, container, or remote config
    - Runtime: idle_ttl, health settings
    - Tools: pre-defined tool schemas

    Example:
        config = ProviderConfig(
            provider_id="math",
            mode=ProviderMode.SUBPROCESS,
            subprocess=SubprocessConfig(command=["python", "-m", "math_server"]),
        )
        provider = Provider(config)
    """

    # Core identity
    provider_id: str
    mode: ProviderMode | str
    description: str | None = None

    # Mode-specific configuration (only one should be set)
    subprocess: SubprocessConfig | None = None
    container: ContainerConfig | None = None
    remote: RemoteConfig | None = None

    # Runtime configuration
    idle_ttl: IdleTTL = field(default_factory=lambda: IdleTTL(300))
    health: HealthConfig = field(default_factory=HealthConfig)

    # Pre-defined tools (allows visibility before provider starts)
    tools: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize mode to ProviderMode enum."""
        if isinstance(self.mode, str):
            self.mode = ProviderMode.normalize(self.mode)

    @classmethod
    def from_dict(cls, provider_id: str, data: dict[str, Any]) -> "ProviderConfig":
        """Create ProviderConfig from a configuration dictionary.

        Args:
            provider_id: The provider identifier.
            data: Configuration dictionary (as from YAML config).

        Returns:
            ProviderConfig instance.
        """
        mode = ProviderMode.normalize(data.get("mode", "subprocess"))

        # Parse mode-specific config
        subprocess_config = None
        container_config = None
        remote_config = None

        if mode == ProviderMode.SUBPROCESS:
            subprocess_config = SubprocessConfig(
                command=data.get("command", []),
                env=data.get("env", {}),
            )
        elif mode in (ProviderMode.DOCKER, ProviderMode.CONTAINER):
            resources = data.get("resources", {})
            container_config = ContainerConfig(
                image=data.get("image", ""),
                volumes=data.get("volumes", []),
                env=data.get("env", {}),
                build=data.get("build"),
                resources=ContainerResourceConfig(
                    memory=resources.get("memory", "512m"),
                    cpu=resources.get("cpu", "1.0"),
                ),
                network=data.get("network", data.get("network_mode", "none")),
                read_only=data.get("read_only", True),
                user=data.get("user"),
            )
        elif mode == ProviderMode.REMOTE:
            remote_config = RemoteConfig(
                endpoint=data.get("endpoint", data.get("url", "")),
                auth=data.get("auth"),
                tls=data.get("tls"),
                http=data.get("http"),
            )

        # Parse runtime config
        idle_ttl_s = data.get("idle_ttl_s", 300)
        idle_ttl = IdleTTL(idle_ttl_s) if isinstance(idle_ttl_s, int) else idle_ttl_s

        health_interval_s = data.get("health_check_interval_s", 60)
        health_interval = (
            HealthCheckInterval(health_interval_s) if isinstance(health_interval_s, int) else health_interval_s
        )

        return cls(
            provider_id=provider_id,
            mode=mode,
            description=data.get("description"),
            subprocess=subprocess_config,
            container=container_config,
            remote=remote_config,
            idle_ttl=idle_ttl,
            health=HealthConfig(
                check_interval=health_interval,
                max_consecutive_failures=data.get("max_consecutive_failures", 3),
            ),
            tools=data.get("tools", []),
        )

    def get_command(self) -> list[str] | None:
        """Get command for subprocess mode."""
        return self.subprocess.command if self.subprocess else None

    def get_image(self) -> str | None:
        """Get image for container mode."""
        return self.container.image if self.container else None

    def get_endpoint(self) -> str | None:
        """Get endpoint for remote mode."""
        return self.remote.endpoint if self.remote else None

    def get_env(self) -> dict[str, str]:
        """Get environment variables for any mode."""
        if self.subprocess:
            return self.subprocess.env
        if self.container:
            return self.container.env
        return {}
