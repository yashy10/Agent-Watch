#!/usr/bin/env python3
"""Quick check: is Datadog configured and working?"""
import os

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv("env.example")
    load_dotenv()
except ImportError:
    pass

print("Datadog config:")
print("  DD_API_KEY:", "set (" + os.environ.get("DD_API_KEY", "")[:10] + "...)" if os.environ.get("DD_API_KEY") else "NOT SET")
print("  DD_APP_KEY:", "set" if os.environ.get("DD_APP_KEY") else "NOT SET")
print("  DD_SITE:   ", os.environ.get("DD_SITE", "datadoghq.com"))
print()

# Import metrics (this initializes Datadog if DD_API_KEY is set)
import metrics

if metrics.DD_ENABLED:
    print("[metrics] Datadog enabled")
    if metrics.statsd:
        try:
            metrics.statsd.increment("agent_watch.check.ping", 1)
            print("  Test metric sent: agent_watch.check.ping")
        except Exception as e:
            print("  Test metric error:", e)
    print("\nDatadog is WORKING.")
else:
    print("[metrics] Datadog NOT active — using local logging")
    print("\nTo enable Datadog:")
    print("  1. Put your DD_API_KEY and DD_APP_KEY in env.example or .env")
    print("  2. Save the file and run this script again.")
