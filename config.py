"""
Configuration - AGV Fleet Commander
Configuración del sistema AGV Fleet Commander
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenAIConfig:
    """Configuración de OpenAI"""

    api_key: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 2000


@dataclass
class SystemConfig:
    """Configuración del sistema"""

    debug: bool = False
    log_level: str = "INFO"
    data_directory: str = "data"
    logs_directory: str = "logs"
    simulation_enabled: bool = True
    simulation_speed: float = 1.0  # Multiplicador de velocidad de simulación


@dataclass
class AGVConfig:
    """Configuración de AGVs"""

    max_battery_level: float = 100.0
    min_battery_level: float = 10.0
    charging_threshold: float = 20.0
    max_speed_kmh: float = 25.0
    max_range_km: float = 50.0
    charging_rate_per_minute: float = 2.5


@dataclass
class FleetConfig:
    """Configuración de la flota"""

    max_agvs: int = 20
    max_concurrent_tasks: int = 50
    task_timeout_minutes: int = 120
    route_optimization_enabled: bool = True
    ai_analytics_enabled: bool = True
    maintenance_prediction_enabled: bool = True


@dataclass
class AppConfig:
    """Configuración principal de la aplicación"""

    # OpenAI
    openai: OpenAIConfig

    # Sistema
    system: SystemConfig

    # AGV
    agv: AGVConfig

    # Flota
    fleet: FleetConfig

    # API
    host: str = "localhost"
    port: int = 5001
    reload: bool = True

    # Seguridad
    secret_key: str = "agv-fleet-commander-secret-key-2025"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Crear configuración desde variables de entorno"""
        # OpenAI Config
        openai_config = OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
        )

        # System Config
        system_config = SystemConfig(
            debug=os.getenv("DEBUG", "False").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            data_directory=os.getenv("DATA_DIRECTORY", "data"),
            logs_directory=os.getenv("LOGS_DIRECTORY", "logs"),
            simulation_enabled=os.getenv("SIMULATION_ENABLED", "True").lower()
            == "true",
            simulation_speed=float(os.getenv("SIMULATION_SPEED", "1.0")),
        )

        # AGV Config
        agv_config = AGVConfig(
            max_battery_level=float(os.getenv("AGV_MAX_BATTERY", "100.0")),
            min_battery_level=float(os.getenv("AGV_MIN_BATTERY", "10.0")),
            charging_threshold=float(os.getenv("AGV_CHARGING_THRESHOLD", "20.0")),
            max_speed_kmh=float(os.getenv("AGV_MAX_SPEED", "25.0")),
            max_range_km=float(os.getenv("AGV_MAX_RANGE", "50.0")),
            charging_rate_per_minute=float(os.getenv("AGV_CHARGING_RATE", "2.5")),
        )

        # Fleet Config
        fleet_config = FleetConfig(
            max_agvs=int(os.getenv("FLEET_MAX_AGVS", "20")),
            max_concurrent_tasks=int(os.getenv("FLEET_MAX_TASKS", "50")),
            task_timeout_minutes=int(os.getenv("TASK_TIMEOUT", "120")),
            route_optimization_enabled=os.getenv("ROUTE_OPTIMIZATION", "True").lower()
            == "true",
            ai_analytics_enabled=os.getenv("AI_ANALYTICS", "True").lower() == "true",
            maintenance_prediction_enabled=os.getenv(
                "MAINTENANCE_PREDICTION", "True"
            ).lower()
            == "true",
        )

        return cls(
            openai=openai_config,
            system=system_config,
            agv=agv_config,
            fleet=fleet_config,
            host=os.getenv("HOST", "localhost"),
            port=int(os.getenv("PORT", "5001")),
            reload=os.getenv("RELOAD", "True").lower() == "true",
            secret_key=os.getenv("SECRET_KEY", "agv-fleet-commander-secret-key-2025"),
        )

    def validate(self) -> bool:
        """Validar configuración"""
        errors = []

        # Validar OpenAI API Key
        if not self.openai.api_key:
            errors.append("OPENAI_API_KEY es requerido")

        # Validar rangos
        if not (0 <= self.openai.temperature <= 2):
            errors.append("OPENAI_TEMPERATURE debe estar entre 0 y 2")

        if not (1 <= self.openai.max_tokens <= 4000):
            errors.append("OPENAI_MAX_TOKENS debe estar entre 1 y 4000")

        if not (1 <= self.port <= 65535):
            errors.append("PORT debe estar entre 1 y 65535")

        if not (0 < self.agv.max_speed_kmh <= 50):
            errors.append("AGV_MAX_SPEED debe estar entre 0 y 50 km/h")

        if not (0 < self.agv.max_range_km <= 100):
            errors.append("AGV_MAX_RANGE debe estar entre 0 y 100 km")

        if errors:
            print("❌ Errores de configuración:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    def get_summary(self) -> dict:
        """Obtener resumen de configuración (sin claves sensibles)"""
        return {
            "openai": {
                "model": self.openai.model,
                "temperature": self.openai.temperature,
                "max_tokens": self.openai.max_tokens,
                "api_key_configured": bool(self.openai.api_key),
            },
            "system": {
                "debug": self.system.debug,
                "log_level": self.system.log_level,
                "simulation_enabled": self.system.simulation_enabled,
                "simulation_speed": self.system.simulation_speed,
            },
            "agv": {
                "max_battery": self.agv.max_battery_level,
                "charging_threshold": self.agv.charging_threshold,
                "max_speed_kmh": self.agv.max_speed_kmh,
                "max_range_km": self.agv.max_range_km,
            },
            "fleet": {
                "max_agvs": self.fleet.max_agvs,
                "max_concurrent_tasks": self.fleet.max_concurrent_tasks,
                "ai_features_enabled": {
                    "route_optimization": self.fleet.route_optimization_enabled,
                    "analytics": self.fleet.ai_analytics_enabled,
                    "maintenance_prediction": self.fleet.maintenance_prediction_enabled,
                },
            },
            "api": {"host": self.host, "port": self.port, "reload": self.reload},
        }


# Configuración por defecto
DEFAULT_CONFIG = AppConfig(
    openai=OpenAIConfig(
        api_key="",  # Debe ser configurada
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=2000,
    ),
    system=SystemConfig(
        debug=True,
        log_level="INFO",
        data_directory="data",
        logs_directory="logs",
        simulation_enabled=True,
        simulation_speed=1.0,
    ),
    agv=AGVConfig(
        max_battery_level=100.0,
        min_battery_level=10.0,
        charging_threshold=20.0,
        max_speed_kmh=25.0,
        max_range_km=50.0,
        charging_rate_per_minute=2.5,
    ),
    fleet=FleetConfig(
        max_agvs=20,
        max_concurrent_tasks=50,
        task_timeout_minutes=120,
        route_optimization_enabled=True,
        ai_analytics_enabled=True,
        maintenance_prediction_enabled=True,
    ),
    host="localhost",
    port=5001,
    reload=True,
)


def get_config() -> AppConfig:
    """Obtener configuración de la aplicación"""
    config = AppConfig.from_env()

    if not config.validate():
        print("⚠️ Usando configuración por defecto debido a errores")
        config = DEFAULT_CONFIG

        # Intentar obtener al menos la API key del entorno
        env_api_key = os.getenv("OPENAI_API_KEY")
        if env_api_key:
            config.openai.api_key = env_api_key

    return config


# Instancia global de configuración
config = get_config()
