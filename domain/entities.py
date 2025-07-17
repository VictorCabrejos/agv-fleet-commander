"""
Domain Entities - AGV Fleet Commander
Arquitectura Hexagonal - Puerto de Chancay
"""

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime
from enum import Enum


class AGVStatus(Enum):
    """Estados posibles de un AGV"""

    IDLE = "IDLE"
    MOVING = "MOVING"
    TRANSPORTING = "TRANSPORTING"
    CHARGING = "CHARGING"
    MAINTENANCE = "MAINTENANCE"


class TaskPriority(Enum):
    """Prioridades de las tareas"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


@dataclass
class Position:
    """Posición en el mapa del puerto"""

    x: float
    y: float
    zone: str = ""

    def distance_to(self, other: "Position") -> float:
        """Calcular distancia euclidiana a otra posición"""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass
class AGV:
    """
    Entidad AGV - Vehículo Autónomo Guiado
    Núcleo del dominio sin dependencias externas
    """

    agv_id: str
    name: str
    position: Position
    battery_level: int  # 0-100
    status: AGVStatus
    current_task_id: Optional[str] = None
    max_speed: float = 20.0  # km/h
    load_capacity: float = 2000.0  # kg
    last_update: datetime = None

    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()

    def is_available(self) -> bool:
        """Verificar si el AGV está disponible para nueva tarea"""
        return (
            self.status == AGVStatus.IDLE
            and self.battery_level > 20
            and self.current_task_id is None
        )

    def needs_charging(self) -> bool:
        """Verificar si necesita carga"""
        return self.battery_level < 30

    def can_reach(self, destination: Position) -> bool:
        """Verificar si puede alcanzar el destino con la batería actual"""
        distance = self.position.distance_to(destination)
        # Estimación: 1% batería por cada 100 metros
        battery_needed = (distance / 100) * 1
        return self.battery_level >= battery_needed + 10  # 10% de margen


@dataclass
class Task:
    """
    Entidad Task - Tarea de transporte
    Define qué debe hacer cada AGV
    """

    task_id: str
    description: str
    origin: Position
    destination: Position
    priority: TaskPriority
    container_id: Optional[str] = None
    assigned_agv_id: Optional[str] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration: float = 0.0  # minutos

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

        # Calcular duración estimada basada en distancia
        if self.estimated_duration == 0.0:
            distance = self.origin.distance_to(self.destination)
            # Estimación: 20 km/h promedio + tiempo de carga/descarga
            travel_time = (distance / 1000) / 20 * 60  # minutos
            self.estimated_duration = travel_time + 5  # 5 min para carga/descarga

    def is_completed(self) -> bool:
        """Verificar si la tarea está completada"""
        return self.completed_at is not None

    def is_in_progress(self) -> bool:
        """Verificar si la tarea está en progreso"""
        return (
            self.started_at is not None
            and self.completed_at is None
            and self.assigned_agv_id is not None
        )

    def get_progress_percentage(self) -> float:
        """Obtener porcentaje de progreso (simulado)"""
        if not self.is_in_progress():
            return 0.0 if not self.is_completed() else 100.0

        # Simulación de progreso basada en tiempo transcurrido
        elapsed = (datetime.now() - self.started_at).total_seconds() / 60
        return min(100.0, (elapsed / self.estimated_duration) * 100)


@dataclass
class Route:
    """
    Entidad Route - Ruta optimizada para AGV
    Define el camino más eficiente
    """

    route_id: str
    agv_id: str
    task_id: str
    waypoints: list[Position]
    total_distance: float
    estimated_time: float  # minutos
    fuel_consumption: float  # % batería
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_waypoint(self, position: Position):
        """Agregar punto de ruta"""
        self.waypoints.append(position)
        self._recalculate_metrics()

    def _recalculate_metrics(self):
        """Recalcular métricas de la ruta"""
        if len(self.waypoints) < 2:
            return

        total_dist = 0.0
        for i in range(len(self.waypoints) - 1):
            total_dist += self.waypoints[i].distance_to(self.waypoints[i + 1])

        self.total_distance = total_dist
        self.estimated_time = (total_dist / 1000) / 20 * 60  # 20 km/h promedio
        self.fuel_consumption = (total_dist / 100) * 1  # 1% por cada 100m


@dataclass
class FleetMetrics:
    """
    Entidad FleetMetrics - Métricas de la flota
    Información de rendimiento del sistema
    """

    total_agvs: int
    active_agvs: int
    idle_agvs: int
    charging_agvs: int
    pending_tasks: int
    completed_tasks: int
    average_battery: float
    fleet_efficiency: float  # 0-100
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def calculate_efficiency(self) -> float:
        """Calcular eficiencia de la flota"""
        if self.total_agvs == 0:
            return 0.0

        # Eficiencia basada en AGVs activos y nivel de batería
        active_ratio = self.active_agvs / self.total_agvs
        battery_ratio = self.average_battery / 100

        return (active_ratio * 0.7 + battery_ratio * 0.3) * 100
