# AGV Fleet Commander

AGV Fleet Commander is an educational fleet-orchestration simulator built
around ports and adapters. It models AGV availability, task assignment, route
construction, battery state, and fleet alerts without claiming control of real
industrial equipment.

## Why it is portfolio-relevant

The differentiator is the domain boundary: orchestration depends on repository,
routing, analytics, and notification ports. CSV persistence and deterministic
heuristics make the core workflow inspectable offline; optional OpenAI adapters
can be supplied without coupling the domain to a vendor SDK.

## Architecture

\`\`\`mermaid
flowchart LR
    API[FastAPI] --> S[Domain services]
    S --> P[Ports]
    P --> CSV[CSV adapter]
    P --> H[Offline heuristic adapters]
    P --> O[Optional OpenAI adapters]
    P --> N[Logging notification adapter]
\`\`\`

See [docs/architecture.md](docs/architecture.md) and
[docs/adr/0001-domain-first-routing.md](docs/adr/0001-domain-first-routing.md).

## Run locally

Requires Python 3.10+.

\`\`\`bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -e ".[runtime]"
uvicorn main:app --host 127.0.0.1 --port 5001
\`\`\`

The default path is deterministic and does not require a network call. To try
the optional model-backed adapters, set \`OPENAI_API_KEY\` in your shell. Never
commit credentials. Copy \`.env.example\` only as a reference; the application
reads process environment variables.

## Test

\`\`\`bash
python -m pip install -e ".[dev]"
pytest -q
ruff check --select F .
\`\`\`

Tests cover domain rules, deterministic routing and analytics, and API health.
\`scripts/manual_navigation_check.py\` is an opt-in probe for an already-running
server and is not part of the automated suite.

## Data and limitations

- \`data/*.csv\` is mutable simulator state, not production telemetry.
- Routing uses Euclidean distance and fixed speed/energy assumptions.
- “AI insights” in offline mode are deterministic summaries, not predictions.
- There is no authentication, durable database, hardware protocol, collision
  avoidance controller, or production safety certification.
- This software must not be used to command physical vehicles.

## License

Code is available under the MIT License. Sample CSV content is synthetic demo
state created for this repository.
