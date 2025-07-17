"""
Domain Services - AGV Fleet Commander
Arquitectura Hexagonal - Lógica de negocio pura
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from domain.entities import (
    AGV,
    Task,
    Route,
    FleetMetrics,
    Position,
    AGVStatus,
    TaskPriority,
)
from domain.ports import (
    AGVRepositoryPort,
    TaskRepositoryPort,
    RouteOptimizerPort,
    AIAnalyticsPort,
    NotificationPort,
)


class FleetOrchestrationService:
    """
    Servicio principal de orquestación de la flota
    Coordina AGVs, tareas y rutas de manera inteligente
    """

    def __init__(
        self,
        agv_repository: AGVRepositoryPort,
        task_repository: TaskRepositoryPort,
        route_optimizer: RouteOptimizerPort,
        ai_analytics: AIAnalyticsPort,
        notification_service: NotificationPort,
    ):
        self.agv_repository = agv_repository
        self.task_repository = task_repository
        self.route_optimizer = route_optimizer
        self.ai_analytics = ai_analytics
        self.notification_service = notification_service

    def get_fleet_overview(self) -> Dict[str, Any]:
        """Obtener vista general de la flota"""
        agvs = self.agv_repository.get_all_agvs()
        tasks = self.task_repository.get_all_tasks()
        pending_tasks = self.task_repository.get_pending_tasks()

        # Calcular métricas
        total_agvs = len(agvs)
        active_agvs = len(
            [
                agv
                for agv in agvs
                if agv.status in [AGVStatus.MOVING, AGVStatus.TRANSPORTING]
            ]
        )
        idle_agvs = len([agv for agv in agvs if agv.status == AGVStatus.IDLE])
        charging_agvs = len([agv for agv in agvs if agv.status == AGVStatus.CHARGING])

        avg_battery = sum(agv.battery_level for agv in agvs) / total_agvs if agvs else 0
        completed_tasks = len([task for task in tasks if task.is_completed()])

        metrics = FleetMetrics(
            total_agvs=total_agvs,
            active_agvs=active_agvs,
            idle_agvs=idle_agvs,
            charging_agvs=charging_agvs,
            pending_tasks=len(pending_tasks),
            completed_tasks=completed_tasks,
            average_battery=avg_battery,
            fleet_efficiency=0.0,  # Se calculará automáticamente
        )
        metrics.fleet_efficiency = metrics.calculate_efficiency()

        return {
            "fleet_metrics": metrics,
            "agvs": agvs,
            "pending_tasks": pending_tasks,
            "total_tasks": len(tasks),
        }

    def assign_optimal_tasks(self) -> Dict[str, Any]:
        """Asignar tareas de manera óptima usando IA"""
        available_agvs = self.agv_repository.get_available_agvs()
        pending_tasks = self.task_repository.get_pending_tasks()

        if not available_agvs or not pending_tasks:
            return {
                "assignments": [],
                "message": "No hay AGVs disponibles o tareas pendientes",
            }

        # Usar IA para recomendar asignaciones
        recommendations = self.ai_analytics.recommend_task_assignment(
            available_agvs, pending_tasks
        )

        assignments = []
        for agv_id, task_id in recommendations.items():
            agv = self.agv_repository.get_agv_by_id(agv_id)
            task = self.task_repository.get_task_by_id(task_id)

            if agv and task and agv.can_reach(task.destination):
                # Asignar tarea
                task.assigned_agv_id = agv_id
                task.started_at = datetime.now()
                agv.current_task_id = task_id
                agv.status = AGVStatus.MOVING

                # Generar ruta optimizada
                route = self.route_optimizer.optimize_route(agv, task)

                # Actualizar en repositorios
                self.task_repository.update_task(task)
                self.agv_repository.update_agv(agv)

                assignments.append(
                    {
                        "agv_id": agv_id,
                        "task_id": task_id,
                        "route": route,
                        "estimated_time": route.estimated_time,
                    }
                )

                # Notificar asignación
                self.notification_service.log_event(
                    "task_assigned",
                    {
                        "agv_id": agv_id,
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

        return {
            "assignments": assignments,
            "total_assigned": len(assignments),
            "message": f"Se asignaron {len(assignments)} tareas exitosamente",
        }

    def monitor_fleet_status(self) -> Dict[str, Any]:
        """Monitorear estado de la flota y detectar problemas"""
        agvs = self.agv_repository.get_all_agvs()
        alerts = []

        for agv in agvs:
            # Verificar batería baja
            if agv.battery_level < 20:
                alerts.append(
                    {
                        "type": "low_battery",
                        "agv_id": agv.agv_id,
                        "message": f"AGV {agv.name} tiene batería baja ({agv.battery_level}%)",
                        "severity": "high" if agv.battery_level < 10 else "medium",
                    }
                )

            # Verificar AGVs inactivos por mucho tiempo
            if agv.status == AGVStatus.IDLE and agv.last_update:
                time_diff = datetime.now() - agv.last_update
                if time_diff > timedelta(minutes=30):
                    alerts.append(
                        {
                            "type": "idle_too_long",
                            "agv_id": agv.agv_id,
                            "message": f"AGV {agv.name} inactivo por {time_diff.seconds // 60} minutos",
                            "severity": "low",
                        }
                    )

        # Usar IA para predecir necesidades de mantenimiento
        maintenance_predictions = self.ai_analytics.predict_maintenance_needs(agvs)

        for agv_id, prediction in maintenance_predictions.items():
            if prediction.get("needs_maintenance", False):
                alerts.append(
                    {
                        "type": "maintenance_needed",
                        "agv_id": agv_id,
                        "message": f"AGV requiere mantenimiento: {prediction.get('reason', 'Predicción IA')}",
                        "severity": "medium",
                    }
                )

        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "maintenance_predictions": maintenance_predictions,
        }

    def optimize_fleet_routes(self) -> Dict[str, Any]:
        """Optimizar rutas de toda la flota"""
        active_agvs = [
            agv
            for agv in self.agv_repository.get_all_agvs()
            if agv.status in [AGVStatus.MOVING, AGVStatus.TRANSPORTING]
        ]

        if not active_agvs:
            return {"message": "No hay AGVs activos para optimizar"}

        # Obtener tareas asignadas
        assigned_tasks = []
        for agv in active_agvs:
            if agv.current_task_id:
                task = self.task_repository.get_task_by_id(agv.current_task_id)
                if task:
                    assigned_tasks.append(task)

        # Optimizar rutas usando IA
        optimized_routes = self.route_optimizer.optimize_fleet_routes(
            active_agvs, assigned_tasks
        )

        # Predecir congestión
        congestion_zones = self.route_optimizer.predict_congestion(
            list(optimized_routes.values())
        )

        return {
            "optimized_routes": optimized_routes,
            "congestion_zones": congestion_zones,
            "total_routes": len(optimized_routes),
            "message": "Rutas optimizadas exitosamente",
        }

    def generate_ai_insights(self) -> List[Dict[str, Any]]:
        """Generar insights inteligentes sobre la flota"""
        fleet_data = self.get_fleet_overview()

        # Usar IA para generar insights
        insights = self.ai_analytics.generate_fleet_insights(
            {
                "metrics": fleet_data["fleet_metrics"].__dict__,
                "agvs_count": len(fleet_data["agvs"]),
                "pending_tasks": len(fleet_data["pending_tasks"]),
                "timestamp": datetime.now().isoformat(),
            }
        )

        return insights

    def create_emergency_task(
        self,
        description: str,
        origin: Position,
        destination: Position,
        container_id: str = None,
    ) -> Dict[str, Any]:
        """Crear tarea de emergencia con máxima prioridad"""
        task = Task(
            task_id=f"URGENT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description=f"🚨 URGENTE: {description}",
            origin=origin,
            destination=destination,
            priority=TaskPriority.URGENT,
            container_id=container_id,
        )

        # Crear la tarea
        if self.task_repository.create_task(task):
            # Intentar asignación inmediata
            assignment_result = self.assign_optimal_tasks()

            # Notificar emergencia
            self.notification_service.send_alert(
                f"Tarea de emergencia creada: {description}", "urgent"
            )

            return {
                "task": task,
                "assignment_result": assignment_result,
                "message": "Tarea de emergencia creada y procesada",
            }

        return {"error": "No se pudo crear la tarea de emergencia"}


class AGVControlService:
    """
    Servicio para control individual de AGVs
    """

    def __init__(
        self, agv_repository: AGVRepositoryPort, notification_service: NotificationPort
    ):
        self.agv_repository = agv_repository
        self.notification_service = notification_service

    def send_agv_to_position(self, agv_id: str, position: Position) -> Dict[str, Any]:
        """Enviar AGV a una posición específica"""
        agv = self.agv_repository.get_agv_by_id(agv_id)

        if not agv:
            return {"error": f"AGV {agv_id} no encontrado"}

        if not agv.is_available():
            return {"error": f"AGV {agv_id} no está disponible"}

        if not agv.can_reach(position):
            return {
                "error": f"AGV {agv_id} no puede alcanzar la posición (batería insuficiente)"
            }

        # Actualizar AGV
        agv.status = AGVStatus.MOVING
        agv.last_update = datetime.now()

        if self.agv_repository.update_agv(agv):
            self.notification_service.log_event(
                "manual_agv_move",
                {
                    "agv_id": agv_id,
                    "destination": position.__dict__,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return {
                "success": True,
                "message": f"AGV {agv.name} enviado a posición ({position.x}, {position.y})",
                "estimated_time": position.distance_to(agv.position)
                / 1000
                / 20
                * 60,  # minutos
            }

        return {"error": "No se pudo actualizar el AGV"}

    def emergency_stop_agv(self, agv_id: str) -> Dict[str, Any]:
        """Parada de emergencia de AGV"""
        agv = self.agv_repository.get_agv_by_id(agv_id)

        if not agv:
            return {"error": f"AGV {agv_id} no encontrado"}

        # Parar AGV
        agv.status = AGVStatus.IDLE
        agv.current_task_id = None
        agv.last_update = datetime.now()

        if self.agv_repository.update_agv(agv):
            self.notification_service.send_alert(
                f"PARADA DE EMERGENCIA: AGV {agv.name}", "urgent"
            )

            return {
                "success": True,
                "message": f"AGV {agv.name} detenido en emergencia",
            }

        return {"error": "No se pudo detener el AGV"}
