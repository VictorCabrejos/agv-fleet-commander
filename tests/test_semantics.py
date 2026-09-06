import copy
import sqlite3
from dataclasses import asdict
from unittest.mock import Mock

import pytest

from agv_fleet.domain import ConflictError, DomainError, Proposal, State, StorageError, Task, Vehicle, World
from agv_fleet.engine import FleetEngine
from agv_fleet.planning import HeuristicPlanner, OpenAIPlanner, parse_proposals
from agv_fleet.replay import demo_state, run
from agv_fleet.store import MemoryStore, SQLiteStore


def engine(state=None):
    return FleetEngine(MemoryStore(state or demo_state()))


def assign(e, request="assign"):
    plan = e.plan()
    return e.assign(request, plan["revision"], plan["assignments"])


def test_pickup_before_delivery_executes_obstacle_detour():
    e = engine()
    assign(e)
    e.tick("first")
    assert e.snapshot().tasks["T"].status == "assigned"
    assert e.snapshot().vehicles["A"].position != (0, 0)
    for n in range(40):
        if e.snapshot().tasks["T"].status == "completed":
            break
        e.tick(f"tick-{n}")
    state = e.snapshot()
    assert state.tasks["T"].status == "completed"
    events = state.events
    pickup = next(i for i, ev in enumerate(events) if ev["kind"] == "picked_up")
    delivery = next(i for i, ev in enumerate(events) if ev["kind"] == "completed")
    assert pickup < delivery
    positions = [ev["position"] for ev in events if ev["kind"] == "moved"]
    assert [4, 0] in positions and positions[-1] == [0, 0]
    assert not any(tuple(p) in state.world.obstacles for p in positions)
    assert state.vehicles["A"].battery == 100 - len(positions)
    assert len(positions) == 16  # 8 each way around the two blocked cells.
    assert state.vehicles["A"].status == "idle"
    assert state.tasks["T"].vehicle_id is None


@pytest.mark.parametrize("after_pickup", [False, True])
def test_stop_pauses_both_references_and_resume_completes(after_pickup):
    e = engine()
    assign(e)
    if after_pickup:
        for n in range(8):
            e.tick(f"before-{n}")
    before = e.snapshot().vehicles["A"].position
    e.stop("stop", "A")
    state = e.snapshot()
    assert state.vehicles["A"].status == "stopped"
    assert state.vehicles["A"].task_id == "T"
    assert state.tasks["T"].vehicle_id == "A"
    assert state.tasks["T"].status == "paused"
    assert e.plan()["assignments"] == []
    e.tick("while-stopped")
    assert e.snapshot().vehicles["A"].position == before
    e.resume("resume", "A")
    assert e.snapshot().tasks["T"].status == ("picked_up" if after_pickup else "assigned")
    for n in range(30):
        e.tick(f"after-{n}")
    assert e.snapshot().tasks["T"].status == "completed"


def test_manual_move_persists_target_and_finishes_after_restart(tmp_path):
    path = tmp_path / "fleet.db"
    e = FleetEngine(SQLiteStore(path, demo_state()))
    e.manual_move("move", "A", (0, 3))
    e.tick("t1")
    e = FleetEngine(SQLiteStore(path, demo_state()))
    assert e.snapshot().vehicles["A"].position == (0, 1)
    e.tick("t2")
    e.tick("t3")
    assert e.snapshot().vehicles["A"].position == (0, 3)
    assert e.snapshot().vehicles["A"].status == "idle"


def test_route_cursor_and_task_phase_survive_restart(tmp_path):
    path = tmp_path / "fleet.db"
    e = FleetEngine(SQLiteStore(path, demo_state()))
    assign(e)
    for n in range(8):
        e.tick(f"before-{n}")
    e = FleetEngine(SQLiteStore(path, demo_state()))
    assert e.snapshot().tasks["T"].status == "picked_up"
    for n in range(8):
        e.tick(f"after-{n}")
    assert e.snapshot().tasks["T"].status == "completed"


@pytest.mark.parametrize(
    "defect",
    [
        "unknown_vehicle",
        "unknown_task",
        "duplicate",
        "jump",
        "obstacle",
        "no_pickup",
        "battery",
        "capacity",
        "unavailable",
        "assigned_task",
    ],
)
def test_invalid_proposal_batch_cannot_mutate(defect):
    state = demo_state()
    p = HeuristicPlanner().propose(state)[0]
    values = asdict(p)
    values["route"] = list(values["route"])
    if defect == "unknown_vehicle":
        values["vehicle_id"] = "invented"
    if defect == "unknown_task":
        values["task_id"] = "invented"
    if defect == "jump":
        values["route"][1] = (8, 8)
    if defect == "obstacle":
        values["route"][1] = (2, 0)
    if defect == "no_pickup":
        values["pickup_index"] = 0
    if defect == "battery":
        state.vehicles["A"].battery = 10
    if defect == "capacity":
        state.tasks["T"].weight = 101
    e = engine(state)
    if defect == "unavailable":
        e.stop("stop", "A")
    if defect == "assigned_task":
        assign(e)
    proposals = [values, values] if defect == "duplicate" else [values]
    before = e.snapshot().encode()
    with pytest.raises(DomainError):
        e.assign("bad", e.snapshot().revision, proposals)
    assert e.snapshot().encode() == before


