#!/usr/bin/env python3
"""Extract text from AgentWatch_Blueprint.pdf. Run: pip install pypdf && python blueprint_extract.py"""
try:
    from pypdf import PdfReader
except ImportError:
    print("Run: pip install pypdf")
    exit(1)

r = PdfReader("AgentWatch_Blueprint.pdf")
with open("AgentWatch_Blueprint.txt", "w") as f:
    for i, p in enumerate(r.pages):
        t = p.extract_text()
        if t:
            f.write(f"\n--- Page {i+1} ---\n\n")
            f.write(t)
            f.write("\n")
print("Wrote AgentWatch_Blueprint.txt")
