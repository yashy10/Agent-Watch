#!/usr/bin/env python3
"""
check_env.py — Verify which env vars are set (never prints values).
Run: python check_env.py
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Keys we care about, grouped by service
GROUPS = {
    "Neo4j": [
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "NEO4J_ACCEPT_SELF_SIGNED",
    ],
    "Datadog": [
        "DD_API_KEY",
        "DD_APP_KEY",
        "DD_SITE",
        "DD_LLMOBS_ENABLED",
        "DD_LLMOBS_ML_APP",
    ],
    "AWS (Bedrock)": [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "BEDROCK_MODEL_ID",
    ],
}

def main():
    print("\n  Agent Watch — Environment check")
    print("  " + "─" * 40)
    all_ok = True
    for group, keys in GROUPS.items():
        print(f"\n  {group}:")
        for key in keys:
            val = os.environ.get(key, "").strip()
            if val and val.lower() not in ("0", "false", "no"):
                print(f"    {key}: set")
            else:
                if key in ("NEO4J_ACCEPT_SELF_SIGNED", "DD_LLMOBS_ENABLED", "DD_LLMOBS_ML_APP", "DD_SITE", "BEDROCK_MODEL_ID"):
                    print(f"    {key}: not set (optional)")
                else:
                    print(f"    {key}: not set")
                    if key in ("NEO4J_URI", "NEO4J_PASSWORD", "DD_API_KEY", "DD_APP_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
                        all_ok = False
    print("\n  " + "─" * 40)
    if all_ok:
        print("  All required keys are set.")
    else:
        print("  Some required keys are missing. Add them to .env")
    print()

if __name__ == "__main__":
    main()