def test_whole_batch_validated_before_mutation():
    state = demo_state()
    state.vehicles["B"] = Vehicle("B", (9, 9))
    state.tasks["U"] = Task("U", (8, 9), (7, 9))
    e = engine(state)
    plan = e.plan()
    plan["assignments"][-1]["task_id"] = "missing"
    before = e.snapshot().encode()
    with pytest.raises(DomainError):
        e.assign("bad", 0, plan["assignments"])
    assert e.snapshot().encode() == before


def test_stale_proposal_and_duplicate_command():
    e = engine()
    plan = e.plan()
    first = e.assign("same", 0, plan["assignments"])
    assert e.assign("same", 0, plan["assignments"]) == first
    with pytest.raises(DomainError):
        e.assign("new", 0, plan["assignments"])
    with pytest.raises(DomainError):
        e.tick("same")
    assert e.snapshot().revision == 1


def test_uncertain_acknowledgment_replays_durable_receipt_after_restart(tmp_path):
    path = tmp_path / "fleet.db"
    store = SQLiteStore(path, demo_state())
    e = FleetEngine(store)
    plan = e.plan()
    original_commit = store.commit

    def committed_but_acknowledgment_lost(expected, state):
        original_commit(expected, state)
        raise StorageError("Synthetic connection loss after durable commit")

    store.commit = committed_but_acknowledgment_lost
    with pytest.raises(StorageError):
        e.assign("uncertain", plan["revision"], plan["assignments"])
    e = FleetEngine(SQLiteStore(path, demo_state()))
    receipt = e.assign("uncertain", plan["revision"], plan["assignments"])
    assert receipt["assigned"] == 1 and receipt["revision"] == 1
    first = e.tick("tick-once")
    e = FleetEngine(SQLiteStore(path, demo_state()))
    assert e.tick("tick-once") == first
    assert e.snapshot().vehicles["A"].cursor == 1
    assert sum(ev["kind"] == "assigned" for ev in e.snapshot().events) == 1


def test_commit_failure_has_no_acknowledgment_or_partial_state(tmp_path):
    store = SQLiteStore(tmp_path / "fleet.db", demo_state())
    e = FleetEngine(store)
    before = e.snapshot().encode()
    store._before_commit = Mock(side_effect=sqlite3.OperationalError("injected failure"))
    with pytest.raises(StorageError):
        assign(e)
    assert e.snapshot().encode() == before
    store._before_commit = Mock()
    assert assign(e)["assigned"] == 1


def test_tick_failure_rolls_back_movement_and_receipt(tmp_path):
    store = SQLiteStore(tmp_path / "fleet.db", demo_state())
    e = FleetEngine(store)
    assign(e)
    before = e.snapshot().encode()
    store._before_commit = Mock(side_effect=sqlite3.OperationalError("failure"))
    with pytest.raises(StorageError):
        e.tick("t1")
    assert e.snapshot().encode() == before
    store._before_commit = Mock()
    e.tick("t1")
    assert e.snapshot().vehicles["A"].cursor == 1


def test_concurrent_revision_conflict_is_atomic(tmp_path):
    store = SQLiteStore(tmp_path / "fleet.db", demo_state())
    a, b = store.read(), store.read()
    a.revision += 1
    b.revision += 1
    store.commit(0, a)
    with pytest.raises(ConflictError):
        store.commit(0, b)
    assert store.read().encode() == a.encode()


def test_provider_failure_and_malformed_json_do_not_mutate():
    e = engine()
    before = e.snapshot().encode()
    client = Mock()
    client.with_options.return_value = client
    client.chat.completions.create.side_effect = TimeoutError()
    with pytest.raises(DomainError):
        e.plan(OpenAIPlanner(client, "explicit-test-model"))
    client.with_options.assert_called_once_with(timeout=15.0, max_retries=0)
    assert client.chat.completions.create.call_count == 1
    assert e.snapshot().encode() == before


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        '{"assignments":null}',
        '{"assignments":[],"extra":0}',
        '{"assignments":[],"assignments":[]}',
        '{"assignments":[{"vehicle_id":"A"}]}',
        "NaN",
        "x" * 100001,
    ],
    ids=["array", "null", "extra", "duplicate", "missing", "nan", "oversize"],
)
def test_provider_schema_rejects_bad_text(text):
    with pytest.raises(DomainError):
        parse_proposals(text)


