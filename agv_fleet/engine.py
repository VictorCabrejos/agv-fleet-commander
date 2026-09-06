"""Propose -> validate all -> atomically commit -> execute the accepted route."""

import hashlib
import json
from dataclasses import asdict
from uuid import NAMESPACE_URL, uuid5

from .domain import DomainError, Proposal, Task, identifier, point, validate_route
from .planning import HeuristicPlanner, shortest_path
from .store import Store


class FleetEngine:
    reserve = 2.0
    max_wait_ticks = 5
    max_receipts = 10000  # Fail explicitly rather than forgetting idempotency history.

    def __init__(self, store: Store):
        self.store = store

    def snapshot(self):
        return self.store.read()

    @staticmethod
    def _event(state, kind, **details):
        if len(state.events) >= 100000:
            raise DomainError("Demo trace capacity reached; export and start a new scenario")
        state.events.append(
            {
                "sequence": len(state.events) + 1,
                "tick": state.tick,
                "revision": state.revision + 1,
                "kind": kind,
                **details,
            }
        )

    def _command(self, request_id, action, payload, apply, expected=None):
        identifier(request_id)
        fingerprint = hashlib.sha256(
            json.dumps([action, payload], sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
        state = self.store.read()
        if request_id in state.receipts:
            receipt = state.receipts[request_id]
            if receipt["fingerprint"] != fingerprint:
                raise DomainError("Request ID was already used for a different command")
            return receipt["result"]
        if len(state.receipts) >= self.max_receipts or len(state.events) >= 100000:
            raise DomainError("Demo history capacity reached; export and start a new scenario")
        if expected is not None and state.revision != expected:
            raise DomainError("Proposal revision is stale; plan again")
        revision = state.revision
        result = apply(state)
        state.validate()
        self._event(state, "command", request_id=request_id, action=action, fingerprint=fingerprint)
        state.revision += 1
        result = {**result, "revision": state.revision, "request_id": request_id}
        state.receipts[request_id] = {"fingerprint": fingerprint, "result": result}
        self.store.commit(revision, state)  # Commit before acknowledgment. No retry of effects.
        return result

    def plan(self, planner=None):
        state = self.store.read()
        planner = planner or HeuristicPlanner()
        proposals = planner.propose(state)
        # Provider is untrusted even when implementing the typed planner protocol.
        self._validate_assignments(state, proposals)
        return {
            "revision": state.revision,
            "planner": planner.name,
            "assignments": [{**asdict(p), "route": [list(cell) for cell in p.route]} for p in proposals],
        }

    def _validate_assignments(self, state, proposals):
        if not isinstance(proposals, list) or len(proposals) > 100:
            raise DomainError("At most 100 typed proposals allowed")
        vehicles, tasks = set(), set()
        for p in proposals:
            if not isinstance(p, Proposal):
                raise DomainError("Planner must return typed proposals")
            # Validate typed instances too: dataclass annotations are not runtime checks.
            p = Proposal.parse({**asdict(p), "route": list(p.route)})
            v, t = state.vehicles.get(p.vehicle_id), state.tasks.get(p.task_id)
            if (
                v is None
                or t is None
                or v.status != "idle"
                or v.task_id
                or t.status != "pending"
                or t.vehicle_id
            ):
                raise DomainError("Proposal must use currently available vehicles and pending tasks")
            if p.vehicle_id in vehicles or p.task_id in tasks:
                raise DomainError("Duplicate vehicle or task assignment")
            vehicles.add(p.vehicle_id)
            tasks.add(p.task_id)
            validate_route(state.world, p.route)
            if p.route[0] != v.position or p.route[p.pickup_index] != t.pickup or p.route[-1] != t.delivery:
                raise DomainError("Route must connect current position, pickup, then delivery")
            if t.pickup in p.route[: p.pickup_index]:
                raise DomainError("Pickup index must be its first visit")
            if len(p.route) - 1 + self.reserve > v.battery:
                raise DomainError("Insufficient battery for complete route plus reserve")
            if t.weight > v.capacity:
                raise DomainError("Payload exceeds vehicle capacity")

    def assign(self, request_id, revision, proposals):
        if type(revision) is not int or revision < 0:
            raise DomainError("Expected revision must be a nonnegative integer")
        if not isinstance(proposals, list) or len(proposals) > 100:
            raise DomainError("At most 100 proposals allowed")
        parsed = [Proposal.parse(p) if isinstance(p, dict) else p for p in proposals]

        def apply(state):
            self._validate_assignments(state, parsed)  # Entire batch before any mutation.
            for p in parsed:
                v, t = state.vehicles[p.vehicle_id], state.tasks[p.task_id]
                v.status, v.task_id = "moving", t.id
                v.route, v.cursor, v.pickup_index, v.wait_ticks = list(p.route), 0, p.pickup_index, 0
                t.status, t.vehicle_id = "assigned", v.id
                self._event(
                    state,
                    "assigned",
                    vehicle_id=v.id,
                    task_id=t.id,
                    route=[list(p) for p in v.route],
                    pickup_index=v.pickup_index,
                )
            return {"assigned": len(parsed)}

        if any(not isinstance(p, Proposal) for p in parsed):
            raise DomainError("Invalid proposal")
        return self._command(
            request_id,
            "assign",
            {"revision": revision, "proposals": [asdict(p) for p in parsed]},
            apply,
            revision,
        )

    def create_task(self, request_id, pickup, delivery, weight=1.0, priority=3):
        pickup, delivery = point(pickup), point(delivery)
        task_id = str(uuid5(NAMESPACE_URL, "agv-task:" + identifier(request_id)))

        def apply(state):
            if task_id in state.tasks:
                raise DomainError("Task identity already exists")
            state.tasks[task_id] = Task(task_id, pickup, delivery, weight, priority)
            self._event(state, "task_created", task_id=task_id)
            return {"task_id": task_id}

        return self._command(request_id, "create_task", [pickup, delivery, weight, priority], apply)

    def manual_move(self, request_id, vehicle_id, destination):
        destination = point(destination)

        def apply(state):
            v = self._vehicle(state, vehicle_id)
            if v.status != "idle":
                raise DomainError("Manual movement requires idle vehicle")
            route = shortest_path(state.world, v.position, destination)
            if len(route) - 1 + self.reserve > v.battery:
                raise DomainError("Insufficient battery for manual route")
            v.route, v.cursor, v.status, v.wait_ticks = route, 0, "manual", 0
            self._event(state, "manual_move", vehicle_id=v.id, route=[list(p) for p in route])
            return {"vehicle_id": v.id, "distance": len(route) - 1}

        return self._command(request_id, "manual_move", [vehicle_id, destination], apply)

    @staticmethod
    def _vehicle(state, vehicle_id):
        if vehicle_id not in state.vehicles:
            raise DomainError("Unknown vehicle")
        return state.vehicles[vehicle_id]

    def _stop(self, state, v, reason):
        if v.status == "stopped":
            return
        if v.status == "idle":
            v.route, v.cursor = [v.position], 0
        v.stopped_from, v.status = v.status, "stopped"
        if v.task_id:
            state.tasks[v.task_id].status = "paused"
        self._event(state, "stopped", vehicle_id=v.id, task_id=v.task_id, reason=reason)

    def stop(self, request_id, vehicle_id):
        def apply(state):
            self._stop(state, self._vehicle(state, vehicle_id), "operator")
            return {"vehicle_id": vehicle_id, "status": "stopped"}

        return self._command(request_id, "stop", vehicle_id, apply)

    def resume(self, request_id, vehicle_id):
        def apply(state):
            v = self._vehicle(state, vehicle_id)
            if v.status != "stopped" or v.stopped_from not in {"idle", "manual", "moving", "transporting"}:
                raise DomainError("Vehicle is not resumable")
            validate_route(state.world, v.route[v.cursor :])
            if len(v.route) - 1 - v.cursor + self.reserve > v.battery:
                raise DomainError("Insufficient battery to resume")
            v.status, v.stopped_from, v.wait_ticks = v.stopped_from, None, 0
            if v.task_id:
                state.tasks[v.task_id].status = "picked_up" if v.status == "transporting" else "assigned"
            if v.status == "idle":
                v.route, v.cursor = [], 0
            self._event(state, "resumed", vehicle_id=v.id, task_id=v.task_id)
            return {"vehicle_id": v.id, "status": v.status}

        return self._command(request_id, "resume", vehicle_id, apply)

    def _checkpoint(self, state, v):
        if v.task_id:
            t = state.tasks[v.task_id]
            if t.status == "assigned" and v.cursor == v.pickup_index:
                t.status, v.status = "picked_up", "transporting"
                self._event(state, "picked_up", vehicle_id=v.id, task_id=t.id)
        if v.cursor == len(v.route) - 1:
            if v.task_id:
                t = state.tasks[v.task_id]
                if t.status != "picked_up":
                    raise DomainError("Completion without pickup is forbidden")
                t.status, t.vehicle_id = "completed", None
                self._event(state, "completed", vehicle_id=v.id, task_id=t.id)
            else:
                self._event(state, "manual_arrived", vehicle_id=v.id)
            v.status, v.task_id, v.route, v.cursor, v.pickup_index = "idle", None, [], 0, None

    def tick(self, request_id):
        def apply(state):
            state.tick += 1
            occupied = {v.position: v.id for v in state.vehicles.values()}
            moves = 0
            for v in sorted(state.vehicles.values(), key=lambda v: v.id):
                if v.status not in {"moving", "transporting", "manual"}:
                    continue
                self._checkpoint(state, v)
                if v.status == "idle":
                    continue
                target = v.route[v.cursor + 1]
                if target in occupied:
                    v.wait_ticks += 1
                    self._event(state, "waiting", vehicle_id=v.id, blocked_by=occupied[target])
                    if v.wait_ticks >= self.max_wait_ticks:
                        self._stop(state, v, "traffic_wait_limit")
                    continue
                if v.battery < 1 + self.reserve:
                    self._stop(state, v, "battery_reserve")
                    continue
                old = v.position
                v.position, v.cursor, v.battery, v.wait_ticks = target, v.cursor + 1, v.battery - 1, 0
                del occupied[old]
                occupied[target] = v.id
                moves += 1
                self._event(state, "moved", vehicle_id=v.id, position=list(target), battery=v.battery)
                self._checkpoint(state, v)
            return {"tick": state.tick, "moves": moves}

        return self._command(request_id, "tick", None, apply)
