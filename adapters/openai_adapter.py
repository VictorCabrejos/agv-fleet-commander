"""
OpenAI Adapter - AGV Fleet Commander
Adaptador para integración con OpenAI GPT-4o mini
"""

import openai
import json
import math
from typing import List, Dict, Any, Optional
from datetime import datetime
import random

from domain.entities import AGV, Task, Route, Position, AGVStatus, TaskPriority
from domain.ports import RouteOptimizerPort, AIAnalyticsPort


class OpenAIRouteOptimizer(RouteOptimizerPort):
    """
    Optimizador de rutas usando OpenAI GPT-4o mini
    """

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def optimize_route(self, agv: AGV, task: Task) -> Route:
        """Optimizar ruta individual para un AGV y tarea"""
        try:
            # Preparar prompt para OpenAI
            prompt = f"""
            Como experto en optimización logística del Puerto de Chancay, necesito optimizar una ruta para un AGV.

            AGV Información:
            - ID: {agv.agv_id}
            - Posición actual: ({agv.position.x}, {agv.position.y})
            - Nivel de batería: {agv.battery_level}%
            - Estado: {agv.status.value}

            Tarea:
            - ID: {task.task_id}
            - Origen: ({task.origin.x}, {task.origin.y})
            - Destino: ({task.destination.x}, {task.destination.y})
            - Prioridad: {task.priority.value}
            - Contenedor: {task.container_id}

            Considera:
            1. Eficiencia energética (batería)
            2. Evitar zonas de congestión típicas
            3. Prioridad de la tarea
            4. Tiempo de trayecto

            Proporciona una ruta optimizada con waypoints intermedios en formato JSON:
            {{
                "waypoints": [
                    {{"x": float, "y": float, "description": "string"}},
                    ...
                ],
                "estimated_time": float,
                "total_distance": float,
                "energy_consumption": float,
                "optimization_notes": "string"
            }}
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en optimización logística portuaria con deep learning en AGVs.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            # Parsear respuesta
            route_data = json.loads(response.choices[0].message.content)

            # Crear objetos Position para waypoints
            waypoints = []
            for wp in route_data["waypoints"]:
                waypoints.append(Position(wp["x"], wp["y"]))

            return Route(
                route_id=f"ROUTE_{agv.agv_id}_{task.task_id}_{datetime.now().strftime('%H%M%S')}",
                agv_id=agv.agv_id,
                task_id=task.task_id,
                waypoints=waypoints,
                estimated_time=route_data["estimated_time"],
                total_distance=route_data["total_distance"],
                created_at=datetime.now(),
            )

        except Exception as e:
            print(f"Error en optimización OpenAI: {e}")
            # Fallback: ruta directa simple
            return self._create_fallback_route(agv, task)

    def optimize_fleet_routes(
        self, agvs: List[AGV], tasks: List[Task]
    ) -> Dict[str, Route]:
        """Optimizar rutas para toda la flota"""
        try:
            # Preparar datos para OpenAI
            agv_data = []
            for agv in agvs:
                agv_data.append(
                    {
                        "id": agv.agv_id,
                        "position": {"x": agv.position.x, "y": agv.position.y},
                        "battery": agv.battery_level,
                        "status": agv.status.value,
                    }
                )

            task_data = []
            for task in tasks:
                task_data.append(
                    {
                        "id": task.task_id,
                        "origin": {"x": task.origin.x, "y": task.origin.y},
                        "destination": {
                            "x": task.destination.x,
                            "y": task.destination.y,
                        },
                        "priority": task.priority.value,
                        "agv_id": task.assigned_agv_id,
                    }
                )

            prompt = f"""
            Como experto en optimización logística del Puerto de Chancay, optimiza las rutas de una flota de AGVs.

            AGVs: {json.dumps(agv_data, indent=2)}
            Tareas: {json.dumps(task_data, indent=2)}

            Considera:
            1. Evitar colisiones entre AGVs
            2. Minimizar tiempo total de operación
            3. Optimizar consumo energético
            4. Respetar prioridades de tareas
            5. Evitar congestión en intersecciones

            Proporciona rutas optimizadas en formato JSON:
            {{
                "agv_id": {{
                    "waypoints": [{{"x": float, "y": float}}],
                    "estimated_time": float,
                    "total_distance": float,
                    "notes": "string"
                }},
                ...
            }}
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en optimización de flotas AGV con algoritmos avanzados.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            routes_data = json.loads(response.choices[0].message.content)

            # Crear objetos Route
            optimized_routes = {}
            for agv_id, route_info in routes_data.items():
                agv = next((a for a in agvs if a.agv_id == agv_id), None)
                task = next((t for t in tasks if t.assigned_agv_id == agv_id), None)

                if agv and task:
                    waypoints = [
                        Position(wp["x"], wp["y"]) for wp in route_info["waypoints"]
                    ]

                    route = Route(
                        route_id=f"FLEET_ROUTE_{agv_id}_{datetime.now().strftime('%H%M%S')}",
                        agv_id=agv_id,
                        task_id=task.task_id,
                        waypoints=waypoints,
                        estimated_time=route_info["estimated_time"],
                        total_distance=route_info["total_distance"],
                        created_at=datetime.now(),
                    )
                    optimized_routes[agv_id] = route

            return optimized_routes

        except Exception as e:
            print(f"Error en optimización de flota OpenAI: {e}")
            # Fallback: rutas individuales
            routes = {}
            for agv in agvs:
                task = next((t for t in tasks if t.assigned_agv_id == agv.agv_id), None)
                if task:
                    routes[agv.agv_id] = self._create_fallback_route(agv, task)
            return routes

    def predict_congestion(self, routes: List[Route]) -> List[Dict[str, Any]]:
        """Predecir zonas de congestión"""
        try:
            # Analizar waypoints comunes
            waypoint_density = {}
            for route in routes:
                for wp in route.waypoints:
                    # Agrupar por grillas de 50x50
                    grid_x = int(wp.x // 50) * 50
                    grid_y = int(wp.y // 50) * 50
                    key = f"{grid_x},{grid_y}"
                    waypoint_density[key] = waypoint_density.get(key, 0) + 1

            # Usar OpenAI para análisis avanzado
            prompt = f"""
            Como experto en análisis de tráfico portuario, analiza estos datos de densidad de waypoints:
            {json.dumps(waypoint_density, indent=2)}

            Predice zonas de congestión considerando:
            1. Densidad de tráfico AGV
            2. Puntos de intersección críticos
            3. Cuellos de botella típicos en puertos
            4. Horarios de mayor actividad

            Formato JSON:
            [
                {{
                    "zone": "string",
                    "coordinates": {{"x": float, "y": float}},
                    "congestion_level": "LOW|MEDIUM|HIGH|CRITICAL",
                    "estimated_delay": float,
                    "recommendation": "string"
                }}
            ]
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en análisis de tráfico y congestión portuaria.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"Error en predicción de congestión: {e}")
            # Fallback: análisis simple
            congestion_zones = []
            for zone, count in waypoint_density.items():
                if count > 2:
                    x, y = map(float, zone.split(","))
                    congestion_zones.append(
                        {
                            "zone": f"Grid_{zone}",
                            "coordinates": {"x": x, "y": y},
                            "congestion_level": "HIGH" if count > 4 else "MEDIUM",
                            "estimated_delay": count * 2.5,
                            "recommendation": f"Evitar zona con {count} AGVs",
                        }
                    )
            return congestion_zones

    def _create_fallback_route(self, agv: AGV, task: Task) -> Route:
        """Crear ruta fallback simple"""
        # Ruta directa con algunos waypoints intermedios
        waypoints = [
            agv.position,  # Posición actual
            task.origin,  # Origen de la tarea
            task.destination,  # Destino final
        ]

        total_distance = agv.position.distance_to(
            task.origin
        ) + task.origin.distance_to(task.destination)
        estimated_time = total_distance / 1000 / 20 * 60  # 20 km/h promedio, en minutos

        return Route(
            route_id=f"FALLBACK_{agv.agv_id}_{task.task_id}_{datetime.now().strftime('%H%M%S')}",
            agv_id=agv.agv_id,
            task_id=task.task_id,
            waypoints=waypoints,
            estimated_time=estimated_time,
            total_distance=total_distance,
            created_at=datetime.now(),
        )


class OpenAIAnalytics(AIAnalyticsPort):
    """
    Servicio de análisis e insights usando OpenAI GPT-4o mini
    """

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def analyze_fleet_performance(
        self, metrics, historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analizar rendimiento de la flota"""
        try:
            prompt = f"""
            Como experto en análisis de rendimiento de flotas AGV del Puerto de Chancay, analiza estos datos:

            Métricas actuales:
            - Total AGVs: {metrics.total_agvs}
            - AGVs activos: {metrics.active_agvs}
            - AGVs en espera: {metrics.idle_agvs}
            - AGVs cargando: {metrics.charging_agvs}
            - Tareas pendientes: {metrics.pending_tasks}
            - Tareas completadas: {metrics.completed_tasks}
            - Batería promedio: {metrics.average_battery}%
            - Eficiencia de flota: {metrics.fleet_efficiency * 100:.1f}%

            Datos históricos: {json.dumps(historical_data, indent=2) if historical_data else "No disponibles"}

            Proporciona un análisis completo en formato JSON:
            {{
                "overall_performance": {{
                    "score": float,
                    "category": "EXCELLENT|GOOD|AVERAGE|POOR|CRITICAL",
                    "summary": "string"
                }},
                "key_metrics": {{
                    "efficiency_trend": "IMPROVING|STABLE|DECLINING",
                    "utilization_rate": float,
                    "battery_management": "OPTIMAL|GOOD|NEEDS_IMPROVEMENT",
                    "task_completion_rate": float
                }},
                "recommendations": [
                    {{
                        "priority": "HIGH|MEDIUM|LOW",
                        "action": "string",
                        "expected_impact": "string"
                    }}
                ],
                "risk_factors": [
                    {{
                        "factor": "string",
                        "probability": float,
                        "impact": "HIGH|MEDIUM|LOW"
                    }}
                ]
            }}
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en análisis de rendimiento de flotas industriales y optimización operacional.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"Error en análisis de rendimiento: {e}")
            # Fallback: análisis básico
            return {
                "overall_performance": {
                    "score": metrics.fleet_efficiency,
                    "category": "GOOD" if metrics.fleet_efficiency > 0.7 else "AVERAGE",
                    "summary": f"Flota operando con {metrics.fleet_efficiency * 100:.1f}% de eficiencia",
                },
                "key_metrics": {
                    "efficiency_trend": "STABLE",
                    "utilization_rate": (
                        metrics.active_agvs / metrics.total_agvs
                        if metrics.total_agvs > 0
                        else 0
                    ),
                    "battery_management": (
                        "GOOD" if metrics.average_battery > 50 else "NEEDS_IMPROVEMENT"
                    ),
                    "task_completion_rate": 0.85,
                },
                "recommendations": [
                    {
                        "priority": "MEDIUM",
                        "action": "Optimizar ciclos de carga",
                        "expected_impact": "Mejora del 10-15% en disponibilidad",
                    }
                ],
                "risk_factors": [],
            }

    def recommend_task_assignment(
        self, agvs: List[AGV], tasks: List[Task]
    ) -> Dict[str, str]:
        """Recomendar asignación óptima de tareas a AGVs"""
        try:
            # Preparar datos
            agv_data = []
            for agv in agvs:
                agv_data.append(
                    {
                        "id": agv.agv_id,
                        "name": agv.name,
                        "position": {"x": agv.position.x, "y": agv.position.y},
                        "battery": agv.battery_level,
                        "status": agv.status.value,
                    }
                )

            task_data = []
            for task in tasks:
                task_data.append(
                    {
                        "id": task.task_id,
                        "description": task.description,
                        "origin": {"x": task.origin.x, "y": task.origin.y},
                        "destination": {
                            "x": task.destination.x,
                            "y": task.destination.y,
                        },
                        "priority": task.priority.value,
                        "container": task.container_id,
                    }
                )

            prompt = f"""
            Como experto en optimización logística del Puerto de Chancay, asigna tareas a AGVs de manera óptima.

            AGVs disponibles: {json.dumps(agv_data, indent=2)}
            Tareas pendientes: {json.dumps(task_data, indent=2)}

            Criterios de optimización:
            1. Minimizar distancia total de viaje
            2. Balancear carga de trabajo
            3. Considerar nivel de batería
            4. Priorizar tareas urgentes
            5. Maximizar eficiencia operacional

            Formato JSON de respuesta:
            {{
                "agv_id": "task_id",
                ...
            }}
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en asignación óptima de recursos en logística portuaria.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"Error en recomendación de asignación: {e}")
            # Fallback: asignación simple por proximidad
            assignments = {}
            available_tasks = tasks.copy()

            for agv in agvs:
                if available_tasks and agv.battery_level > 30:
                    # Encontrar tarea más cercana
                    closest_task = min(
                        available_tasks,
                        key=lambda t: agv.position.distance_to(t.origin),
                    )
                    assignments[agv.agv_id] = closest_task.task_id
                    available_tasks.remove(closest_task)

            return assignments

    def predict_maintenance_needs(self, agvs: List[AGV]) -> Dict[str, Dict[str, Any]]:
        """Predecir necesidades de mantenimiento"""
        try:
            agv_data = []
            for agv in agvs:
                agv_data.append(
                    {
                        "id": agv.agv_id,
                        "name": agv.name,
                        "battery": agv.battery_level,
                        "status": agv.status.value,
                        "last_update": (
                            agv.last_update.isoformat() if agv.last_update else None
                        ),
                        "position": {"x": agv.position.x, "y": agv.position.y},
                    }
                )

            prompt = f"""
            Como experto en mantenimiento predictivo de AGVs, analiza estos datos:
            {json.dumps(agv_data, indent=2)}

            Predice necesidades de mantenimiento considerando:
            1. Patrones de uso
            2. Desgaste de batería
            3. Tiempo de operación
            4. Eficiencia operacional
            5. Indicadores de fallos tempranos

            Formato JSON:
            {{
                "agv_id": {{
                    "needs_maintenance": boolean,
                    "urgency": "LOW|MEDIUM|HIGH|CRITICAL",
                    "predicted_issue": "string",
                    "recommended_action": "string",
                    "estimated_cost": float,
                    "downtime_hours": float
                }},
                ...
            }}
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en mantenimiento predictivo y análisis de flotas AGV.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"Error en predicción de mantenimiento: {e}")
            # Fallback: análisis simple
            predictions = {}
            for agv in agvs:
                needs_maintenance = (
                    agv.battery_level < 50 or agv.status == AGVStatus.CHARGING
                )
                predictions[agv.agv_id] = {
                    "needs_maintenance": needs_maintenance,
                    "urgency": "HIGH" if agv.battery_level < 20 else "LOW",
                    "predicted_issue": (
                        "Batería baja"
                        if agv.battery_level < 50
                        else "Funcionamiento normal"
                    ),
                    "recommended_action": (
                        "Revisar sistema de carga"
                        if needs_maintenance
                        else "Continuar operación"
                    ),
                    "estimated_cost": (
                        random.uniform(100, 500) if needs_maintenance else 0
                    ),
                    "downtime_hours": random.uniform(1, 4) if needs_maintenance else 0,
                }
            return predictions

    def generate_fleet_insights(
        self, fleet_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generar insights inteligentes sobre la flota"""
        try:
            prompt = f"""
            Como consultor experto en optimización de flotas AGV del Puerto de Chancay, analiza estos datos:
            {json.dumps(fleet_data, indent=2)}

            Genera insights accionables sobre:
            1. Eficiencia operacional
            2. Oportunidades de mejora
            3. Tendencias de rendimiento
            4. Recomendaciones estratégicas
            5. Alertas importantes

            Formato JSON:
            [
                {{
                    "category": "EFFICIENCY|PERFORMANCE|MAINTENANCE|STRATEGY|ALERT",
                    "title": "string",
                    "description": "string",
                    "impact": "LOW|MEDIUM|HIGH|CRITICAL",
                    "recommendation": "string",
                    "metrics": {{"key": "value"}},
                    "priority": int
                }},
                ...
            ]
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un consultor senior en optimización logística y análisis de datos portuarios.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"Error generando insights: {e}")
            # Fallback: insights básicos
            insights = []

            if fleet_data.get("metrics"):
                metrics = fleet_data["metrics"]

                # Insight sobre eficiencia
                if metrics.get("fleet_efficiency", 0) < 0.7:
                    insights.append(
                        {
                            "category": "EFFICIENCY",
                            "title": "Eficiencia de flota por debajo del objetivo",
                            "description": f"La eficiencia actual es {metrics.get('fleet_efficiency', 0):.1%}, por debajo del 70% objetivo",
                            "impact": "MEDIUM",
                            "recommendation": "Revisar asignación de tareas y optimizar rutas",
                            "metrics": {
                                "current_efficiency": metrics.get("fleet_efficiency", 0)
                            },
                            "priority": 2,
                        }
                    )

                # Insight sobre batería
                avg_battery = metrics.get("average_battery", 0)
                if avg_battery < 50:
                    insights.append(
                        {
                            "category": "ALERT",
                            "title": "Nivel promedio de batería bajo",
                            "description": f"Batería promedio de flota: {avg_battery:.1f}%",
                            "impact": "HIGH",
                            "recommendation": "Implementar ciclos de carga más frecuentes",
                            "metrics": {"average_battery": avg_battery},
                            "priority": 1,
                        }
                    )

            return insights
