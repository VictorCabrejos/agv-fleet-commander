"""Deterministic offline adapters for routing and fleet analytics."""

from datetime import datetime
from typing import Any

from domain.entities import AGV, FleetMetrics, Position, Route, Task
from domain.ports import AIAnalyticsPort, RouteOptimizerPort


class HeuristicRouteOptimizer(RouteOptimizerPort):
    """Build direct routes without network or paid API calls."""

    def optimize_route(
        self, agv: AGV, task: Task, obstacles: list[Position] | None = None
    ) -> Route:
        del obstacles
        waypoints = [agv.position, task.origin, task.destination]
        distance = sum(
            start.distance_to(end) for start, end in zip(waypoints, waypoints[1:])
        )
        return Route(
            route_id=f"DIRECT_{agv.agv_id}_{task.task_id}",
            agv_id=agv.agv_id,
            task_id=task.task_id,
            waypoints=waypoints,
            total_distance=distance,
            estimated_time=(distance / 1000) / 20 * 60,
            fuel_consumption=distance / 100,
            created_at=datetime.now(),
        )

    def optimize_fleet_routes(
        self, agvs: list[AGV], tasks: list[Task]
    ) -> dict[str, Route]:
        tasks_by_agv = {task.assigned_agv_id: task for task in tasks}
        return {
            agv.agv_id: self.optimize_route(agv, tasks_by_agv[agv.agv_id])
            for agv in agvs
            if agv.agv_id in tasks_by_agv
        }

    def predict_congestion(self, current_routes: list[Route]) -> dict[str, float]:
        density: dict[str, int] = {}
        for route in current_routes:
            for waypoint in route.waypoints:
                cell = f"{int(waypoint.x // 50) * 50},{int(waypoint.y // 50) * 50}"
                density[cell] = density.get(cell, 0) + 1
        return {cell: count / max(len(current_routes), 1) for cell, count in density.items()}


class HeuristicAnalytics(AIAnalyticsPort):
    """Provide reproducible portfolio-demo analytics from domain state."""

    def analyze_fleet_performance(
        self, metrics: FleetMetrics, historical_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        del historical_data
        return {
            "score": metrics.fleet_efficiency,
            "average_battery": metrics.average_battery,
        }

    def predict_maintenance_needs(
        self, agvs: list[AGV]
    ) -> dict[str, dict[str, Any]]:
        return {
            agv.agv_id: {
                "needs_maintenance": agv.battery_level < 15,
                "reason": "low simulated battery" if agv.battery_level < 15 else "none",
            }
            for agv in agvs
        }

    def recommend_task_assignment(
        self, available_agvs: list[AGV], pending_tasks: list[Task]
    ) -> dict[str, str]:
        remaining = list(pending_tasks)
        assignments: dict[str, str] = {}
        for agv in sorted(available_agvs, key=lambda item: item.agv_id):
            if not remaining:
                break
            task = min(remaining, key=lambda item: agv.position.distance_to(item.origin))
            assignments[agv.agv_id] = task.task_id
            remaining.remove(task)
        return assignments

    def generate_fleet_insights(
        self, fleet_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        metrics = fleet_data["metrics"]
        return [
            {
                "category": "SIMULATION",
                "title": "Fleet snapshot",
                "description": f"{metrics['active_agvs']} active of {metrics['total_agvs']} AGVs",
                "impact": "INFORMATIONAL",
                "priority": 3,
            }
        ]
