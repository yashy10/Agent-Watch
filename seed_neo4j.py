"""
scripts/seed_neo4j.py — Seeds the Neo4j policy graph.
Run this once to populate the graph with agents, tools, permissions, etc.

Usage: python scripts/seed_neo4j.py
"""

import os
import sys

try:
    from neo4j import GraphDatabase
except ImportError:
    print("Install neo4j: pip install neo4j")
    sys.exit(1)

URI = os.environ.get("NEO4J_URI", "").strip()
USER = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME") or "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD")

if not URI or not PASSWORD:
    print("Set NEO4J_URI and NEO4J_PASSWORD environment variables")
    print("Get a free instance at https://neo4j.com/cloud/aura-free/")
    sys.exit(1)

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

SEED_QUERY = """
// ── Clear existing data ──
MATCH (n) DETACH DELETE n;
"""

CREATE_QUERY = """
// ══════════════════════════════════════════════
// AGENT WATCH — Policy Graph
// ══════════════════════════════════════════════

// ── Agents ──
CREATE (sa:Agent {name: "support-agent", role: "customer_support", risk_level: "medium", description: "Handles customer inquiries and support tickets"})
CREATE (aa:Agent {name: "admin-agent", role: "admin", risk_level: "high", description: "System administration and configuration"})
CREATE (da:Agent {name: "data-agent", role: "analytics", risk_level: "low", description: "Read-only data analysis and reporting"})

// ── Tools ──
CREATE (t1:Tool {name: "get_user_data", category: "read", sensitivity: "medium", description: "Fetch user profile by ID"})
CREATE (t2:Tool {name: "send_email", category: "write", sensitivity: "high", description: "Send email to a user"})
CREATE (t3:Tool {name: "query_database", category: "read", sensitivity: "high", description: "Run SQL queries"})
CREATE (t4:Tool {name: "update_config", category: "admin", sensitivity: "critical", description: "Modify system configuration"})
CREATE (t5:Tool {name: "search_knowledge_base", category: "read", sensitivity: "low", description: "Search help articles"})
CREATE (t6:Tool {name: "create_ticket", category: "write", sensitivity: "low", description: "Create support ticket"})
CREATE (t7:Tool {name: "export_data", category: "write", sensitivity: "critical", description: "Export data to files"})

// ── Data Scopes ──
CREATE (d1:DataScope {name: "user_profiles", classification: "PII", description: "User personal information"})
CREATE (d2:DataScope {name: "support_tickets", classification: "internal", description: "Support ticket data"})
CREATE (d3:DataScope {name: "financial_records", classification: "restricted", description: "Billing and payment data"})
CREATE (d4:DataScope {name: "system_config", classification: "critical", description: "System configuration values"})
CREATE (d5:DataScope {name: "knowledge_base", classification: "public", description: "Help articles and documentation"})

// ── Conditions ──
CREATE (c1:Condition {rule: "email_internal_only", description: "Emails can only be sent to @company.com addresses"})
CREATE (c2:Condition {rule: "read_only_queries", description: "No DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE"})
CREATE (c3:Condition {rule: "no_config_modification", description: "System config changes are blocked"})
CREATE (c4:Condition {rule: "no_pii_export", description: "Cannot export PII data externally"})
CREATE (c5:Condition {rule: "rate_limit_10_per_min", description: "Maximum 10 calls per minute"})

// ── Actions (what happens on violation) ──
CREATE (a1:Action {type: "block", severity: "high", notify: true, description: "Block the action and alert"})
CREATE (a2:Action {type: "alert", severity: "medium", notify: true, description: "Allow but send alert"})
CREATE (a3:Action {type: "throttle", severity: "low", notify: false, description: "Throttle request rate"})
CREATE (a4:Action {type: "log_only", severity: "info", notify: false, description: "Log for audit only"})

// ══════════════════════════════════════════════
// PERMISSIONS: support-agent
// ══════════════════════════════════════════════
CREATE (sa)-[:CAN_USE {max_calls_per_min: 20, granted_by: "default_policy"}]->(t1)
CREATE (sa)-[:CAN_USE {max_calls_per_min: 5, granted_by: "default_policy"}]->(t2)
CREATE (sa)-[:CAN_USE {max_calls_per_min: 10, granted_by: "default_policy"}]->(t3)
CREATE (sa)-[:CAN_USE {max_calls_per_min: 50, granted_by: "default_policy"}]->(t5)
CREATE (sa)-[:CAN_USE {max_calls_per_min: 10, granted_by: "default_policy"}]->(t6)
// NOTE: support-agent has NO access to t4 (update_config) or t7 (export_data)

// ══════════════════════════════════════════════
// PERMISSIONS: admin-agent
// ══════════════════════════════════════════════
CREATE (aa)-[:CAN_USE {max_calls_per_min: 50}]->(t1)
CREATE (aa)-[:CAN_USE {max_calls_per_min: 20}]->(t2)
CREATE (aa)-[:CAN_USE {max_calls_per_min: 50}]->(t3)
CREATE (aa)-[:CAN_USE {max_calls_per_min: 5}]->(t4)
CREATE (aa)-[:CAN_USE {max_calls_per_min: 50}]->(t5)
CREATE (aa)-[:CAN_USE {max_calls_per_min: 20}]->(t6)
CREATE (aa)-[:CAN_USE {max_calls_per_min: 2}]->(t7)

// ══════════════════════════════════════════════
// PERMISSIONS: data-agent (read-only)
// ══════════════════════════════════════════════
CREATE (da)-[:CAN_USE {max_calls_per_min: 30}]->(t1)
CREATE (da)-[:CAN_USE {max_calls_per_min: 30}]->(t3)
CREATE (da)-[:CAN_USE {max_calls_per_min: 100}]->(t5)

// ══════════════════════════════════════════════
// TOOL → DATA SCOPE MAPPINGS
// ══════════════════════════════════════════════
CREATE (t1)-[:ACCESSES]->(d1)
CREATE (t2)-[:ACCESSES]->(d1)
CREATE (t3)-[:ACCESSES]->(d2)
CREATE (t3)-[:ACCESSES]->(d3)
CREATE (t4)-[:ACCESSES]->(d4)
CREATE (t5)-[:ACCESSES]->(d5)
CREATE (t6)-[:ACCESSES]->(d2)
CREATE (t7)-[:ACCESSES]->(d1)
CREATE (t7)-[:ACCESSES]->(d3)

// ══════════════════════════════════════════════
// CONDITIONS ON PERMISSIONS
// ══════════════════════════════════════════════

// support-agent email must be internal only
MATCH (sa:Agent {name:"support-agent"})-[p:CAN_USE]->(t2:Tool {name:"send_email"})
CREATE (p)-[:REQUIRES]->(c1)

// support-agent queries must be read-only
MATCH (sa:Agent {name:"support-agent"})-[p:CAN_USE]->(t3:Tool {name:"query_database"})
CREATE (p)-[:REQUIRES]->(c2)

// admin-agent data exports cannot include PII
MATCH (aa:Agent {name:"admin-agent"})-[p:CAN_USE]->(t7:Tool {name:"export_data"})
CREATE (p)-[:REQUIRES]->(c4)

// ══════════════════════════════════════════════
// VIOLATION → ACTION MAPPINGS
// ══════════════════════════════════════════════
CREATE (c1)-[:ON_VIOLATION]->(a1)
CREATE (c2)-[:ON_VIOLATION]->(a1)
CREATE (c3)-[:ON_VIOLATION]->(a1)
CREATE (c4)-[:ON_VIOLATION]->(a1)
CREATE (c5)-[:ON_VIOLATION]->(a3)

// ══════════════════════════════════════════════
// INCIDENT TRACKING (template — populated at runtime)
// ══════════════════════════════════════════════
CREATE (i_template:IncidentTemplate {
    description: "Runtime incidents are created as Incident nodes linked to the violating Agent, Tool, and Condition",
    fields: "timestamp, agent_name, tool_name, violation_type, severity, resolved"
})
"""


def seed():
    print("🌱 Seeding Neo4j policy graph...")
    with driver.session() as session:
        # Clear
        session.run(SEED_QUERY)
        print("   Cleared existing data")

        # Create
        session.run(CREATE_QUERY)
        print("   Created policy graph")

        # Verify
        result = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count")
        print("\n   📊 Graph contents:")
        total_nodes = 0
        for record in result:
            print(f"      {record['label']}: {record['count']}")
            total_nodes += record['count']

        result2 = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count")
        total_rels = 0
        print()
        for record in result2:
            print(f"      {record['type']}: {record['count']}")
            total_rels += record['count']

        print(f"\n   ✅ Total: {total_nodes} nodes, {total_rels} relationships")

    driver.close()
    print("\n🎉 Policy graph seeded successfully!")


if __name__ == "__main__":
    seed()
