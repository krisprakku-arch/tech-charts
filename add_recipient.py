"""Add one recipient to TECH_CHART_TO in the pipeline .env (usage: add_recipient.py <email>)."""
import sys
from pathlib import Path

ENV = Path("/Users/kris/Desktop/Invetement Intelligence/Investment_Intelligence/.env")

def main():
    email = sys.argv[1].strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        print("INVALID_EMAIL")
        raise SystemExit(1)
    lines = ENV.read_text().splitlines()
    tos = []
    for l in lines:
        if l.startswith("TECH_CHART_TO="):
            tos = [a.strip() for a in l.split("=", 1)[1].split(",") if a.strip()]
    if email not in tos:
        tos.append(email)
        out = [l for l in lines if not l.startswith("TECH_CHART_TO=")]
        out.append("TECH_CHART_TO=" + ",".join(tos))
        ENV.write_text("\n".join(out) + "\n")
        print("ADDED")
    else:
        print("ALREADY_PRESENT")
    print("count =", len(tos))

main()
