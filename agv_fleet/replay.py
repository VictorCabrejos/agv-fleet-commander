"""Executable, owned scenario and restart-independent deterministic trace evidence."""

import hashlib
import json

from .domain import State, Task, Vehicle, World
from .engine import FleetEngine
from .store import MemoryStore


def demo_state():
    return State(
        World(10, 10, [(2, 0), (2, 1)]),
        {"A": Vehicle("A", (0, 0))},
        {"T": Task("T", (4, 0), (0, 0), priority=3)},
    )


def run(store=None):
    engine = FleetEngine(store or MemoryStore(demo_state()))
    plan = engine.plan()
    result = engine.assign("assign-1", plan["revision"], plan["assignments"])
    assert result["assigned"] == 1
    for number in range(100):
        engine.tick(f"tick-{number}")
        if engine.snapshot().tasks["T"].status == "completed":
            break
    state = engine.snapshot()
    assert state.tasks["T"].status == "completed"
    kinds = [e["kind"] for e in state.events]
    assert kinds.index("picked_up") < kinds.index("completed")
    assert state.vehicles["A"].position == (0, 0)
    trace = json.dumps(state.encode(), sort_keys=True, separators=(",", ":"))
    return {
        "scenario": "blocked-direct-path-pickup-return-v1",
        "ticks": state.tick,
        "moves": sum(e["kind"] == "moved" for e in state.events),
        "battery": state.vehicles["A"].battery,
        "sha256": hashlib.sha256(trace.encode()).hexdigest(),
    }


if __name__ == "__main__":
    first, second = run(), run()
    assert first == second, "Scenario replay differed"
    print(json.dumps({"replay_equal": True, **first}, indent=2))
