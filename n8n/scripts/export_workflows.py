#!/usr/bin/env python3
"""Export every n8n workflow to n8n/workflows/<id>__<slug>.json via the n8n public API.

Needs N8N_BASE_URL and N8N_API_KEY in the environment (see .env.example).
Workflow JSON holds credential *IDs*, not secrets. Pinned test data is stripped because it
can contain real borrower records.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

BASE = os.environ.get("N8N_BASE_URL", "").rstrip("/")
KEY = os.environ.get("N8N_API_KEY")
OUT = Path(__file__).resolve().parent.parent / "workflows"
VOLATILE = ("updatedAt", "createdAt", "pinData", "staticData", "shared", "meta")

if not BASE or not KEY:
    sys.exit("Set N8N_BASE_URL and N8N_API_KEY first (see .env.example).")


def get(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}/api/v1{path}", headers={"X-N8N-API-KEY": KEY})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cursor, count = None, 0
    while True:
        page = get("/workflows?limit=100" + (f"&cursor={cursor}" if cursor else ""))
        for wf in page.get("data", []):
            for k in VOLATILE:
                wf.pop(k, None)
            path = OUT / f"{wf['id']}__{slug(wf.get('name', 'workflow'))}.json"
            path.write_text(json.dumps(wf, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                            encoding="utf-8")
            count += 1
        cursor = page.get("nextCursor")
        if not cursor:
            break
    print(f"Exported {count} workflows to {OUT}")


if __name__ == "__main__":
    main()
