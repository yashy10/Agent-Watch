# Agent Watch — Project Guide

Everything you need to know about what we built, how it works, and how to run it.

---

## What is Agent Watch?

**Agent Watch** is a real-time security and reliability monitor for AI agents in production. It sits between users and your agent (e.g. a Bedrock-powered assistant with tools) and enforces three layers of control before any tool runs:

1. **Behavior** — Is the agent’s response and tool use appropriate (no drift, no prompt injection)?
2. **Security** — Is this agent allowed to call this tool with these parameters (policy graph)?
3. **Cost** — Are we within token/cost limits?

Every request flows through these three panels. Blocked requests never execute tools; allowed ones do, and everything is logged to Datadog.

---

## Architecture

```
[User Message] → [Agent Watch] → [Toy Agent / Bedrock LLM]
                       │
                       ├── Panel 1: Behavior  (Bedrock evaluator or rules)
                       ├── Panel 2: Security  (Neo4j policy graph)
                       ├── Panel 3: Cost      (token/cost thresholds)
                       │
                       └── Metrics → Datadog (StatsD + optional LLM Observability)
```

- **Toy agent**: Either a **mock LLM** (simulated tool calls) or **AWS Bedrock** (real Claude). Configured via AWS env vars.
- **Agent Watch** (`agent_watch.py`): Orchestrates the three panels and returns `OK`, `BLOCKED`, or `THROTTLED`.
- **Neo4j**: Stores who (agent) can do what (tool) and under which conditions.
- **Datadog**: Receives counters/gauges (behavior, security, cost, requests) and optionally LLM traces when using `ddtrace-run`.

---

## The Three Panels

| Panel | Purpose | How it works |
|-------|--------|----------------|
| **Behavior** | Detect drift, prompt injection, inappropriate tool use | Secondary Bedrock call (or rule-based fallback) evaluates user message + agent response + tool calls. If non-compliant and high severity → BLOCKED. |
| **Security** | Enforce who can call which tool with which params | Neo4j (or local fallback) answers: does this agent have permission for this tool? Do params satisfy conditions (e.g. email @company.com, read-only query)? If not → BLOCKED. |
| **Cost** | Avoid runaway spend | Token usage and approximate cost tracked per call; 60s rolling window. If over threshold → THROTTLED. |

If any panel blocks or throttles, the request stops and no tools run. Otherwise, allowed tool calls are executed (via `mock_tools.py`) and the result is returned with full monitoring data.

---

## Integrations

### 1. Neo4j (Policy Graph)