def test_provider_schema_accepts_typed_but_domain_rejects_invented_id():
    import json

    e = engine()
    p = e.plan()["assignments"][0]
    p["vehicle_id"] = "unknown"
    proposals = parse_proposals(json.dumps({"assignments": [p]}))
    with pytest.raises(DomainError):
        e.assign("bad", 0, proposals)
    assert e.snapshot().revision == 0


def test_new_tasks_unique_and_idempotent_without_clock():
    e = engine()
    a = e.create_task("request-1", (0, 0), (1, 0))
    b = e.create_task("request-2", (0, 0), (1, 0))
    assert a["task_id"] != b["task_id"]
    assert e.create_task("request-1", (0, 0), (1, 0)) == a
    with pytest.raises(DomainError):
        e.create_task("request-1", (0, 0), (3, 0))


def test_priority_capacity_and_battery_have_deterministic_baseline():
    state = State(
        World(10, 10),
        {"A": Vehicle("A", (0, 0), battery=10)},
        {
            "low": Task("low", (0, 1), (0, 2), priority=0),
            "urgent": Task("urgent", (1, 0), (3, 0), priority=3),
        },
    )
    assert engine(state).plan()["assignments"][0]["task_id"] == "urgent"
    state.vehicles["A"].battery = 2
    assert engine(state).plan()["assignments"] == []


def test_blocked_route_no_assignment_and_bounded_traffic_wait():
    state = State(
        World(3, 2, [(1, 0), (1, 1)]), {"A": Vehicle("A", (0, 0))}, {"T": Task("T", (2, 0), (2, 1))}
    )
    assert engine(state).plan()["assignments"] == []
    state = State(World(3, 1), {"A": Vehicle("A", (0, 0)), "B": Vehicle("B", (1, 0))})
    e = engine(state)
    e.manual_move("move", "A", (2, 0))
    for n in range(5):
        e.tick(f"tick-{n}")
    assert e.snapshot().vehicles["A"].status == "stopped"
    assert e.snapshot().vehicles["A"].position == (0, 0)
    assert e.snapshot().vehicles["B"].position == (1, 0)


def test_replay_hash_is_equal_across_memory_and_sqlite(tmp_path):
    assert run() == run() == run(SQLiteStore(tmp_path / "fleet.db", demo_state()))


def test_corrupt_persisted_state_fails_closed(tmp_path):
    path = tmp_path / "fleet.db"
    SQLiteStore(path, demo_state())
    with sqlite3.connect(path) as db:
        db.execute("UPDATE fleet SET body='{}'")
    with pytest.raises(StorageError):
        SQLiteStore(path, demo_state())


def test_read_returns_detached_state_and_false_direct_typed_route_rejected():
    e = engine()
    detached = e.snapshot()
    detached.vehicles["A"].battery = 0
    assert e.snapshot().vehicles["A"].battery == 100
    p = Proposal("A", "T", ((0, 0), (True, 0)), 1)
    with pytest.raises(DomainError):
        e.assign("bad", 0, [p])


def test_invariant_rejects_orphaned_references():
    e = engine()
    assign(e)
    state = copy.deepcopy(e.snapshot())
    state.vehicles["A"].task_id = None
    with pytest.raises(DomainError):
        state.validate()


@pytest.mark.parametrize("seed", range(30))
def test_seeded_worlds_complete_every_feasible_single_vehicle_plan(seed):
    import random

    rng = random.Random(seed)
    cells = [(x, y) for x in range(6) for y in range(6)]
    rng.shuffle(cells)
    start, pickup, delivery = cells[:3]
    state = State(World(6, 6, cells[3:9]), {"A": Vehicle("A", start)}, {"T": Task("T", pickup, delivery)})
    e = engine(state)
    plan = e.plan()
    if not plan["assignments"]:
        return  # Disconnected maps are legitimately infeasible.
    e.assign("assign", 0, plan["assignments"])
    route = e.snapshot().vehicles["A"].route
    for n in range(len(route)):
        e.tick(f"t-{n}")
        e.snapshot().validate()
    state = e.snapshot()
    assert state.tasks["T"].status == "completed"
    assert state.vehicles["A"].position == delivery
    assert state.vehicles["A"].battery >= 2
    kinds = [ev["kind"] for ev in state.events]
    assert kinds.index("picked_up") < kinds.index("completed")
