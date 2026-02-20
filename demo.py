"""
demo.py — Interactive demo runner for Agent Watch.
Walks through normal operation, then three attacks.
Includes 'before/after' comparison mode.

Usage: python demo.py
"""

# Load env first so Neo4j/Datadog/AWS are set before other modules read them
try:
    from dotenv import load_dotenv
    load_dotenv("env.example")
    load_dotenv()
except ImportError:
    pass

import time
import json
from agent_watch import handle_request, handle_request_unprotected
from attacks import (
    attack_prompt_injection,
    attack_data_exfiltration,
    attack_cost_spike,
    attack_subtle_social_engineering,
)
from metrics import local_metrics
from neo4j_client import get_graph_stats


def banner(text, char="═"):
    width = 70
    print(f"\n{char*width}")
    print(f"  {text}")
    print(f"{char*width}")


def pause(msg="Press Enter to continue..."):
    input(f"\n  ⏎  {msg}")


def print_result(result):
    status = result["status"]
    icons = {"OK": "✅", "BLOCKED": "🛑", "THROTTLED": "⚠️", "UNPROTECTED": "⚠️"}
    icon = icons.get(status, "❓")
    print(f"\n  {icon} Status: {status}")
    if result.get("reason"):
        print(f"  📋 Reason: {result['reason']}")
    if result.get("blocked_tools"):
        for bt in result["blocked_tools"]:
            print(f"  🔒 Blocked: {bt['name']} → {bt['reason']}")
    if result.get("behavior") and not result["behavior"].get("compliant", True):
        print(f"  🧠 Behavior issues:")
        for issue in result["behavior"].get("issues", []):
            print(f"     → {issue}")


