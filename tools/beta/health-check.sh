#!/usr/bin/env bash
# =============================================================================
# health-check.sh — post-deploy / post-rollback health gate (briq-09b, area 54)
#
#   tools/beta/health-check.sh                 # on the phone (root=/)
#   tools/beta/health-check.sh --root DIR      # offline against a fixture tree
#   tools/beta/health-check.sh --json FILE     # machine-readable report
#   tools/beta/health-check.sh --quiet
#
# Exit 0 = HEALTHY, 1 = UNHEALTHY, 2 = usage/guard error.
#
# WHAT "HEALTHY" MEANS
#   On device: every Nuxel stack unit is active, `systemctl --failed` is empty,
#   the framebuffer owner record exists and its PID is alive, and the launcher
#   answers 200 on 127.0.0.1:8000.  That is a *service* health gate — it is not
#   proof that any hardware works (touch, audio, radios all need their own
#   owner-proof steps; see the manual proof checklist).
#   Offline (--root DIR): the same checks run against a recorded/fixture tree
#   and are reported as advisory; the verdict is OFFLINE_TESTED at best.
#
# SAFETY  never reboots, never starts/stops a service, never writes to a block
#         device, never touches .qq/, never writes receipt JSON.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT_TREE=""
JSON_OUT=""
QUIET=0
PY="${HEALTH_PY:-python3}"

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --root)  ROOT_TREE="$2"; shift 2 ;;
    --json)  JSON_OUT="$2"; shift 2 ;;
    --quiet|-q) QUIET=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "health-check: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$ROOT_TREE" in
  *"/.qq/"*|*"/.qq"|*"/.codeseeq/"*)
    echo "health-check: REFUSING to treat QonQrete metadata as a root: $ROOT_TREE" >&2
    exit 2 ;;
esac
[ -n "$ROOT_TREE" ] || ROOT_TREE="/"

tmp="$(mktemp "${TMPDIR:-/tmp}/nuxel-health-XXXXXX")"
trap 'rm -f "$tmp"' EXIT
rc=0
"$PY" "$HERE/release_lib.py" health --root "$ROOT_TREE" --json "$tmp" >/dev/null 2>&1 || rc=$?
if [ ! -s "$tmp" ]; then
  echo "health-check: internal error (release_lib.py produced no report)" >&2
  exit 2
fi
if [ -n "$JSON_OUT" ]; then
  mkdir -p "$(dirname "$JSON_OUT")"
  cp "$tmp" "$JSON_OUT"
fi
if [ "$QUIET" -eq 0 ]; then
  "$PY" - "$tmp" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print("=== Nuxel health check ===  root=%s  tier=%s" % (d["root"], d["tier"]))
for c in d["checks"]:
    mark = "ok  " if c["ok"] else ("FAIL" if c["level"] == "hard" else "warn")
    print("  [%s] %-24s %s" % (mark, c["id"], c["detail"]))
print("verdict: %s%s" % (d["verdict"],
      ("  (hard failures: %s)" % ", ".join(d["hard_failures"])) if d["hard_failures"] else ""))
print("note: %s" % d["note"])
PY
fi
exit "$rc"
