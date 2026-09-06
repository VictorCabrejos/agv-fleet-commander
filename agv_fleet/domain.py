"""Owned grid-world state and strict proposal contracts (standard library only)."""

from dataclasses import asdict, dataclass, field
from math import isfinite


class DomainError(ValueError):
    """An action violates the declared simulator contract."""


class StorageError(RuntimeError):
    """State was not acknowledged as committed."""


class ConflictError(StorageError):
    """The proposal was based on an obsolete state revision."""


def identifier(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 80:
        raise DomainError("IDs must be nonempty strings of at most 80 characters")
    return value


def point(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise DomainError("A position must contain two grid integers")
    if any(type(x) is not int for x in value):
        raise DomainError("Grid coordinates must be integers, not booleans or floats")
    return tuple(value)


@dataclass
class World:
    width: int = 20
    height: int = 20
    obstacles: list = field(default_factory=list)

    def validate(self):
        if any(type(v) is not int or not 1 <= v <= 100 for v in (self.width, self.height)):
            raise DomainError("World dimensions must be grid integers in 1..100")
        self.obstacles = [point(p) for p in self.obstacles]
        if len(set(self.obstacles)) != len(self.obstacles):
            raise DomainError("Duplicate obstacle")
        for x, y in self.obstacles:
            if not (0 <= x < self.width and 0 <= y < self.height):
                raise DomainError("Obstacle outside world")

    def free(self, p):
        x, y = point(p)
        return 0 <= x < self.width and 0 <= y < self.height and (x, y) not in self.obstacles


@dataclass
class Vehicle:
    id: str
    position: tuple
    battery: float = 100.0
    capacity: float = 100.0
    status: str = "idle"
    task_id: str | None = None
    route: list = field(default_factory=list)
    cursor: int = 0
    pickup_index: int | None = None
    wait_ticks: int = 0
    stopped_from: str | None = None


@dataclass
class Task:
    id: str
    pickup: tuple
    delivery: tuple
    weight: float = 1.0
    priority: int = 0
    status: str = "pending"
    vehicle_id: str | None = None


@dataclass(frozen=True)
class Proposal:
    vehicle_id: str
    task_id: str
    route: tuple
    pickup_index: int

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict) or set(value) != {"vehicle_id", "task_id", "route", "pickup_index"}:
            raise DomainError("Proposal requires exactly vehicle_id, task_id, route, pickup_index")
        route = value["route"]
        if not isinstance(route, list) or not 1 <= len(route) <= 10000:
            raise DomainError("Route must contain 1..10000 grid points")
        index = value["pickup_index"]
        if type(index) is not int or not 0 <= index < len(route):
            raise DomainError("Invalid pickup index")
        return cls(
            identifier(value["vehicle_id"]),
            identifier(value["task_id"]),
            tuple(point(p) for p in route),
            index,
        )


@dataclass
class State:
    world: World
    vehicles: dict = field(default_factory=dict)
    tasks: dict = field(default_factory=dict)
    revision: int = 0
    tick: int = 0
    receipts: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def encode(self):
        return asdict(self)

    @classmethod
    def decode(cls, value):
        state = cls(
            World(**value["world"]),
            {k: Vehicle(**v) for k, v in value["vehicles"].items()},
            {k: Task(**v) for k, v in value["tasks"].items()},
            value["revision"],
            value["tick"],
            value["receipts"],
            value["events"],
        )
        state.validate()
        return state

    def validate(self):
        self.world.validate()
        if type(self.revision) is not int or self.revision < 0 or type(self.tick) is not int or self.tick < 0:
            raise DomainError("Invalid state revision or tick")
        if len(self.vehicles) > 100 or len(self.tasks) > 1000:
            raise DomainError("Demo state limit exceeded")
        positions = set()
        for key, v in self.vehicles.items():
            if key != identifier(v.id):
                raise DomainError("Vehicle identity mismatch")
            v.position = point(v.position)
            if not self.world.free(v.position) or v.position in positions:
                raise DomainError("Vehicle position blocked or occupied")
            positions.add(v.position)
            if type(v.battery) not in (int, float) or not isfinite(v.battery) or not 0 <= v.battery <= 100:
                raise DomainError("Invalid battery")
            if type(v.capacity) not in (int, float) or not isfinite(v.capacity) or v.capacity <= 0:
                raise DomainError("Invalid capacity")
            if v.status not in {"idle", "moving", "transporting", "manual", "stopped"}:
                raise DomainError("Invalid vehicle status")
            v.route = [point(p) for p in v.route]
            if v.status == "idle":
                if v.task_id or v.route or v.pickup_index is not None:
                    raise DomainError("Idle vehicle retains an assignment")
            else:
                validate_route(self.world, v.route)
                if not 0 <= v.cursor < len(v.route) or v.route[v.cursor] != v.position:
                    raise DomainError("Route cursor does not match position")
                if v.task_id:
                    if v.task_id not in self.tasks or self.tasks[v.task_id].vehicle_id != v.id:
                        raise DomainError("Vehicle/task reference mismatch")
                elif v.status not in {"manual", "stopped"}:
                    raise DomainError("Moving vehicle lacks task")
        for key, t in self.tasks.items():
            if key != identifier(t.id):
                raise DomainError("Task identity mismatch")
            t.pickup, t.delivery = point(t.pickup), point(t.delivery)
            if not self.world.free(t.pickup) or not self.world.free(t.delivery):
                raise DomainError("Task endpoint blocked")
            if type(t.weight) not in (int, float) or not isfinite(t.weight) or t.weight <= 0:
                raise DomainError("Task weight must be positive")
            if type(t.priority) is not int or not 0 <= t.priority <= 3:
                raise DomainError("Task priority must be 0..3")
            if t.status not in {"pending", "assigned", "picked_up", "paused", "completed"}:
                raise DomainError("Invalid task status")
            if t.status in {"pending", "completed"}:
                if t.vehicle_id is not None:
                    raise DomainError("Inactive task retains a vehicle")
            else:
                v = self.vehicles.get(t.vehicle_id)
                if v is None or v.task_id != t.id:
                    raise DomainError("Task/vehicle reference mismatch")
                if v.pickup_index is None or not 0 <= v.pickup_index < len(v.route):
                    raise DomainError("Missing pickup checkpoint")
                if v.route[v.pickup_index] != t.pickup or v.route[-1] != t.delivery:
                    raise DomainError("Route does not implement task")
                if t.status == "paused" and v.status != "stopped":
                    raise DomainError("Paused task vehicle must be stopped")
                if t.status == "assigned" and (v.status != "moving" or v.cursor > v.pickup_index):
                    raise DomainError("Assigned task passed its pickup")
                if t.status == "picked_up" and (v.status != "transporting" or v.cursor < v.pickup_index):
                    raise DomainError("Transport without pickup")


def validate_route(world, route):
    if not route or len(route) > 10000:
        raise DomainError("Invalid route length")
    for p in route:
        if not world.free(p):
            raise DomainError("Route enters obstacle or leaves world")
    for a, b in zip(route, route[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            raise DomainError("Route must use adjacent cardinal grid cells")
