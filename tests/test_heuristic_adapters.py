from adapters.heuristic_adapter import HeuristicAnalytics, HeuristicRouteOptimizer
from domain.entities import AGV, AGVStatus, Position, Task, TaskPriority


def make_agv(agv_id: str = "A-1") -> AGV:
    return AGV(agv_id, "Test", Position(0, 0), 80, AGVStatus.IDLE)


def make_task(task_id: str = "T-1") -> Task:
    return Task(
        task_id,
        "Move synthetic load",
        Position(3, 4),
        Position(6, 8),
        TaskPriority.MEDIUM,
    )


def test_direct_route_has_reproducible_metrics():
    route = HeuristicRouteOptimizer().optimize_route(make_agv(), make_task())
    assert route.total_distance == 10
    assert route.fuel_consumption == 0.1
    assert [point.x for point in route.waypoints] == [0, 3, 6]


def test_assignment_chooses_nearest_task_once():
    analytics = HeuristicAnalytics()
    near = make_task("near")
    far = Task("far", "Far", Position(100, 100), Position(110, 110), TaskPriority.LOW)
    assert analytics.recommend_task_assignment([make_agv()], [far, near]) == {"A-1": "near"}