def run_demo():
    banner("AGENT WATCH — LIVE DEMO", "█")
    print("""
  Three panels. Three attacks. Real-time monitoring.
  "Every agent needs an operator. We built the operator."
    """)

    # Clarify agent mode so it doesn't look hardcoded
    try:
        from toy_agent import BEDROCK_ENABLED
        if BEDROCK_ENABLED:
            print("  🤖 Agent: Bedrock (real LLM — model may actually comply with prompt injection)")
        else:
            print("  🤖 Agent: Mock (simulated tool calls for demo; policy checks are real)")
            print("     → Set AWS_ACCESS_KEY_ID for real LLM behavior; security/cost logic is unchanged.")
    except Exception:
        pass
    print()

    # Show graph stats
    stats = get_graph_stats()
    print(f"  📊 Policy Graph: {stats['source']}")
    for label, count in stats.get("nodes", {}).items():
        print(f"     {label}: {count} nodes")
    for rtype, count in stats.get("relationships", {}).items():
        print(f"     {rtype}: {count} relationships")

    # ──────────────────────────────────────────────
    # PHASE 0: Normal Operation
    # ──────────────────────────────────────────────
    pause("Press Enter to start: Normal Operation...")
    banner("PHASE 0: NORMAL OPERATION")
    print("  Showing a normal, legitimate request going through Agent Watch.\n")

    result = handle_request("What is user 12345's email address?")
    print_result(result)

    # ──────────────────────────────────────────────
    # PHASE 1: Attack 1 — Prompt Injection
    # ──────────────────────────────────────────────
    attack1 = attack_prompt_injection()
    pause(f"Press Enter to start Attack 1: {attack1['name']}...")
    banner(f"ATTACK 1: {attack1['name'].upper()}")
    print(f"  📖 {attack1['description']}")
    print(f"  📄 Research: {attack1['paper_reference']}")

    # Before: unprotected
    print(f"\n  --- WITHOUT Agent Watch ---")
    result_before = handle_request_unprotected(attack1["message"])
    print_result(result_before)

    pause("Now watch Agent Watch catch it...")

    # After: protected
    print(f"\n  --- WITH Agent Watch ---")
    result_after = handle_request(attack1["message"])
    print_result(result_after)

    # ──────────────────────────────────────────────
    # PHASE 2: Attack 2 — Data Exfiltration
    # ──────────────────────────────────────────────
    attack2 = attack_data_exfiltration()
    pause(f"Press Enter to start Attack 2: {attack2['name']}...")
    banner(f"ATTACK 2: {attack2['name'].upper()}")
    print(f"  📖 {attack2['description']}")
    print(f"  📄 Research: {attack2['paper_reference']}")

    # Before
    print(f"\n  --- WITHOUT Agent Watch ---")
    result_before = handle_request_unprotected(attack2["message"])
    print_result(result_before)

    pause("Now watch Agent Watch catch it...")

    # After
    print(f"\n  --- WITH Agent Watch ---")
    result_after = handle_request(attack2["message"])
    print_result(result_after)

    # ──────────────────────────────────────────────
    # PHASE 3: Attack 3 — Cost Spike
    # ──────────────────────────────────────────────
    attack3 = attack_cost_spike()
    pause(f"Press Enter to start Attack 3: {attack3['name']}...")
    banner(f"ATTACK 3: {attack3['name'].upper()}")
    print(f"  📖 {attack3['description']}")
    print(f"  📄 Research: {attack3['paper_reference']}")
    print(f"\n  Sending {len(attack3['messages'])} rapid requests...\n")

    throttled = False
    for i, msg in enumerate(attack3["messages"]):
        print(f"  [{i+1}/{len(attack3['messages'])}] \"{msg[:50]}...\"")
        result = handle_request(msg)
        if result["status"] == "THROTTLED":
            print(f"\n  ⚠️  THROTTLED after {i+1} requests!")
            print(f"  💰 Reason: {result['reason']}")
            throttled = True
            break
        time.sleep(0.1)

    if not throttled:
        print(f"\n  ℹ️  All requests completed (threshold not reached in mock mode)")
        print(f"  💡 With real Bedrock calls, cost would spike much faster")

    # ──────────────────────────────────────────────
    # PHASE 4: Bonus — Subtle Social Engineering
    # ──────────────────────────────────────────────
    attack4 = attack_subtle_social_engineering()
    pause(f"Press Enter for BONUS Attack: {attack4['name']}...")
    banner(f"BONUS: {attack4['name'].upper()}")
    print(f"  📖 {attack4['description']}")
    print(f"  📄 Research: {attack4['paper_reference']}")
    print(f"\n  This one sounds completely reasonable — but violates policy.\n")

    result = handle_request(attack4["message"])
    print_result(result)

    # ──────────────────────────────────────────────
    # TRY YOUR OWN (shows the pipeline isn't hardcoded)
    # ──────────────────────────────────────────────
    banner("TRY YOUR OWN MESSAGE (optional)")
    print("  Type any message and see it go through the same Agent Watch pipeline.")
    print("  Example: ask for user data, try to trigger a tool, or your own prompt injection.")
    print("  Press Enter with empty input to skip.\n")
    custom = input("  Your message: ").strip()
    if custom:
        print()
        result = handle_request(custom)
        print_result(result)
    else:
        print("  (skipped)")

    # ──────────────────────────────────────────────
    # SUMMARY
    # ──────────────────────────────────────────────
    banner("DEMO COMPLETE — SUMMARY", "█")

    summary = local_metrics.get_summary()
    print(f"\n  📊 Metrics Summary:")
    for name, value in sorted(summary["counters"].items()):
        print(f"     {name}: {value}")

    print(f"\n  🎯 Key Results:")
    blocked = summary["counters"].get("agent_watch.security.blocked", 0)
    allowed = summary["counters"].get("agent_watch.security.allowed", 0)
    drift = summary["counters"].get("agent_watch.behavior.drift_detected", 0)
    ok = summary["counters"].get("agent_watch.request.ok", 0)
    total_blocked = summary["counters"].get("agent_watch.request.blocked", 0)

    print(f"     Requests OK:       {ok}")
    print(f"     Requests Blocked:  {total_blocked}")
    print(f"     Security Blocks:   {blocked}")
    print(f"     Security Allows:   {allowed}")
    print(f"     Behavior Drifts:   {drift}")

    print(f"""
  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║   "Every agent needs an operator.                    ║
  ║    We built the operator."                           ║
  ║                                                      ║
  ╚══════════════════════════════════════════════════════╝
    """)


def run_single(message: str, agent: str = "support-agent"):
    """Run a single request through Agent Watch (for ad-hoc testing)."""
    result = handle_request(message, agent)
    print_result(result)
    return result


if __name__ == "__main__":
    run_demo()
