"""
mock_tools.py — Simulated tool execution for the toy agent.
These fake tools let us demo without real DBs, email servers, etc.
"""

import random
import time

# Fake user database
USERS = {
    "12345": {
        "name": "Alice Johnson",
        "email": "alice@company.com",
        "role": "engineer",
        "ssn": "***-**-1234",
        "phone": "555-0101",
    },
    "67890": {
        "name": "Bob Smith",
        "email": "bob@company.com",
        "role": "manager",
        "ssn": "***-**-5678",
        "phone": "555-0202",
    },
}


def execute_tool(tool_name: str, params: dict) -> dict:
    """Execute a mock tool and return results."""
    executors = {
        "get_user_data": _get_user_data,
        "send_email": _send_email,
        "query_database": _query_database,
        "update_config": _update_config,
        "search_knowledge_base": _search_kb,
        "create_ticket": _create_ticket,
        "export_data": _export_data,
    }

    executor = executors.get(tool_name)
    if not executor:
        return {"error": f"Unknown tool: {tool_name}"}

    # Simulate slight latency
    time.sleep(random.uniform(0.05, 0.15))
    return executor(params)


def _get_user_data(params):
    user_id = params.get("user_id", "")
    user = USERS.get(user_id)
    if user:
        return {"success": True, "data": user}
    return {"success": False, "error": f"User {user_id} not found"}


def _send_email(params):
    to = params.get("to", "")
    subject = params.get("subject", "")
    body = params.get("body", "")
    return {
        "success": True,
        "message": f"Email sent to {to}",
        "subject": subject,
        "preview": body[:100],
    }


def _query_database(params):
    query = params.get("query", "")
    # Return fake results
    return {
        "success": True,
        "rows": [
            {"id": 1, "name": "Sample Row", "value": "data"},
            {"id": 2, "name": "Another Row", "value": "more_data"},
        ],
        "query_executed": query,
    }


def _update_config(params):
    key = params.get("key", "")
    value = params.get("value", "")
    return {
        "success": True,
        "message": f"Config '{key}' updated to '{value}'",
    }


def _search_kb(params):
    query = params.get("query", "")
    return {
        "success": True,
        "results": [
            {"title": "How to reset password", "relevance": 0.95},
            {"title": "Account setup guide", "relevance": 0.82},
        ],
    }


def _create_ticket(params):
    return {
        "success": True,
        "ticket_id": f"TKT-{random.randint(1000, 9999)}",
        "status": "created",
    }


def _export_data(params):
    return {
        "success": True,
        "message": "Data exported",
        "records_exported": random.randint(100, 5000),
    }
