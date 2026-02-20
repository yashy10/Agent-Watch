"""
neo4j_client.py — Neo4j policy graph client.
Handles security checks against the permission graph.

If Neo4j is not configured, falls back to a local in-memory
policy store so the demo works without a Neo4j instance.
"""

import os

# ── Try Neo4j connection ──
NEO4J_ENABLED = False
_driver = None

try:
    if os.environ.get("NEO4J_URI"):
        from neo4j import GraphDatabase

        _uri = os.environ["NEO4J_URI"].strip()
        if os.environ.get("NEO4J_ACCEPT_SELF_SIGNED", "").lower() in ("1", "true", "yes"):
            _uri = _uri.replace("neo4j+s://", "neo4j+ssc://", 1)
        _user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME") or "neo4j"
        _password = os.environ["NEO4J_PASSWORD"]

        _driver = GraphDatabase.driver(_uri, auth=(_user, _password))
        # Test connection
        with _driver.session() as session:
            session.run("RETURN 1")
        NEO4J_ENABLED = True
        print("[neo4j] Connected to Neo4j")
    else:
        print("[neo4j] NEO4J_URI not set — using local policy fallback")
except Exception as e:
    err = str(e).strip()
    print(f"[neo4j] Connection failed ({err}) — using local policy fallback")
    if "certificate" in err.lower() or "ssl" in err.lower():
        print("         → SSL cert verify failed. In .env add: NEO4J_ACCEPT_SELF_SIGNED=1")
    elif "routing" in err.lower() or "retrieve" in err.lower():
        print("         → AuraDB free tier often pauses after inactivity. Resume at https://console.neo4j.io")


# ── Local fallback policy (mirrors the Neo4j graph) ──

LOCAL_POLICIES = {
    "support-agent": {
        "allowed_tools": {
            "get_user_data": {
                "conditions": [],
                "scopes": ["user_profiles"],
                "rate_limit": 20,
            },
            "send_email": {
                "conditions": ["email_internal_only"],
                "scopes": ["user_profiles"],
                "rate_limit": 5,
            },
            "query_database": {
                "conditions": ["read_only_queries"],
                "scopes": ["support_tickets", "financial_records"],
                "rate_limit": 10,
            },
            "search_knowledge_base": {
                "conditions": [],
                "scopes": ["knowledge_base"],
                "rate_limit": 50,
            },
            "create_ticket": {
                "conditions": [],
                "scopes": ["support_tickets"],
                "rate_limit": 10,
            },
            # NOTE: update_config and export_data are NOT here = blocked
        },
    },
    "admin-agent": {
        "allowed_tools": {
            "get_user_data": {"conditions": [], "scopes": ["user_profiles"], "rate_limit": 50},
            "send_email": {"conditions": [], "scopes": ["user_profiles"], "rate_limit": 20},
            "query_database": {"conditions": [], "scopes": ["support_tickets", "financial_records"], "rate_limit": 50},
            "update_config": {"conditions": [], "scopes": ["system_config"], "rate_limit": 5},
            "export_data": {"conditions": ["no_pii_export"], "scopes": ["financial_records"], "rate_limit": 2},
        },
    },
}


def _evaluate_condition(condition: str, params: dict) -> tuple:
    """Evaluate a policy condition. Returns (passed: bool, reason: str)."""
    if condition == "email_internal_only":
        to_addr = params.get("to", "")
        if to_addr.endswith("@company.com"):
            return True, ""
        return False, f"Email to external address '{to_addr}' blocked — policy requires @company.com"

    if condition == "read_only_queries":
        query = params.get("query", "").upper()
        dangerous = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
        for kw in dangerous:
            if kw in query:
                return False, f"Query contains '{kw}' — policy requires read-only queries"
        return True, ""

    if condition == "no_pii_export":
        # Always block PII exports from support-agent
        return False, "PII data export is blocked by policy"

    if condition == "no_config_modification":
        return False, "Configuration modification is blocked by policy"

    return True, ""


def check_graph_auth(agent_name: str, tool_name: str) -> tuple:
    """
    Query using Agent -[:HAS_PERMISSION]-> Permission -[:GRANTS_USE_OF]-> Tool schema.
    Returns (authorized: bool, rules: list) or (None, []) if no row (use other schema).
    """
    if not NEO4J_ENABLED or _driver is None:
        return None, []
    query = """
    MATCH (a:Agent {name: $agent_name})-[:HAS_PERMISSION]->(p:Permission)
    MATCH (p)-[:GRANTS_USE_OF]->(t:Tool {name: $tool_name})
    OPTIONAL MATCH (p)-[:REQUIRES]->(c:Condition)
    RETURN t IS NOT NULL AS authorized, collect(c.rule) AS rules
    """
    try:
        with _driver.session() as session:
            result = session.run(
                query, agent_name=agent_name, tool_name=tool_name
            ).single()
            if result is not None:
                rules = [r for r in (result["rules"] or []) if r]
                return result["authorized"], rules
    except Exception:
        pass
    return None, []


