# Agent Watch — MVP

Real-time security & reliability monitor for AI agents in production.

## Quick Start

### 1. Install dependencies
```bash
pip install boto3 neo4j fastapi uvicorn datadog ddtrace requests
```

### 2. Set environment variables
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
export NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password
export DD_API_KEY=your_datadog_api_key
export DD_APP_KEY=your_datadog_app_key
export DD_SITE=datadoghq.com
```

### 3. Seed Neo4j policy graph
```bash
python scripts/seed_neo4j.py
```

**Neo4j "Unable to retrieve routing information":** Usually means your **AuraDB instance is paused** (free tier pauses after inactivity). Open [Neo4j Aura Console](https://console.neo4j.io), select your database, and click **Resume**. Use the connection URI from that page in `.env` as `NEO4J_URI`. Env accepts either `NEO4J_USER` or `NEO4J_USERNAME`. If you see **SSL certificate verify failed** (e.g. on macOS with Python 3.14), add `NEO4J_ACCEPT_SELF_SIGNED=1` to `.env` so the driver uses the `neo4j+ssc://` scheme.

### 4. Start Agent Watch server
```bash
python server.py
```

### 5. Run the demo
```bash
# Terminal 2 — run the demo script
python demo.py
```

**Making the demo look real (not hardcoded):**
- **With Bedrock:** Set `AWS_ACCESS_KEY_ID` and run the demo. The toy agent becomes a real LLM that may actually comply with prompt injection; Agent Watch still blocks at the policy layer. The same pipeline runs for any user input. If you see *"on-demand throughput isn't supported"*, set `BEDROCK_MODEL_ID` in `.env` to your Bedrock **inference profile** ID (from AWS Console → Bedrock → Inference profiles).
- **Try your own message:** At the end of the demo you can type any message and see it go through the same Behavior → Security → Cost checks. That shows the policy is general, not a fixed script.
- **Variation:** Prompt-injection attack uses one of several phrasings at random so the same attack class can look different across runs.

## Viewing Datadog (see your metrics)

Your app sends metrics to Datadog. To see them:

1. **Open Datadog** (use your site from `DD_SITE`):
   - US5: **https://app.datadoghq.com** (or **https://us5.datadoghq.com**)
   - EU: https://app.datadoghq.eu  
   - US3: https://us3.datadoghq.com  
   - US1: https://app.datadoghq.com  

2. **Create the Agent Watch dashboard** (one-time; needs `DD_APP_KEY` in env):
   ```bash
   python setup_datadog.py
   ```
   This creates a dashboard **"🛡️ Agent Watch — Real-Time Agent Monitor"** with Behavior, Security, and Cost panels.

3. **Or browse metrics manually:**
   - In Datadog: **Metrics → Explorer** (or **Dashboards → New Dashboard**).
   - Query metrics like: `agent_watch.behavior.compliant`, `agent_watch.security.blocked`, `agent_watch.cost.last_60s`, `agent_watch.request.ok`.

4. **Generate some traffic** so data appears: run the server, open the web UI, send a few messages (or run `python demo.py`). Metrics may take 1–2 minutes to show in Datadog.

## Architecture
```
[User Request] → [Agent Watch Proxy] → [Bedrock LLM + Tools]
                        │
                        ├── checks Neo4j policy graph (security)
                        ├── evaluates behavior via Bedrock (behavior)
                        ├── tracks cost via metrics (cost)
                        └── logs everything to Datadog (observability)
```

## Files
- `server.py` — FastAPI server (main entry point)
- `agent_watch.py` — Core monitoring logic (3 panels)
- `toy_agent.py` — The agent being monitored
- `mock_tools.py` — Simulated tool execution
- `neo4j_client.py` — Neo4j policy graph queries
- `metrics.py` — Datadog metrics + LLM Observability
- `demo.py` — Interactive demo runner
- `scripts/seed_neo4j.py` — Seeds the policy graph
- `attacks.py` — Three attack scenarios for demo
