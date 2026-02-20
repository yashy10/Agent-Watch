#!/usr/bin/env python3
"""Print the exact Neo4j connection error. Run: python check_neo4j_connection.py"""
import os

# Load .env so we use your real credentials
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv("env.example")
except ImportError:
    pass

uri = os.environ.get("NEO4J_URI", "").strip()
if os.environ.get("NEO4J_ACCEPT_SELF_SIGNED", "").lower() in ("1", "true", "yes"):
    uri = uri.replace("neo4j+s://", "neo4j+ssc://", 1)
user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME") or "neo4j"
password = os.environ.get("NEO4J_PASSWORD")

print("NEO4J_URI:", uri or "(not set)")
print("NEO4J_USER/USERNAME:", user)
print("NEO4J_PASSWORD:", "***" if password else "(not set)")
print()

if not uri or not password:
    print("Set NEO4J_URI and NEO4J_PASSWORD in .env")
    exit(1)

print("Attempting connection...")
try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        session.run("RETURN 1")
    print("OK — connected.")
    driver.close()
except Exception as e:
    print("EXACT ERROR:")
    print("  Type:", type(e).__name__)
    print("  Message:", str(e))
    tb_str = "".join(__import__("traceback").format_exception(type(e), e, e.__traceback__))
    if "certificate" in tb_str.lower() or "ssl" in tb_str.lower() or "CERTIFICATE_VERIFY_FAILED" in tb_str:
        print()
        print("FIX: SSL cert verify failed (common on macOS/Python 3.14). In .env add:")
        print("     NEO4J_ACCEPT_SELF_SIGNED=1")
        print("  Or set URI to neo4j+ssc://... instead of neo4j+s://...")
    print()
    import traceback
    print("Full traceback:")
    traceback.print_exc()