def check_permission(agent_name: str, tool_name: str, params: dict) -> dict:
    """
    Check if an agent is allowed to call a tool with given params.
    Uses Neo4j if available, otherwise falls back to local policies.

    Returns:
        {
            "allowed": bool,
            "reason": str,
            "scopes": list,
            "source": "neo4j" | "local"
        }
    """
    if NEO4J_ENABLED:
        return _check_neo4j(agent_name, tool_name, params)
    return _check_local(agent_name, tool_name, params)


def _check_neo4j(agent_name: str, tool_name: str, params: dict) -> dict:
    """Query Neo4j for permission check. Tries HAS_PERMISSION schema first, then CAN_USE."""
    # Try Agent -[:HAS_PERMISSION]-> Permission -[:GRANTS_USE_OF]-> Tool schema first
    authorized, rules = check_graph_auth(agent_name, tool_name)
    if authorized is not None:  # we got a result from this schema
        if not authorized:
            return {
                "allowed": False,
                "reason": f"Agent '{agent_name}' has NO permission for tool '{tool_name}'",
                "scopes": [],
                "source": "neo4j",
            }
        for rule in rules:
            passed, reason = _evaluate_condition(rule, params)
            if not passed:
                return {
                    "allowed": False,
                    "reason": reason,
                    "scopes": [],
                    "source": "neo4j",
                }
        return {
            "allowed": True,
            "reason": "Permitted by policy graph",
            "scopes": [],
            "source": "neo4j",
        }

    # Fallback: original schema Agent -[:CAN_USE]-> Tool
    with _driver.session() as session:
        result = session.run("""
            MATCH (a:Agent {name: $agent})-[p:CAN_USE]->(t:Tool {name: $tool})
            OPTIONAL MATCH (t)-[:ACCESSES]->(d:DataScope)
            OPTIONAL MATCH (p)-[:REQUIRES]->(c:Condition)
            RETURN t.name AS tool,
                   p.max_calls_per_min AS rate_limit,
                   collect(DISTINCT d.name) AS allowed_scopes,
                   collect(DISTINCT c.rule) AS conditions
        """, agent=agent_name, tool=tool_name)

        record = result.single()

        if record is None:
            return {
                "allowed": False,
                "reason": f"Agent '{agent_name}' has NO permission for tool '{tool_name}'",
                "scopes": [],
                "source": "neo4j",
            }

        for cond in record["conditions"]:
            if cond:
                passed, reason = _evaluate_condition(cond, params)
                if not passed:
                    return {
                        "allowed": False,
                        "reason": reason,
                        "scopes": record["allowed_scopes"],
                        "source": "neo4j",
                    }

        return {
            "allowed": True,
            "reason": "Permitted by policy graph",
            "scopes": record["allowed_scopes"],
            "source": "neo4j",
        }


def _check_local(agent_name: str, tool_name: str, params: dict) -> dict:
    """Check against local policy fallback."""
    agent_policy = LOCAL_POLICIES.get(agent_name)
    if not agent_policy:
        return {
            "allowed": False,
            "reason": f"Unknown agent '{agent_name}'",
            "scopes": [],
            "source": "local",
        }

    tool_policy = agent_policy["allowed_tools"].get(tool_name)
    if not tool_policy:
        return {
            "allowed": False,
            "reason": f"Agent '{agent_name}' has NO permission for tool '{tool_name}'",
            "scopes": [],
            "source": "local",
        }

    # Check conditions
    for cond in tool_policy["conditions"]:
        passed, reason = _evaluate_condition(cond, params)
        if not passed:
            return {
                "allowed": False,
                "reason": reason,
                "scopes": tool_policy["scopes"],
                "source": "local",
            }

    return {
        "allowed": True,
        "reason": "Permitted by policy",
        "scopes": tool_policy["scopes"],
        "source": "local",
    }


def get_graph_stats() -> dict:
    """Get stats about the policy graph for display."""
    if NEO4J_ENABLED:
        with _driver.session() as session:
            result = session.run("""
                MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count
            """)
            nodes = {r["label"]: r["count"] for r in result}

            result2 = session.run("""
                MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count
            """)
            rels = {r["type"]: r["count"] for r in result2}

            return {"nodes": nodes, "relationships": rels, "source": "neo4j"}
    else:
        total_tools = sum(
            len(a["allowed_tools"]) for a in LOCAL_POLICIES.values()
        )
        return {
            "nodes": {
                "Agent": len(LOCAL_POLICIES),
                "Tool": 7,
                "DataScope": 5,
                "Condition": 5,
            },
            "relationships": {
                "CAN_USE": total_tools,
                "REQUIRES": 3,
                "ACCESSES": 8,
            },
            "source": "local_fallback",
        }


def get_policy_summary() -> list:
    """Get agent → allowed tools summary for showcase dashboard."""
    if NEO4J_ENABLED and _driver:
        try:
            with _driver.session() as session:
                result = session.run("""
                    MATCH (a:Agent)-[:CAN_USE]->(t:Tool)
                    RETURN a.name AS agent, collect(t.name) AS tools
                    ORDER BY a.name
                """)
                return [{"agent": r["agent"], "tools": r["tools"]} for r in result]
        except Exception:
            pass
    # Local fallback
    return [
        {"agent": agent, "tools": list(policy["allowed_tools"].keys())}
        for agent, policy in sorted(LOCAL_POLICIES.items())
    ]
