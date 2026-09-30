#!/usr/bin/env bash
# Offline: turns the files fetched by fetch.sh into AUTOMATION_INVENTORY.md.
# Usage: ./run.sh <workDir> <output.md>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?usage: run.sh <workDir> <output.md>}"
OUT="${2:?usage: run.sh <workDir> <output.md>}"
[ -d "$HERE/node_modules/fast-xml-parser" ] || (cd "$HERE" && npm install --silent)
node "$HERE/analyze-flows.js" "$WORK"
node "$HERE/analyze-rules.js" "$WORK" > /dev/null
node "$HERE/render.js" "$WORK"
node "$HERE/assemble.js" "$WORK" "$OUT"
