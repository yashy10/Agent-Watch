# Agent Watch — Blueprint Checklist

This project is aligned with **AgentWatch_Blueprint.pdf** (AWS x Datadog GenAI Hackathon). Use this checklist to confirm you’re at “blueprint state.”

---

## Architecture (Blueprint §2)

| Item | Status | Notes |
|------|--------|--------|
| Toy Agent → Agent Watch Proxy → Bedrock/Tools | Done | `toy_agent.py` → `agent_watch.py` → Bedrock + `mock_tools.py` |
| Agent Watch checks Neo4j before tool execution | Done | `neo4j_client.check_permission()` in `agent_watch.py` |
| Agent Watch logs to Datadog | Done | `metrics.py` (StatsD) + optional ddtrace LLM Obs |
| Attack Simulator injects into Toy Agent | Done | `attacks.py` + `demo.py` / `run_demo.py` |
| Datadog Dashboard reads telemetry | Done | `setup_datadog.py` creates 3-panel dashboard |

---

## Three Panels (Blueprint §3)

| Panel | Status | Implementation |
|-------|--------|----------------|
| **Behavior** | Done | `agent_watch.evaluate_behavior()` — Bedrock evaluator or rule-based fallback |
| **Security** | Done | `neo4j_client.check_permission()` + conditions (email_internal_only, read_only_queries) |
| **Cost** | Done | `metrics.track_cost()` + `get_cost_status()`; throttle when threshold exceeded |

---

## Code Components (Blueprint §5–9)

| Component | File(s) | Status |
|-----------|---------|--------|
| Toy Agent (Bedrock + tools) | `toy_agent.py` | Done — mock fallback when no AWS |
| Agent Watch backend | `agent_watch.py` | Done — handle_request, behavior/security/cost |
| Neo4j policy graph | `neo4j_client.py`, `seed_neo4j.py` | Done — schema matches blueprint |
| Datadog integration | `metrics.py`, `setup_datadog.py` | Done — StatsD + optional LLMObs |
| Attack simulator | `attacks.py` | Done — prompt injection, data exfil, cost spike, social engineering |
| Demo runner | `demo.py`, `run_demo.py` | Done — `run_demo.py` is blueprint name |

---

## Environment (Blueprint §8)

| Variable | Purpose |
|----------|---------|
| `DD_API_KEY`, `DD_APP_KEY`, `DD_SITE` | Datadog API and dashboard |
| `DD_LLMOBS_ENABLED=1`, `DD_LLMOBS_ML_APP=agent-watch`, `DD_LLMOBS_AGENTLESS_ENABLED=true` | LLM Observability (in `env.example`) |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Neo4j AuraDB policy graph |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` | Bedrock (optional; mock used if unset) |

---

## How to Run at Blueprint State

1. **Env**  
   Copy `env.example` to `.env` and set API keys (or use `env.example` with `load_dotenv("env.example")`).

2. **Neo4j** (optional)  
   `python seed_neo4j.py` to seed the policy graph (or use local fallback).

3. **Datadog dashboard** (optional)  
   `python setup_datadog.py` (needs `DD_APP_KEY`) to create the 3-panel dashboard.

4. **Server**  
   `python server.py` or `uvicorn server:app --port 8002`  
   Dashboard: http://localhost:8002

5. **Demo (2‑minute script, Blueprint §10)**  
   `python run_demo.py` or `python demo.py`  
   Normal request → Attack 1 (Prompt Injection) → Attack 2 (Data Exfiltration) → Attack 3 (Cost Spike).

6. **With LLM Observability**  
   `DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=agent-watch ddtrace-run python server.py`

---

## Hackathon Requirement Checklist (Blueprint §12)

| Requirement | How we meet it |
|-------------|----------------|
| AWS (Bedrock) | Toy agent + behavior evaluator use Bedrock (mock when no creds). |
| Datadog dashboards | 3-panel dashboard via `setup_datadog.py`; custom metrics via StatsD. |
| Datadog LLM Observability | Optional ddtrace; run with `ddtrace-run` and env vars above. |
| Live demo | `run_demo.py` — normal + 3 attacks, repeatable. |
| Neo4j (bonus) | Policy graph in AuraDB; Cypher in `neo4j_client.py`; local fallback if no Neo4j. |

---

## Optional / Polish

- **Lambda**: Blueprint suggests Lambda for the proxy; this repo uses FastAPI. For hackathon, FastAPI is enough.
- **SSM**: Config is via env/`.env`; SSM can be added for production.
- **Talking points**: See Blueprint §11 (Judge Q&A) and §10 (Demo script wording).

You’re at blueprint state when: env is set, Neo4j (or fallback) and Datadog are configured, `run_demo.py` runs all four phases, and the Datadog dashboard shows behavior, security, and cost.
