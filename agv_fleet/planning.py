"""Bounded shortest-path proposals; all proposals still pass engine validation."""

import json
from collections import deque

from .domain import DomainError, Proposal


def shortest_path(world, start, goal):
    if not world.free(start) or not world.free(goal):
        raise DomainError("Route endpoint is blocked")
    parents = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            route = []
            while cell is not None:
                route.append(cell)
                cell = parents[cell]
            return list(reversed(route))
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            nxt = (cell[0] + dx, cell[1] + dy)
            if nxt not in parents and world.free(nxt):
                parents[nxt] = cell
                queue.append(nxt)
    raise DomainError("No traversable route")


class HeuristicPlanner:
    name = "priority-shortest-feasible-v1"

    def propose(self, state):
        available = sorted((v for v in state.vehicles.values() if v.status == "idle"), key=lambda v: v.id)
        tasks = sorted(
            (t for t in state.tasks.values() if t.status == "pending"), key=lambda t: (-t.priority, t.id)
        )
        proposals = []
        for task in tasks:
            choices = []
            for v in available:
                if task.weight > v.capacity:
                    continue
                try:
                    pickup = shortest_path(state.world, v.position, task.pickup)
                    delivery = shortest_path(state.world, task.pickup, task.delivery)
                except DomainError:
                    continue
                route = pickup + delivery[1:]
                if len(route) - 1 + 2 <= v.battery:
                    choices.append((len(route), v.id, route, len(pickup) - 1))
            if choices:
                _, vehicle_id, route, index = min(choices)
                proposals.append(Proposal(vehicle_id, task.id, tuple(route), index))
                available = [v for v in available if v.id != vehicle_id]
        return proposals


def parse_proposals(text):
    if not isinstance(text, str) or len(text.encode("utf-8")) > 100000:
        raise DomainError("Provider output exceeds 100KB")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DomainError("Duplicate JSON field")
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=lambda x: (_ for _ in ()).throw(DomainError("Nonfinite JSON")),
        )
    except (ValueError, RecursionError) as exc:
        raise DomainError("Invalid provider JSON") from exc
    if not isinstance(value, dict) or set(value) != {"assignments"}:
        raise DomainError("Expected assignments object")
    if not isinstance(value["assignments"], list) or len(value["assignments"]) > 100:
        raise DomainError("At most 100 assignments allowed")
    return [Proposal.parse(p) for p in value["assignments"]]


class OpenAIPlanner:
    """Explicit opt-in only. One bounded SDK call; no implicit fallback/retries."""

    name = "openai-proposal-v1"

    def __init__(self, client, model):
        self.client = client.with_options(timeout=15.0, max_retries=0)
        self.model = model

    def propose(self, state):
        # Only caller-owned simulator positions/tasks; never arbitrary user documents.
        payload = {
            "world": state.encode()["world"],
            "vehicles": [vars(v) for v in state.vehicles.values() if v.status == "idle"],
            "tasks": [vars(t) for t in state.tasks.values() if t.status == "pending"],
        }
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_completion_tokens=4000,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Propose only. Return JSON {assignments:[{vehicle_id,task_id,route:[[x,y],...],pickup_index}]}. "
                            "Route includes vehicle start, pickup at pickup_index, delivery last. "
                            "Use adjacent cardinal integer grid cells, avoid obstacles; each task and vehicle once. "
                            "Respect capacity, battery cost one per step and reserve two. Never invent IDs."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, allow_nan=False)},
                ],
            )
            return parse_proposals(response.choices[0].message.content)
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError("Provider unavailable; no assignment committed") from exc
