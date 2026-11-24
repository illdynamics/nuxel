#!/usr/bin/env bash
# Generate a machine-readable JSON receipt for the native radio host suite.
# Authoritative source is recorded (git HEAD + source file SHA-256s); host
# PASS is explicitly marked as not establishing any physical layer.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="${1:-$ROOT/reports/S5000AP-07-HOST-TEST-RECEIPT.json}"

cd "$ROOT"
HEAD="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
BRANCH="$(git branch --show-current 2>/dev/null || echo unknown)"
CLEAN="$([ -z "$(git status --porcelain)" ] && echo clean || echo dirty)"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

declare -a SRC_FILES
while IFS= read -r f; do SRC_FILES+=("$f"); done < <(cd "$HERE/src" && find . -name '*.c' -o -name '*.h' | sort)

src_hashes="{}"
SRCJSON="$HERE/.src-hashes.tmp.json"
{
  echo "{"
  first=1
  for f in "${SRC_FILES[@]}"; do
    h="$(shasum -a 256 "$HERE/src/${f#./}" | awk '{print $1}')"
    [ $first -eq 1 ] && first=0 || echo ","
    printf '  "%s": "%s"' "$f" "$h"
  done
  echo ""
  echo "}"
} > "$SRCJSON"
src_hashes="$(cat "$SRCJSON")"
rm -f "$SRCJSON"

# Run the suite and capture the tail.
set +e
SUITE_LOG="$(mktemp)"
"$HERE/build.sh" >"$SUITE_LOG" 2>&1
SUITE_RC=$?
set -e
SUITE_TAIL="$(tail -n 3 "$SUITE_LOG" | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g' | cut -c1-300)"
rm -f "$SUITE_LOG"

# Phone app offline acceptance.
set +e
APP_LOG="$(mktemp)"
python3 "$ROOT/tools/s10plus/a33/tests/test-phone-apps.py" >"$APP_LOG" 2>&1
APP_RC=$?
set -e
APP_TAIL="$(grep 'RESULT:' "$APP_LOG" | tail -1)"
rm -f "$APP_LOG"

python3 - "$HEAD" "$BRANCH" "$CLEAN" "$NOW" "$SUITE_RC" "$SUITE_TAIL" "$APP_RC" "$APP_TAIL" "$src_hashes" "$OUT" <<'PYEOF'
import json, sys
head, branch, clean, now, suite_rc, suite_tail, app_rc, app_tail, src_hashes, out = sys.argv[1:11]
receipt = {
  "schema": "s5000ap-07-host-test-receipt-v1",
  "generated": now,
  "authoritative_source": {
    "git_head": head,
    "git_branch": branch,
    "tree_state": clean,
    "suite_script": "tools/s10plus/s5000ap-05/build.sh",
    "app_test": "tools/s10plus/a33/tests/test-phone-apps.py",
    "source_file_sha256": json.loads(src_hashes),
  },
  "results": {
    "radio_host_suite": {
      "exit": int(suite_rc),
      "status": "PASS" if int(suite_rc) == 0 else "FAIL",
      "tail": suite_tail,
    },
    "phone_app_offline_acceptance": {
      "exit": int(app_rc),
      "status": "PASS" if int(app_rc) == 0 else "FAIL",
      "summary": app_tail,
    },
  },
  "honesty": {
    "host_pass_establishes_physical_layer": False,
    "note": "Host PASS validates source/parsers/FSM only. Physical SMS/voice/IMS remain owner-gated and are NOT claimed by this receipt.",
  },
}
with open(out, "w") as f:
    json.dump(receipt, f, indent=2, sort_keys=True)
    f.write("\n")
print("wrote", out)
PYEOF
