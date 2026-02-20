"""
scripts/setup_datadog.py — Creates the Agent Watch dashboard in Datadog.
Uses the Datadog API to create a 3-panel dashboard programmatically.

Usage: python scripts/setup_datadog.py

Requires: DD_API_KEY and DD_APP_KEY environment variables
"""

import os
import sys
import json
import requests

API_KEY = os.environ.get("DD_API_KEY")
APP_KEY = os.environ.get("DD_APP_KEY")
SITE = os.environ.get("DD_SITE", "datadoghq.com")

if not API_KEY or not APP_KEY:
    print("Set DD_API_KEY and DD_APP_KEY environment variables")
    print("Get them from https://app.datadoghq.com/organization-settings/api-keys")
    sys.exit(1)

HEADERS = {
    "DD-API-KEY": API_KEY,
    "DD-APPLICATION-KEY": APP_KEY,
    "Content-Type": "application/json",
}

BASE_URL = f"https://api.{SITE}"

DASHBOARD = {
    "title": "🛡️ Agent Watch — Real-Time Agent Monitor",
    "description": "Security, behavior, and cost monitoring for AI agents in production",
    "layout_type": "ordered",
    "widgets": [
        # ── Row 1: Overview Stats ──
        {
            "definition": {
                "title": "🧠 Behavior Monitor",
                "type": "group",
                "layout_type": "ordered",
                "widgets": [
                    {
                        "definition": {
                            "title": "Behavior — Compliant vs Drift",
                            "type": "query_value",
                            "requests": [
                                {
                                    "q": "sum:agent_watch.behavior.compliant{*}.as_count()",
                                    "aggregator": "sum",
                                    "conditional_formats": [
                                        {"comparator": ">", "value": 0, "palette": "white_on_green"}
                                    ],
                                }
                            ],
                            "precision": 0,
                        }
                    },
                    {
                        "definition": {
                            "title": "Drift Detected",
                            "type": "query_value",
                            "requests": [
                                {
                                    "q": "sum:agent_watch.behavior.drift_detected{*}.as_count()",
                                    "aggregator": "sum",
                                    "conditional_formats": [
                                        {"comparator": ">", "value": 0, "palette": "white_on_red"},
                                        {"comparator": "<=", "value": 0, "palette": "white_on_green"},
                                    ],
                                }
                            ],
                            "precision": 0,
                        }
                    },
                    {
                        "definition": {
                            "title": "Behavior Over Time",
                            "type": "timeseries",
                            "requests": [
                                {
                                    "q": "sum:agent_watch.behavior.compliant{*}.as_count()",
                                    "display_type": "bars",
                                    "style": {"palette": "green"},
                                },
                                {
                                    "q": "sum:agent_watch.behavior.drift_detected{*}.as_count()",
                                    "display_type": "bars",
                                    "style": {"palette": "red"},
                                },
                            ],
                        }
                    },
                ],
            }
        },
        {
            "definition": {
                "title": "🔒 Security Monitor",
                "type": "group",
                "layout_type": "ordered",
                "widgets": [
                    {
                        "definition": {
                            "title": "Tool Calls Allowed",
                            "type": "query_value",
                            "requests": [
                                {
                                    "q": "sum:agent_watch.security.allowed{*}.as_count()",
                                    "aggregator": "sum",
                                    "conditional_formats": [
                                        {"comparator": ">=", "value": 0, "palette": "white_on_green"}
                                    ],
                                }
                            ],
                            "precision": 0,
                        }
                    },
                    {
                        "definition": {
                            "title": "Tool Calls BLOCKED",
                            "type": "query_value",
                            "requests": [
                                {
                                    "q": "sum:agent_watch.security.blocked{*}.as_count()",
                                    "aggregator": "sum",
                                    "conditional_formats": [
                                        {"comparator": ">", "value": 0, "palette": "white_on_red"},
                                        {"comparator": "<=", "value": 0, "palette": "white_on_green"},
                                    ],
                                }
                            ],
                            "precision": 0,
                        }
                    },
                    {
                        "definition": {
                            "title": "Security Events Over Time",
                            "type": "timeseries",
                            "requests": [
                                {
                                    "q": "sum:agent_watch.security.allowed{*}.as_count()",
                                    "display_type": "bars",
                                    "style": {"palette": "green"},
                                },
                                {
                                    "q": "sum:agent_watch.security.blocked{*}.as_count()",
                                    "display_type": "bars",
                                    "style": {"palette": "red"},
                                },
                            ],
                        }
                    },
                ],
            }
        },
        {
            "definition": {
                "title": "💰 Cost Monitor",
                "type": "group",
                "layout_type": "ordered",
                "widgets": [
                    {
                        "definition": {
                            "title": "Cost (Last 60s)",
                            "type": "query_value",
                            "requests": [
                                {
                                    "q": "avg:agent_watch.cost.last_60s{*}",
                                    "aggregator": "last",
                                    "conditional_formats": [
                                        {"comparator": ">", "value": 0.5, "palette": "white_on_red"},
                                        {"comparator": ">", "value": 0.1, "palette": "white_on_yellow"},
                                        {"comparator": "<=", "value": 0.1, "palette": "white_on_green"},
                                    ],
                                }
                            ],
                            "precision": 6,
                            "custom_unit": "$",
                        }
                    },
                    {
                        "definition": {
                            "title": "Token Usage",
                            "type": "query_value",
                            "requests": [
                                {
                                    "q": "avg:agent_watch.cost.total_tokens{*}",
                                    "aggregator": "last",
                                }
                            ],
                            "precision": 0,
                        }
                    },
                    {
                        "definition": {
                            "title": "Cost Per Call Over Time",
                            "type": "timeseries",
                            "requests": [
                                {
                                    "q": "avg:agent_watch.cost.per_call{*}",
                                    "display_type": "line",
                                    "style": {"palette": "orange"},
                                },
                            ],
                        }
                    },
                ],
            }
        },
        # ── Row 2: Aggregate Views ──
        {
            "definition": {
                "title": "Request Outcomes",
                "type": "timeseries",
                "requests": [
                    {
                        "q": "sum:agent_watch.request.ok{*}.as_count()",
                        "display_type": "bars",
                        "style": {"palette": "green"},
                    },
                    {
                        "q": "sum:agent_watch.request.blocked{*}.as_count()",
                        "display_type": "bars",
                        "style": {"palette": "red"},
                    },
                    {
                        "q": "sum:agent_watch.request.throttled{*}.as_count()",
                        "display_type": "bars",
                        "style": {"palette": "yellow"},
                    },
                ],
            }
        },
        {
            "definition": {
                "title": "Threshold Breaches",
                "type": "query_value",
                "requests": [
                    {
                        "q": "sum:agent_watch.cost.threshold_exceeded{*}.as_count()",
                        "aggregator": "sum",
                        "conditional_formats": [
                            {"comparator": ">", "value": 0, "palette": "white_on_red"},
                            {"comparator": "<=", "value": 0, "palette": "white_on_green"},
                        ],
                    }
                ],
                "precision": 0,
            }
        },
    ],
}


