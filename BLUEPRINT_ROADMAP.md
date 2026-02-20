# Agent Watch — Blueprint alignment roadmap

Use this to bring the project to the state described in **AgentWatch_Blueprint.pdf**.

## 1. Get the blueprint as text (so we can align exactly)

In your terminal:

```bash
pip install pypdf
python blueprint_extract.py
```

That creates **AgentWatch_Blueprint.txt**. You can open it, or paste the relevant sections (architecture, UI, deployment, etc.) into the chat so we can match the implementation to the blueprint.

---

## 2. Current state vs typical blueprint items

| Blueprint area        | Current state in this repo                    | How to align |
|-----------------------|-----------------------------------------------|--------------|
| **Architecture**       | Request → Agent Watch → Bedrock + Tools; 3 panels (Behavior, Security, Cost) | Already matches typical diagram; we can rename/restructure if the PDF shows a different layout. |
| **Behavior panel**    | Rule-based + optional Bedrock evaluator        | Add or change evaluator (e.g. different model, thresholds) if the blueprint specifies. |
| **Security panel**    | Neo4j policy graph + local fallback           | Ensure agents/tools/conditions match the blueprint; add policies if listed. |
| **Cost panel**        | Token cost, 60s window, threshold throttle     | Adjust thresholds, window, or add budget alerts if the blueprint defines them. |
| **Dashboard UI**      | Single HTML page in `server.py` (3 panels, input, status) | Rebuild or restyle to match blueprint screenshots/layout (e.g. separate pages, charts). |
| **API**               | `/api/monitor`, `/api/unprotected`, `/api/metrics`, `/api/graph`, `/api/check`, `/api/cost` | Add or change endpoints to match blueprint API spec. |
| **Observability**     | Datadog metrics + optional ddtrace LLM        | Add dashboards/monitors (e.g. `setup_datadog.py`) or extra metrics if the blueprint lists them. |
| **Deployment**        | Run `python server.py` or uvicorn             | Add Dockerfile, env template, or cloud steps if the blueprint describes deployment. |
| **Neo4j graph**       | `seed_neo4j.py` with agents, tools, conditions | Extend seed script to match blueprint schema (nodes, relationships, attributes). |
| **Demo / attacks**     | `demo.py`, `attacks.py` (prompt injection, exfil, cost spike) | Add or rename scenarios to match blueprint “attack” or “test” list. |

---

## 3. Next steps

1. **Extract the PDF** (step 1 above) and, if you can, paste the sections that describe:
   - Target architecture (diagram or bullet list)
   - UI / dashboard (layout, panels, or screenshots description)
   - API or integration points
   - Deployment or environment
   - Policy/security model (agents, tools, conditions)
2. **Share those sections** (or the whole **AgentWatch_Blueprint.txt**), and we can:
   - Update the app (UI, API, metrics, Neo4j seed) to match the blueprint.
   - Add a concrete checklist (e.g. “Blueprint section 3.2 → change X in `server.py`”).

If you prefer to work from the PDF only, describe the target state (e.g. “dashboard should look like X”, “we need endpoint Y”) and we can drive changes from that.
