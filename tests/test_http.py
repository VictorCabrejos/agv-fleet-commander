from fastapi.testclient import TestClient

from agv_fleet.replay import demo_state
from agv_fleet.store import MemoryStore, SQLiteStore
from main import create_app


def test_http_proposal_assignment_pickup_delivery_and_restart(tmp_path):
    path = tmp_path / "state.db"
    with TestClient(create_app(SQLiteStore(path, demo_state()))) as client:
        plan = client.post("/plan").json()
        assert (
            client.post(
                "/assign",
                json={
                    "request_id": "assign",
                    "revision": plan["revision"],
                    "assignments": plan["assignments"],
                },
            ).status_code
            == 200
        )
        for n in range(8):
            assert client.post("/tick", json={"request_id": f"t-{n}"}).status_code == 200
        assert client.get("/state").json()["tasks"]["T"]["status"] == "picked_up"
    with TestClient(create_app(SQLiteStore(path, demo_state()))) as client:
        for n in range(8, 16):
            client.post("/tick", json={"request_id": f"t-{n}"})
        state = client.get("/state").json()
        assert state["tasks"]["T"]["status"] == "completed"
        assert state["vehicles"]["A"]["position"] == [0, 0]
        assert state["vehicles"]["A"]["battery"] == 84
        assert client.get("/health").json()["revision"] == state["revision"]


def test_http_invalid_proposal_stop_manual_and_oversize():
    with TestClient(create_app(MemoryStore(demo_state()))) as client:
        assert (
            client.post(
                "/assign",
                json={"request_id": "bad", "revision": 0, "assignments": [{"vehicle_id": "unknown"}]},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/move", json={"request_id": "m", "vehicle_id": "A", "destination": [0, 1]}
            ).status_code
            == 200
        )
        client.post("/stop", json={"request_id": "s", "vehicle_id": "A"})
        client.post("/tick", json={"request_id": "t"})
        assert client.get("/state").json()["vehicles"]["A"]["position"] == [0, 0]
        client.post("/resume", json={"request_id": "r", "vehicle_id": "A"})
        client.post("/tick", json={"request_id": "t2"})
        assert client.get("/state").json()["vehicles"]["A"]["position"] == [0, 1]
        assert client.post("/assign", content=b"x" * 100001).status_code == 413
        assert (
            client.post(
                "/move", json={"request_id": "m2", "vehicle_id": "A", "destination": [True, 1]}
            ).status_code
            == 422
        )