def create_dashboard():
    print("📊 Creating Agent Watch dashboard in Datadog...")
    url = f"{BASE_URL}/api/v1/dashboard"
    resp = requests.post(url, headers=HEADERS, json=DASHBOARD)

    if resp.status_code == 200:
        data = resp.json()
        dashboard_url = data.get("url", "")
        full_url = f"https://app.{SITE}{dashboard_url}"
        print(f"\n  ✅ Dashboard created!")
        print(f"  🔗 URL: {full_url}")
        print(f"  📋 ID: {data.get('id', 'unknown')}")
        return data
    else:
        print(f"\n  ❌ Failed: {resp.status_code}")
        print(f"  {resp.text[:500]}")
        return None


def create_monitors():
    """Create Datadog monitors for alerting."""
    print("\n📢 Creating monitors...")

    monitors = [
        {
            "name": "Agent Watch — Security Block Detected",
            "type": "metric alert",
            "query": "sum(last_5m):sum:agent_watch.security.blocked{*}.as_count() > 0",
            "message": "🛑 Agent Watch detected a blocked security event!\n\nA tool call was blocked by the policy graph. Check the Agent Watch dashboard for details.",
            "priority": 2,
        },
        {
            "name": "Agent Watch — Behavior Drift Detected",
            "type": "metric alert",
            "query": "sum(last_5m):sum:agent_watch.behavior.drift_detected{*}.as_count() > 0",
            "message": "🧠 Agent Watch detected behavior drift!\n\nThe agent's response deviated from expected behavior. Review in the Agent Watch dashboard.",
            "priority": 2,
        },
        {
            "name": "Agent Watch — Cost Threshold Exceeded",
            "type": "metric alert",
            "query": "avg(last_1m):avg:agent_watch.cost.last_60s{*} > 0.5",
            "message": "💰 Agent Watch: Cost threshold exceeded!\n\nAgent spending has exceeded $0.50/min. Auto-throttling may be active.",
            "priority": 1,
        },
    ]

    url = f"{BASE_URL}/api/v1/monitor"
    for m in monitors:
        resp = requests.post(url, headers=HEADERS, json=m)
        if resp.status_code == 200:
            print(f"  ✅ Monitor created: {m['name']}")
        else:
            print(f"  ⚠️  Monitor failed: {m['name']} ({resp.status_code})")


if __name__ == "__main__":
    create_dashboard()
    create_monitors()
    print("\n🎉 Datadog setup complete!")
