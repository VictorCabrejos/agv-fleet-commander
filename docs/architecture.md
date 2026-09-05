# Architecture

The FastAPI layer translates HTTP input into domain entities. Domain services
depend only on abstract ports. Adapters implement CSV persistence,
notifications, route construction, and analytics.

\`\`\`mermaid
flowchart TB
    HTTP[FastAPI routes] --> ORCH[FleetOrchestrationService]
    HTTP --> CONTROL[AGVControlService]
    ORCH --> REPO[AGV and Task repository ports]
    ORCH --> ROUTE[Route optimizer port]
    ORCH --> ANALYTICS[Analytics port]
    ORCH --> NOTICE[Notification port]
    REPO --> CSV[CSVDataAdapter]
    ROUTE --> HEURISTIC[HeuristicRouteOptimizer]
    ANALYTICS --> SUMMARY[HeuristicAnalytics]
    ROUTE -. optional .-> OPENAI[OpenAI adapter]
    ANALYTICS -. optional .-> OPENAI
\`\`\`

The default composition is offline and deterministic. Setting
\`OPENAI_API_KEY\` selects the optional provider adapters at application startup.
No production control or safety layer is implemented.
