#!/usr/bin/env python3
"""
quickstart.py — One-command setup and test for Agent Watch.
Verifies all components work and runs a quick smoke test.

Usage: python quickstart.py
"""

import sys
import os

def check(name, test_fn):
    try:
        result = test_fn()
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ⚠️  {name}: {e}")
        return False

def main():
    print("\n🛡️  Agent Watch — Quick Start\n")

    # ── Check dependencies ──
    print("Checking dependencies...")
    check("FastAPI", lambda: __import__("fastapi"))
    check("Uvicorn", lambda: __import__("uvicorn"))
    check("Requests", lambda: __import__("requests"))

    has_boto = check("Boto3 (AWS)", lambda: __import__("boto3"))
    has_neo4j = check("Neo4j driver", lambda: __import__("neo4j"))
    has_dd = check("Datadog", lambda: __import__("datadog"))

    # ── Check env vars ──
    print("\nChecking configuration...")
    aws_ok = bool(os.environ.get("AWS_ACCESS_KEY_ID"))
    neo4j_ok = bool(os.environ.get("NEO4J_URI"))
    dd_ok = bool(os.environ.get("DD_API_KEY"))

    print(f"  {'✅' if aws_ok else '⚠️ '} AWS credentials {'configured' if aws_ok else 'NOT set — using mock LLM'}")
    print(f"  {'✅' if neo4j_ok else '⚠️ '} Neo4j {'configured' if neo4j_ok else 'NOT set — using local policy'}")
    print(f"  {'✅' if dd_ok else '⚠️ '} Datadog {'configured' if dd_ok else 'NOT set — using local metrics'}")

    if not aws_ok and not neo4j_ok and not dd_ok:
        print("\n  ℹ️  Running in full local/mock mode — all features work!")
        print("  ℹ️  Add credentials to .env for real integrations.")

    # ── Smoke test ──
    print("\nRunning smoke test...")
    from agent_watch import handle_request, handle_request_unprotected
    from attacks import attack_prompt_injection, attack_data_exfiltration

    # Normal request
    r = handle_request("What is user 12345's email?")
    assert r["status"] == "OK", f"Normal request failed: {r['status']}"
    print("  ✅ Normal request: OK")

    # Prompt injection
    a = attack_prompt_injection()
    r = handle_request(a["message"])
    assert r["status"] == "BLOCKED", f"Injection not blocked: {r['status']}"
    print("  ✅ Prompt injection: BLOCKED")

    # Data exfiltration
    a = attack_data_exfiltration()
    r = handle_request(a["message"])
    assert r["status"] == "BLOCKED", f"Exfiltration not blocked: {r['status']}"
    print("  ✅ Data exfiltration: BLOCKED")

    # Unprotected mode
    a = attack_prompt_injection()
    r = handle_request_unprotected(a["message"])
    assert r["status"] == "UNPROTECTED"
    print("  ✅ Unprotected mode: tools executed without checks")

    print(f"""
{'='*60}
  ✅ ALL CHECKS PASSED — Agent Watch is ready!

  Next steps:
    1. Run the demo:     python demo.py
    2. Start the server: python server.py
       then open:        http://localhost:8000
    3. API demo:         python demo_api.py (while server is running)

  For the hackathon:
    1. Set up Neo4j:     python scripts/seed_neo4j.py
    2. Set up Datadog:   python scripts/setup_datadog.py
    3. Run server:       python server.py
    4. Run demo:         python demo_api.py
{'='*60}
""")


if __name__ == "__main__":
    main()
