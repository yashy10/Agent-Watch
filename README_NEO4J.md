# How Agent Watch Uses Neo4j

Agent Watch uses **Neo4j** as the **policy graph** for the **Security** panel. Every time the agent tries to call a tool, we query the graph to decide whether that agent is allowed to use that tool and whether the specific parameters satisfy any conditions (e.g. “email only to @company.com”).

---

## Why a graph?

- **Policies are relationships**: “support-agent can use send_email” and “send_email requires email_internal_only” are naturally modeled as nodes and edges.
- **Easy to extend**: Add new agents, tools, or conditions without changing application code.
- **Auditable**: You can inspect and visualize who can do what in Neo4j Browser or the showcase dashboard.

---

## Graph schema

### Node labels

| Label       | Purpose |
|------------|---------|
| **Agent**  | Identity making requests (e.g. `support-agent`, `admin-agent`, `data-agent`). |
| **Tool**   | Callable capability (e.g. `get_user_data`, `send_email`, `update_config`). |
| **Permission** | Optional intermediate node in the HAS_PERMISSION schema. |
| **DataScope**  | Data category a tool can access (e.g. `user_profiles`, `financial_records`). |
| **Condition**  | Rule that must hold for a permission (e.g. `email_internal_only`, `read_only_queries`). |
| **Action**     | What to do on violation (e.g. block, alert, throttle). |

### Relationships

| Relationship   | Meaning |
|----------------|--------|
| **CAN_USE**    | Agent is allowed to call this tool (optional: `max_calls_per_min`, `granted_by` on the edge). |
| **HAS_PERMISSION** → **GRANTS_USE_OF** | Alternative schema: Agent has a Permission that grants use of a Tool. |
| **REQUIRES**   | Permission or CAN_USE edge requires this Condition (e.g. send_email REQUIRES email_internal_only). |
| **ACCESSES**   | Tool touches this DataScope. |
| **ON_VIOLATION** | When a Condition is violated, this Action is used (e.g. block, alert). |

The app supports both:

- **Agent → HAS_PERMISSION → Permission → GRANTS_USE_OF → Tool**
- **Agent → CAN_USE → Tool** (with optional **REQUIRES → Condition**)

So you can use either schema (or a mix) in the same graph.

---

## How permission checks work

1. **Request**: User message is handled by the agent; the agent may emit one or more **tool calls** (tool name + parameters).
2. **Per tool call**: Agent Watch calls `check_permission(agent_name, tool_name, params)`.
3. **Neo4j** (when connected):
   - **Option A**: Look up `(Agent)-[:HAS_PERMISSION]->(Permission)-[:GRANTS_USE_OF]->(Tool)`. If no path, agent is not allowed. If path exists, load any `(Permission)-[:REQUIRES]->(Condition)` and evaluate each condition against `params`.
   - **Option B**: Look up `(Agent)-[:CAN_USE]->(Tool)` and any `(CAN_USE)-[:REQUIRES]->(Condition)`. If no CAN_USE edge, agent is not allowed. If conditions exist, evaluate them against `params`.
4. **Result**: `allowed: true/false`, `reason`, `scopes`, `source: "neo4j"`. If any condition fails (e.g. external email, destructive query), the tool is blocked and the reason is returned.

Conditions are implemented in code in `neo4j_client.py` (`_evaluate_condition`), e.g.:

- **email_internal_only**: `to` must end with `@company.com`.
- **read_only_queries**: query text must not contain DELETE, DROP, UPDATE, etc.
- **no_pii_export** / **no_config_modification**: always deny (or as configured).

---

## Where Neo4j is used in the app

| Use | Location | Purpose |
|-----|----------|---------|
| **Permission check** | `neo4j_client.check_permission()` | Decide allow/deny for each tool call (Security panel). |
| **Graph stats** | `neo4j_client.get_graph_stats()` | Counts of nodes by label and relationships by type (dashboard / status). |
| **Policy summary** | `neo4j_client.get_policy_summary()` | List of agents and their allowed tools (showcase dashboard). |
| **API** | `GET /api/graph`, `POST /api/check` | Expose graph stats and permission checks to the UI and scripts. |

The **Security** panel in the dashboard and showcase uses these to show “Allowed” vs “Blocked” and to display reasons (from Neo4j-backed `check_permission`).

---

## Setup

### 1. Neo4j instance

- Use [Neo4j Aura](https://neo4j.com/cloud/aura-free/) (free tier) or your own Neo4j server.
- Create a database and note the connection URI, username, and password.

### 2. Environment variables

In `.env` (or your environment):

```bash
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

Optional:

- `NEO4J_USER` — same as `NEO4J_USERNAME` if you prefer that name.
- `NEO4J_ACCEPT_SELF_SIGNED=1` — use if you hit SSL certificate errors (e.g. on macOS with Python 3.14). This makes the driver use the `neo4j+ssc://` scheme.

### 3. Seed the policy graph

Run once (or when you want to reset the graph):

```bash
python seed_neo4j.py
```

This script:

- Clears existing data in the database.
- Creates the nodes and relationships described above (agents, tools, data scopes, conditions, CAN_USE, REQUIRES, ACCESSES, ON_VIOLATION, etc.).

After seeding, the app will use this graph for all permission checks when `NEO4J_URI` (and credentials) are set.

---

## Local fallback

If Neo4j is not configured (`NEO4J_URI` unset) or the connection fails, Agent Watch falls back to an **in-memory policy** defined in `neo4j_client.py` (`LOCAL_POLICIES`). The logic is the same (allow/deny + conditions); only the source of truth changes from the graph to the hardcoded dict. So the demo and the Security panel still work without Neo4j; the dashboard will show `Policy: local_fallback` and the API will return `source: "local"` in permission results.

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **“Unable to retrieve routing information”** | Aura free tier often pauses; resume the database in [Neo4j Aura Console](https://console.neo4j.io). |
| **SSL certificate verify failed** | Set `NEO4J_ACCEPT_SELF_SIGNED=1` in `.env` (or use URI scheme `neo4j+ssc://...`). |
| **Connection refused / timeouts** | Check URI, credentials, and that the instance is running and reachable. |
| **Permission always denied** | Confirm the graph was seeded and that the agent/tool names in requests match node properties (e.g. `name: "support-agent"`, `name: "send_email"`). |

To verify connectivity and that the app can talk to Neo4j:

```bash
python check_neo4j_connection.py
```

---

## Files reference

| File | Role |
|------|------|
| `neo4j_client.py` | Connection, `check_permission`, `get_graph_stats`, `get_policy_summary`, condition evaluation, local fallback. |
| `seed_neo4j.py` | One-off script to clear and create the policy graph (nodes + relationships). |
| `check_neo4j_connection.py` | Simple connectivity check; suggests SSL fix if needed. |

This is how we use Neo4j: as the single source of truth for **who (agent) can do what (tool)** and under **which conditions**, so the Security panel and APIs can allow or block tool calls in real time.