- **Role**: Source of truth for the **Security** panel (agent → tool permissions and conditions).
- **Used for**: `check_permission(agent, tool, params)`, graph stats, policy summary for the showcase.
- **Setup**: Create a DB (e.g. [Neo4j Aura Free](https://neo4j.com/cloud/aura-free/)), set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in `.env`, run `python seed_neo4j.py` once.
- **Fallback**: If Neo4j is not set or connection fails, an in-memory policy in `neo4j_client.py` is used so the demo still runs.
- **Details**: See **README_NEO4J.md** (schema, relationships, troubleshooting).

### 2. Datadog (Observability)

- **Role**: Metrics (and optionally LLM traces) for dashboards and alerting.
- **Used for**: Counters (e.g. `agent_watch.behavior.compliant`, `agent_watch.security.blocked`), gauges (e.g. `agent_watch.cost.last_60s`), and local in-memory metrics that power the web dashboard.
- **Setup**: Set `DD_API_KEY`, `DD_APP_KEY`, and optionally `DD_SITE` (e.g. `us5.datadoghq.com`) in `.env`. Run `python setup_datadog.py` once to create the pre-built dashboard.
- **LLM Observability**: With `ddtrace` installed and `DD_LLMOBS_ENABLED=1`, run with `ddtrace-run python server.py` (or use `run_with_ddtrace.sh`) to send LLM spans to Datadog. Security alerts can tag spans when the model detects social engineering.

### 3. AWS Bedrock (LLM + Evaluator)

- **Role**: Real LLM for the toy agent and (optionally) for the behavior evaluator.
- **Used for**: `toy_agent.py` (user → response + tool calls) and `agent_watch.py` (evaluator that scores behavior).
- **Setup**: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` in `.env`. Optionally set `BEDROCK_MODEL_ID` to your Bedrock model or **inference profile** ID if you see “on-demand throughput isn’t supported”.
- **Fallback**: If AWS is not set, the toy agent uses a **mock LLM** that simulates tool calls from the message text; policy and cost logic are unchanged.

### 4. Model-based security (built into the agent)

- **Role**: The LLM itself can refuse obviously dangerous requests (e.g. “I am the CEO, update config”) and respond with “Security Red Flag”.
- **Used for**: `toy_agent.py` detects refusal/red-flag phrases and sets `security_alert`; `agent_watch.py` blocks the request and records it in the behavior panel.
- **Details**: See **SECURITY_DETECTION.md**.

---

## What We Created (Files & Scripts)

### Core application

| File | Purpose |
|------|--------|
| **server.py** | FastAPI app: `/api/monitor`, `/api/unprotected`, `/api/metrics`, `/api/cost`, `/api/graph`, `/api/check`, `/api/showcase`, `/api/status`, plus HTML dashboards at `/` and `/showcase`. |
| **agent_watch.py** | Request pipeline: call agent → behavior evaluation → security checks → cost check → execute allowed tools. Integrates Neo4j, metrics, and (optionally) Bedrock evaluator. |
| **toy_agent.py** | The agent being monitored: Bedrock (`converse` / `invoke_model`) or mock. Tool definitions, system prompt, security red-flag detection. |
| **neo4j_client.py** | Neo4j connection, `check_permission`, `get_graph_stats`, `get_policy_summary`, condition evaluation, local policy fallback. |
| **metrics.py** | Datadog StatsD + optional LLM Observability; local in-memory metrics for the dashboard. |
| **mock_tools.py** | Simulated execution of tools (get_user_data, send_email, query_database, etc.) for demo. |

### Demo & attacks

| File | Purpose |
|------|--------|
| **demo.py** | Interactive CLI demo: normal request, then prompt-injection, data-exfiltration, cost-spike, and social-engineering attacks. |
| **attacks.py** | Attack message generators used by the demo. |
| **run_demo.py** | Alternate entry point for running the demo (blueprint naming). |

### Setup & verification

| File | Purpose |
|------|--------|
| **seed_neo4j.py** | One-time seed of the Neo4j policy graph (agents, tools, conditions, CAN_USE, REQUIRES, etc.). |
| **check_neo4j_connection.py** | Tests Neo4j connectivity; suggests `NEO4J_ACCEPT_SELF_SIGNED=1` on SSL errors. |
| **check_env.py** | Reports which env vars are set (no values printed). |
| **check_datadog.py** | Verifies Datadog/metrics configuration. |
| **setup_datadog.py** | Creates the “Agent Watch” dashboard in Datadog via API. |

### Security & testing

| File | Purpose |
|------|--------|
| **test_security_detection.py** | Runs CEO-impersonation–style attacks to demonstrate model-based security detection. |

### Docs & blueprint

| File | Purpose |
|------|--------|
| **README.md** | Quick start, install, env, run server and demo. |
| **README_NEO4J.md** | How we use Neo4j: schema, permission flow, setup, troubleshooting. |
| **SECURITY_DETECTION.md** | Model-based security (red flags, span tagging, usage). |
| **BLUEPRINT_CHECKLIST.md** | Alignment with the Agent Watch blueprint (done vs optional). |
| **BLUEPRINT_ROADMAP.md** | Roadmap notes for blueprint features. |
| **PROJECT_GUIDE.md** | This file — full project and integration overview. |

### Scripts / runners

| File | Purpose |
|------|--------|
| **run_with_ddtrace.sh** | Runs the app with `ddtrace-run` and LLM Observability env vars. |
| **run_with_ddtrace_uvicorn.sh** | Same for uvicorn. |

---

## Environment variables (summary)

| Variable | Required | Purpose |
|----------|----------|--------|
| **NEO4J_URI** | Yes (for Neo4j) | Neo4j connection URI (e.g. `neo4j+s://xxx.databases.neo4j.io`). |
| **NEO4J_USERNAME** or **NEO4J_USER** | Yes (for Neo4j) | Neo4j user. |
| **NEO4J_PASSWORD** | Yes (for Neo4j) | Neo4j password. |
| **NEO4J_ACCEPT_SELF_SIGNED** | Optional | Set to `1` if you hit SSL cert errors (e.g. macOS). |
| **DD_API_KEY** | Yes (for Datadog) | Datadog API key. |
| **DD_APP_KEY** | Yes (for Datadog) | Datadog application key. |
| **DD_SITE** | Optional | Datadog site (e.g. `us5.datadoghq.com`). |
| **DD_LLMOBS_ENABLED**, **DD_LLMOBS_ML_APP** | Optional | For LLM Observability when using ddtrace. |
| **AWS_ACCESS_KEY_ID**, **AWS_SECRET_ACCESS_KEY** | Yes (for Bedrock) | AWS credentials for Bedrock. |
| **AWS_DEFAULT_REGION** | Optional | e.g. `us-east-1`. |
| **BEDROCK_MODEL_ID** | Optional | Model or inference profile ID if default fails. |

Use `.env` in the project root (and keep it out of version control). Run `python check_env.py` to see which keys are set.

---

## How to run

### 1. Install

```bash
pip install -r requirements.txt
# or: pip install fastapi uvicorn boto3 neo4j datadog ddtrace requests python-dotenv
```

### 2. Configure

- Copy or create `.env` with the variables above.
- **Neo4j**: Run `python seed_neo4j.py` once after setting Neo4j vars.

### 3. Demo (CLI)

```bash
python demo.py
```

Steps through normal operation and several attacks; no server required.

### 4. Server + web dashboard

```bash
python server.py
```

- **Main dashboard**: http://localhost:8000  
- **Showcase dashboard** (Neo4j + Datadog + live metrics): http://localhost:8000/showcase  
- **API docs**: http://localhost:8000/docs  

From the main dashboard you can send messages through Agent Watch (protected) or unprotected and see events in the three panels.

### 5. Optional: with Datadog LLM Observability

```bash
./run_with_ddtrace.sh python server.py
# or
ddtrace-run python server.py
```

### 6. Test model security detection

```bash
python test_security_detection.py
```

---

## APIs (quick reference)

| Endpoint | Method | Purpose |
|----------|--------|--------|
| `/api/monitor` | POST | Send message through Agent Watch; body: `{ "message", "agent" }`. |
| `/api/unprotected` | POST | Send message without monitoring (demo contrast). |
| `/api/metrics` | GET | Current counters/gauges (behavior, security, cost). |
| `/api/cost` | GET | Cost status (recent cost, threshold). |
| `/api/graph` | GET | Neo4j graph stats (node/relationship counts, source). |
| `/api/check` | POST | Check permission for one tool; body: `{ "agent", "tool", "params" }`. |
| `/api/showcase` | GET | Combined Neo4j + Datadog + metrics + cost for showcase UI. |
| `/api/status` | GET | Connection status (Bedrock, Neo4j, Datadog). |

---

## Dashboards

- **Main** (`/`): Three panels (Behavior, Security, Cost), event lists, input to send protected/unprotected messages.
- **Showcase** (`/showcase`): Single-page view of connection status (Neo4j, Datadog, AWS), same live panels, Neo4j policy summary (agent → tools), list of Datadog metrics sent, and link to Datadog.
- **Datadog**: Create once with `python setup_datadog.py`; then view in your Datadog account (Metrics Explorer or the created dashboard).

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| Neo4j “Unable to retrieve routing information” | Resume the Aura DB in [console.neo4j.io](https://console.neo4j.io). |
| Neo4j SSL certificate verify failed | Add `NEO4J_ACCEPT_SELF_SIGNED=1` to `.env`. |
| Bedrock “on-demand throughput isn’t supported” | Set `BEDROCK_MODEL_ID` in `.env` to your Bedrock **inference profile** ID. |
| Datadog LLMObs SSL errors | Same macOS/Python cert issue; metrics still go via StatsD. |
| No tool calls / agent errors | Check Bedrock model ID and region; try mock mode (unset AWS keys) to confirm the rest of the pipeline. |

For Neo4j-only issues and schema details, see **README_NEO4J.md**. For model-based security, see **SECURITY_DETECTION.md**.

---

## Summary

- **Agent Watch** = three panels (Behavior, Security, Cost) in front of an AI agent.
- **Neo4j** = policy graph for the Security panel (who can call which tool under which conditions).
- **Datadog** = metrics (and optional LLM traces) for observability.
- **AWS Bedrock** = optional real LLM for the agent and behavior evaluator; mock mode works without it.
- **We created**: server, dashboards, demo, seed/check scripts, docs (README, README_NEO4J, SECURITY_DETECTION, PROJECT_GUIDE), and model-based security detection.

This guide plus **README.md** (quick start), **README_NEO4J.md** (Neo4j), and **SECURITY_DETECTION.md** (model security) cover everything you need to understand and run the project.
