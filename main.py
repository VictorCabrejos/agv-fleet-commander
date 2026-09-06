"""Local-only API for a deterministic simulator; startup owns runtime storage."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from agv_fleet.domain import ConflictError, DomainError, StorageError
from agv_fleet.engine import FleetEngine
from agv_fleet.planning import HeuristicPlanner, OpenAIPlanner
from agv_fleet.replay import demo_state
from agv_fleet.store import SQLiteStore


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=80)


class Assignment(Command):
    revision: StrictInt = Field(ge=0)
    assignments: list[dict] = Field(max_length=100)


class Move(Command):
    vehicle_id: str = Field(min_length=1, max_length=80)
    destination: tuple[StrictInt, StrictInt]


class VehicleCommand(Command):
    vehicle_id: str = Field(min_length=1, max_length=80)


class NewTask(Command):
    pickup: tuple[StrictInt, StrictInt]
    delivery: tuple[StrictInt, StrictInt]
    weight: float = Field(default=1.0, gt=0, allow_inf_nan=False)
    priority: StrictInt = Field(default=3, ge=0, le=3)


class BodyLimit:
    """Bound request bodies even when Content-Length is absent or dishonest."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 100000:
                return await JSONResponse({"detail": "Request exceeds 100KB"}, status_code=413)(
                    scope, receive, send
                )
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay():
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay, send)


def create_app(store=None, planner=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.engine = FleetEngine(
            store or SQLiteStore(os.environ.get("AGV_STATE_PATH", ".runtime/fleet.sqlite3"), demo_state())
        )
        app.state.planner = planner or HeuristicPlanner()
        if planner is None and os.environ.get("AGV_PLANNER", "heuristic") == "openai":
            from openai import OpenAI

            model = os.environ.get("AGV_OPENAI_MODEL")
            if not model:
                raise DomainError("Opt-in OpenAI planner requires AGV_OPENAI_MODEL")
            app.state.planner = OpenAIPlanner(OpenAI(), model)
        yield

    app = FastAPI(
        title="AGV Fleet Commander",
        version="1.0.0",
        lifespan=lifespan,
        description="Educational deterministic grid simulator. Proposals cannot bypass domain validation. No physical vehicles.",
    )
    app.add_middleware(BodyLimit)

    @app.exception_handler(DomainError)
    async def invalid(request, error):
        return JSONResponse({"detail": str(error)}, status_code=422)

    @app.exception_handler(StorageError)
    async def storage_error(request, error):
        code = 409 if isinstance(error, ConflictError) else 503
        return JSONResponse({"detail": str(error)}, status_code=code)

    @app.get("/health")
    def health(request: Request):
        state = request.app.state.engine.snapshot()
        return {"status": "ready", "revision": state.revision, "mode": "educational_simulator"}

    @app.get("/state")
    def state(request: Request):
        return request.app.state.engine.snapshot().encode()

    @app.post("/plan")
    def plan(request: Request):
        return request.app.state.engine.plan(request.app.state.planner)

    @app.post("/assign")
    def assign(command: Assignment, request: Request):
        return request.app.state.engine.assign(command.request_id, command.revision, command.assignments)

    @app.post("/tick")
    def tick(command: Command, request: Request):
        return request.app.state.engine.tick(command.request_id)

    @app.post("/move")
    def move(command: Move, request: Request):
        return request.app.state.engine.manual_move(
            command.request_id, command.vehicle_id, command.destination
        )

    @app.post("/stop")
    def stop(command: VehicleCommand, request: Request):
        return request.app.state.engine.stop(command.request_id, command.vehicle_id)

    @app.post("/resume")
    def resume(command: VehicleCommand, request: Request):
        return request.app.state.engine.resume(command.request_id, command.vehicle_id)

    @app.post("/tasks")
    def tasks(command: NewTask, request: Request):
        return request.app.state.engine.create_task(
            command.request_id, command.pickup, command.delivery, command.weight, command.priority
        )

    @app.get("/", response_class=HTMLResponse)
    def index():
        return """<!doctype html><html lang="en"><meta charset="utf-8"><title>AGV simulator</title>
        <style>body{max-width:1000px;margin:3rem auto;font:18px system-ui;background:#101826;color:#e6eef7}button{padding:12px;margin:5px}pre{white-space:pre-wrap;font-size:14px}</style>
        <h1>AGV Fleet Commander</h1><p>Deterministic grid simulation. No physical vehicle control.</p>
        <p>Plan first, inspect the proposal, then explicitly assign it. One tick moves at most one cell per vehicle.</p>
        <button id="plan">Propose</button><button id="assign">Validate and assign</button><button id="tick">Tick</button>
        <button id="stop">Stop A</button><button id="resume">Resume A</button><a href="/docs">API contracts</a>
        <h2>Proposal / command result</h2><pre id="result"></pre><h2>Durable state and trace</h2><pre id="state"></pre>
        <script>let proposal=null;const out=document.getElementById('result');
        async function refresh(){document.getElementById('state').textContent=JSON.stringify(await (await fetch('/state')).json(),null,2)}
        async function call(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const v=await r.json();out.textContent=JSON.stringify(v,null,2);await refresh();if(!r.ok)throw Error(v.detail);return v}
        document.getElementById('plan').onclick=async()=>{try{proposal=await call('/plan',{})}catch(e){proposal=null}};
        document.getElementById('assign').onclick=async()=>{try{if(!proposal)throw Error('Propose first');await call('/assign',{request_id:crypto.randomUUID(),revision:proposal.revision,assignments:proposal.assignments});proposal=null}catch(e){out.textContent=String(e)}};
        for(const name of ['tick','stop','resume'])document.getElementById(name).onclick=async()=>{try{await call('/'+name,{request_id:crypto.randomUUID(),...(name==='tick'?{}:{vehicle_id:'A'})})}catch(e){out.textContent=String(e)}};
        refresh();</script></html>"""

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=5001)
