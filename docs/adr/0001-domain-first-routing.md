# ADR 1: deterministic domain authority and atomic simulation state

Status: accepted for remediation branch.

The prior pipeline mutated assignments before computing routes, saved task and vehicle separately, and simulated motion toward delivery without using the generated route. Additional checks around those paths would leave conflicting state owners.

Decision: replace them with one typed state model and one command engine. Planners are proposal-only. A bounded cardinal grid makes obstacle, pickup and energy constraints executable and inspectable. A single SQLite snapshot transaction stores reciprocal references, cursor, phase, trace and receipt together. Detached snapshots and revision comparison prevent partial mutation and stale-plan acceptance.

Consequences: restart and failure behavior can be tested without robotics hardware or a provider. The old CSV datasets remain inert and recoverable. APIs intentionally change to explicit plan/assign/tick/stop/resume commands. The design is limited to a small single-host simulator with conservative cell reservations; it does not claim enterprise fleet scheduling or production autonomy.
