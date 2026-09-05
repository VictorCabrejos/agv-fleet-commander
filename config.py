"""Environment-backed configuration for the AGV fleet simulator."""

from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str | None = None
    model: str = "gpt-4o-mini"


@dataclass(frozen=True)
class SystemConfig:
    debug: bool = False
    log_level: str = "INFO"
    data_directory: str = "data"
    logs_directory: str = "logs"
    simulation_enabled: bool = True
    simulation_speed: float = 1.0


@dataclass(frozen=True)
class AGVConfig:
    max_battery_level: float = 100.0
    min_battery_level: float = 10.0
    charging_threshold: float = 20.0
    max_speed_kmh: float = 25.0
    max_range_km: float = 50.0
    charging_rate_per_minute: float = 2.5


@dataclass(frozen=True)
class FleetConfig:
    max_agvs: int = 20
    max_concurrent_tasks: int = 50
    task_timeout_minutes: int = 120
    route_optimization_enabled: bool = True
    ai_analytics_enabled: bool = True
    maintenance_prediction_enabled: bool = True


@dataclass(frozen=True)
class AppConfig:
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    agv: AGVConfig = field(default_factory=AGVConfig)
    fleet: FleetConfig = field(default_factory=FleetConfig)
    host: str = "127.0.0.1"
    port: int = 5001
    reload: bool = False
    secret_key: str | None = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            openai=OpenAIConfig(
                api_key=os.getenv("OPENAI_API_KEY") or None,
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            ),
            system=SystemConfig(
                debug=os.getenv("DEBUG", "false").lower() == "true",
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                data_directory=os.getenv("DATA_DIRECTORY", "data"),
                logs_directory=os.getenv("LOGS_DIRECTORY", "logs"),
                simulation_enabled=os.getenv("SIMULATION_ENABLED", "true").lower() == "true",
                simulation_speed=float(os.getenv("SIMULATION_SPEED", "1.0")),
            ),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "5001")),
            reload=os.getenv("RELOAD", "false").lower() == "true",
            secret_key=os.getenv("SECRET_KEY") or None,
        )

    def validate(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")
        if self.system.simulation_speed <= 0:
            raise ValueError("SIMULATION_SPEED must be positive")

    def get_summary(self) -> dict:
        return {
            "openai": {
                "model": self.openai.model,
                "api_key_configured": bool(self.openai.api_key),
            },
            "system": {
                "debug": self.system.debug,
                "log_level": self.system.log_level,
                "simulation_enabled": self.system.simulation_enabled,
                "simulation_speed": self.system.simulation_speed,
            },
            "api": {"host": self.host, "port": self.port, "reload": self.reload},
        }


config = AppConfig.from_env()
config.validate()
