"""
Domain Ports - AGV Fleet Commander
Arquitectura Hexagonal - Interfaces del dominio
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from domain.entities import AGV, Task, Route, FleetMetrics, Position


class AGVRepositoryPort(ABC):
    """Puerto para persistencia de AGVs"""

    @abstractmethod
    def get_all_agvs(self) -> List[AGV]:
        """Obtener todos los AGVs"""
        pass

    @abstractmethod
    def get_agv_by_id(self, agv_id: str) -> Optional[AGV]:
        """Obtener AGV por ID"""
        pass

    @abstractmethod
    def update_agv(self, agv: AGV) -> bool:
        """Actualizar AGV"""
        pass

    @abstractmethod
    def get_available_agvs(self) -> List[AGV]:
        """Obtener AGVs disponibles para tareas"""
        pass


class TaskRepositoryPort(ABC):
    """Puerto para persistencia de tareas"""

    @abstractmethod
    def get_all_tasks(self) -> List[Task]:
        """Obtener todas las tareas"""
        pass

    @abstractmethod
    def get_pending_tasks(self) -> List[Task]:
        """Obtener tareas pendientes"""
        pass

    @abstractmethod
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Obtener tarea por ID"""
        pass

    @abstractmethod
    def create_task(self, task: Task) -> bool:
        """Crear nueva tarea"""
        pass

    @abstractmethod
    def update_task(self, task: Task) -> bool:
        """Actualizar tarea"""
        pass


class RouteOptimizerPort(ABC):
    """Puerto para optimización de rutas con IA"""

    @abstractmethod
    def optimize_route(
        self, agv: AGV, task: Task, obstacles: List[Position] = None
    ) -> Route:
        """Optimizar ruta para AGV y tarea específica"""
        pass

    @abstractmethod
    def optimize_fleet_routes(
        self, agvs: List[AGV], tasks: List[Task]
    ) -> Dict[str, Route]:
        """Optimizar rutas para toda la flota"""
        pass

    @abstractmethod
    def predict_congestion(self, current_routes: List[Route]) -> Dict[str, float]:
        """Predecir congestión en diferentes zonas"""
        pass


class AIAnalyticsPort(ABC):
    """Puerto para análisis con IA"""

    @abstractmethod
    def analyze_fleet_performance(
        self, metrics: FleetMetrics, historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analizar rendimiento de la flota"""
        pass

    @abstractmethod
    def predict_maintenance_needs(self, agvs: List[AGV]) -> Dict[str, Dict[str, Any]]:
        """Predecir necesidades de mantenimiento"""
        pass

    @abstractmethod
    def recommend_task_assignment(
        self, available_agvs: List[AGV], pending_tasks: List[Task]
    ) -> Dict[str, str]:
        """Recomendar asignación de tareas"""
        pass

    @abstractmethod
    def generate_fleet_insights(
        self, fleet_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generar insights inteligentes de la flota"""
        pass


class NotificationPort(ABC):
    """Puerto para notificaciones del sistema"""

    @abstractmethod
    def send_alert(self, message: str, severity: str) -> bool:
        """Enviar alerta"""
        pass

    @abstractmethod
    def log_event(self, event: str, data: Dict[str, Any]) -> bool:
        """Registrar evento"""
        pass
