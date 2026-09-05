# ADR 0001: Keep routing behind a domain port

- Status: accepted
- Date: 2026-09-05

## Context

Portfolio evaluation must be possible without credentials, paid calls, or
non-deterministic model output. The simulator also needs a clear separation
between business rules and external model SDKs.

## Decision

`FleetOrchestrationService` consumes `RouteOptimizerPort` and
`AIAnalyticsPort`. The default adapters are deterministic heuristics. Optional
OpenAI adapters remain replaceable composition-root choices.

## Consequences

Core workflows and tests run offline. Heuristics are deliberately simple and
must not be represented as industrial route optimization or predictive
maintenance. Any future provider adapter must preserve the same port contracts.
