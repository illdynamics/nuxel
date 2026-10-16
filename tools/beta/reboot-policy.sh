#!/usr/bin/env bash
# =============================================================================
# reboot-policy.sh — the autonomous reboot policy and its checklists (briq-09b)
#
#   tools/beta/reboot-policy.sh status
#   tools/beta/reboot-policy.sh check --reason R --diagnostic D [--mode M]
#   tools/beta/reboot-policy.sh record --reason R --diagnostic D --returned-to-nuxel yes
#   tools/beta/reboot-policy.sh failure --mode M --note "what was tried"
#   tools/beta/reboot-policy.sh pre  [--run]      # pre-reboot checklist
#   tools/beta/reboot-policy.sh post [--run]      # post-reboot checklist
#   tools/beta/reboot-policy.sh reboot --reason R --diagnostic D [--execute --confirm]
#   tools/beta/reboot-policy.sh selftest
#
# THE POLICY (area 53) — reboots are allowed, blind reboots are not:
#   * hard budget: at most 3 reboots per cycle (POLICY.max_reboots);
#   * the previous reboot must have RETURNED TO NUXEL (console reconnected and
#     answered a framed command) before another one is permitted;
#   * every reboot needs a stated reason AND a *different* diagnostic than the
#     previous one — a repeat is refused as a blind repeat;
#   * a known-good userspace rollback must exist (tools/beta/rollback.sh status);
#   * the three-same-mode-failure rule is an automated guard: after three
#     failures in the same diagnostic mode the policy refuses further reboots in
#     that mode and demands a changed strategy.
#
# `reboot` is the ONLY place a reboot could ever be issued, and it refuses
# unless BOTH (a) `--execute --confirm` are given and (b) the live USB console is
# actually reachable.  In this repository-first run there is no owner and no live
# console, so the command reports the exact command to run and exits 3
# (BLOCKED_EXTERNAL_RESOURCE) — it never reboots the phone by itself.
#
# SAFETY  never flashes, never writes to a block device, never touches .qq/ or a
#         QonQrete RUN_ROOT, never writes receipt JSON into the workspace.
#
# EXIT  0 allowed/ok · 1 denied · 2 usage/guard · 3 blocked external resource
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$HERE/../.." && pwd)"
LIB="$HERE/release_lib.py"
PY="${REBOOT_PY:-python3}"
REACHABILITY="$HERE/live/nuxel-live-reachability.py"

CMD=""
REASON=""
DIAGNOSTIC=""
MODE=""
NOTE=""
RETURNED="no"
EVIDENCE_BEFORE=""
EVIDENCE_AFTER=""
STATE_FILE=""
ROOT_DIR="/"
RUN=0
EXECUTE=0
CONFIRM=0
QUIET=0

usage() { sed -n '2,34p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    status|check|record|failure|pre|post|reboot|selftest|policy) CMD="$1"; shift ;;
    --reason)          REASON="$2"; shift 2 ;;
    --diagnostic)      DIAGNOSTIC="$2"; shift 2 ;;
    --mode)            MODE="$2"; shift 2 ;;
    --note)            NOTE="$2"; shift 2 ;;
    --returned-to-nuxel) RETURNED="$2"; shift 2 ;;
    --evidence-before) EVIDENCE_BEFORE="$2"; shift 2 ;;
    --evidence-after)  EVIDENCE_AFTER="$2"; shift 2 ;;
    --state)           STATE_FILE="$2"; shift 2 ;;
    --root)            ROOT_DIR="$2"; shift 2 ;;
    --run)             RUN=1; shift ;;
    --execute)         EXECUTE=1; shift ;;
    --confirm)         CONFIRM=1; shift ;;
    --quiet|-q)        QUIET=1; shift ;;
    -h|--help)         usage; exit 0 ;;
    *) echo "reboot-policy: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[ -n "$CMD" ] || { usage; exit 2; }

case "$ROOT_DIR" in
  *"/.qq/"*|*"/.qq"|*"/.codeseeq/"*)
    echo "reboot-policy: REFUSING QonQrete metadata as a root: $ROOT_DIR" >&2; exit 2 ;;
esac
case "$STATE_FILE" in
  *"/.qq/"*|*"/.qq") echo "reboot-policy: REFUSING QonQrete metadata path" >&2; exit 2 ;;
esac
if [ -z "$STATE_FILE" ]; then
  if [ "$ROOT_DIR" = "/" ]; then STATE_FILE="/var/lib/nuxel/reboot-history.json"
  else STATE_FILE="$ROOT_DIR/var/lib/nuxel/reboot-history.json"; fi
fi
mkdir -p "$(dirname "$STATE_FILE")" 2>/dev/null || true
say() { [ "$QUIET" -eq 1 ] || echo "$@"; }

policy_check() {  # policy_check [reason diagnostic mode]
  "$PY" "$LIB" policy-check --state "$STATE_FILE" \
      ${1:+--reason "$1"} ${2:+--diagnostic "$2"} ${3:+--mode "$3"}
}

print_status() {
  local doc
  doc="$("$PY" - "$STATE_FILE" <<'PY'
import json, sys
try:
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    doc = {"history": [], "failures": {}}
hist = doc.get("history", [])
print("  state file : %s" % sys.argv[1])
print("  reboots    : %d/%d used" % (len([h for h in hist if h.get("kind", "reboot") != "failure"]), 3))
print("  failures   : %s" % (json.dumps(doc.get("failures", {})) or "{}"))
print("  last entry : %s" % (json.dumps(hist[-1]) if hist else "<none>"))
print("  loop check : reached_to_nuxel=%s  same_mode_failures=%s" % (
    (hist[-1].get("returned_to_nuxel") if hist else "n/a"),
    json.dumps(doc.get("failures", {}))))
PY
)"
  say "reboot policy status"
  printf '%s\n' "$doc"
}

run_checklist() {  # run_checklist pre|post
  local which="$1" json
  json="$("$PY" "$LIB" checklists)"
  say "=== $(printf '%s' "$which" | tr '[:lower:]' '[:upper:]')-reboot checklist ($( [ "$RUN" -eq 1 ] && echo "executing read-only probes" || echo "plan only")) ==="
  "$PY" - "$json" "$which" "$RUN" <<'PY'
import json, subprocess, sys
doc, which, run = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3] == "1"
items = doc["pre"] if which == "pre" else doc["post"]
fails = 0
for cid, title, cmd in items:
    print("  [%s] %s" % (cid, title))
    print("        %s" % cmd)
    if run:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        state = "ok" if p.returncode == 0 else "FAIL"
        if p.returncode != 0:
            fails += 1
        print("        -> %s (%s)" % (state, (p.stdout or p.stderr).strip().splitlines()[:1]))
print("checklist: %s" % ("all read-only probes passed" if fails == 0 else "%d probe(s) failed" % fails))
sys.exit(1 if fails else 0)
PY
}

case "$CMD" in
  status|policy)
    print_status
    policy_check; rc=$?
    [ "$rc" -eq 0 ] && say "  next reboot: ALLOWED" || say "  next reboot: DENIED (see above)"
    exit "$rc" ;;

  check)
    out="$(policy_check "$REASON" "$DIAGNOSTIC" "$MODE")"; rc=$?
    printf '%s\n' "$out"
    if [ "$rc" -eq 0 ]; then say "reboot-policy: ALLOWED"; else say "reboot-policy: DENIED"; fi
    exit "$rc" ;;

  failure)
    [ -n "$MODE" ] || { echo "reboot-policy failure: --mode is required" >&2; exit 2; }
    "$PY" "$LIB" policy-record --state "$STATE_FILE" --kind failure --mode "$MODE" \
        --reason "${NOTE:-same-mode failure}" --diagnostic "mode=$MODE" >/dev/null
    n="$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1])).get("failures",{}).get(sys.argv[2],0))' "$STATE_FILE" "$MODE")"
    say "reboot-policy: recorded failure #$n in mode '$MODE'"
    if [ "$n" -ge 3 ]; then
      say "reboot-policy: THREE-SAME-MODE-FAILURE GUARD ACTIVE — no further reboot will"
      say "               be allowed with mode '$MODE'; change the diagnostic strategy"
      say "               (different evidence channel / different layer / different tool)."
      exit 1
    fi
    exit 0 ;;

  record)
    out="$(policy_check "$REASON" "$DIAGNOSTIC")"; rc=$?
    if [ "$rc" -ne 0 ]; then
      echo "reboot-policy: refusing to record — the policy denied this reboot:" >&2
      printf '%s\n' "$out" >&2
      exit 1
    fi
    "$PY" "$LIB" policy-record --state "$STATE_FILE" --kind reboot --reason "$REASON" \
        --diagnostic "$DIAGNOSTIC" --mode "$MODE" --returned-to-nuxel "$RETURNED" >/dev/null
    say "reboot-policy: recorded reboot (returned_to_nuxel=$RETURNED)"
    [ -n "$EVIDENCE_BEFORE" ] && say "  evidence before: $EVIDENCE_BEFORE"
    [ -n "$EVIDENCE_AFTER" ]  && say "  evidence after : $EVIDENCE_AFTER"
    exit 0 ;;

  pre)  run_checklist pre ;;
  post) run_checklist post ;;

  reboot)
    [ -n "$REASON" ] && [ -n "$DIAGNOSTIC" ] || {
      echo "reboot-policy reboot: --reason and --diagnostic are both required (no blind reboots)" >&2
      exit 2; }
    out="$(policy_check "$REASON" "$DIAGNOSTIC" "$MODE")" || {
      echo "reboot-policy reboot: DENIED by policy:" >&2
      printf '%s\n' "$out" >&2
      exit 1; }
    say "reboot-policy: policy allows this reboot"
    say "  reason     : $REASON"
    say "  diagnostic : $DIAGNOSTIC (must differ from the previous reboot)"
    say "  command    : reboot"
    say "  rollback   : tools/beta/rollback.sh status (must be known-good)"
    if [ "$EXECUTE" -eq 0 ] || [ "$CONFIRM" -eq 0 ]; then
      say "reboot-policy: NOT ISSUING — --execute --confirm were not both supplied."
      say "               This tool never reboots on its own initiative."
      exit 3
    fi
    # reachability gate: a reboot without a working console cannot be recovered
    reach_rc=0
    if [ -n "${REBOOT_REACHABILITY_CMD:-}" ]; then
      bash -c "$REBOOT_REACHABILITY_CMD" >/dev/null 2>&1 || reach_rc=$?
    elif [ -x "$REACHABILITY" ]; then
      "$PY" "$REACHABILITY" --json >/dev/null 2>&1 || reach_rc=$?
    else
      reach_rc=3
    fi
    if [ "$reach_rc" -ne 0 ]; then
      say "reboot-policy: BLOCKED_EXTERNAL_RESOURCE — the live S10+ console is not reachable"
      say "               (reachability rc=$reach_rc, see tools/beta/live/nuxel-live-reachability.py)."
      say "               A reboot with no console to reconnect to is unrecoverable: refused."
      exit 3
    fi
    say "reboot-policy: console reachable; issuing the reboot now"
    if [ "${REBOOT_DRY_RUN:-0}" = "1" ]; then
      say "  (REBOOT_DRY_RUN=1: command printed, not executed)"
      exit 0
    fi
    # The actual reboot: normal OS reboot only — nothing else.  The caller (the
    # live group) owns the session; the record is written first so a lost post
    # state is still visible in the history.
    "$PY" "$LIB" policy-record --state "$STATE_FILE" --kind reboot --reason "$REASON" \
        --diagnostic "$DIAGNOSTIC" --mode "$MODE" --returned-to-nuxel no >/dev/null
    reboot
    exit 0 ;;

  selftest)
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-reboot-XXXXXX")"
    st="$tmp/history.json"
    fails=0
    ok()  { echo "  PASS $1"; }
    bad() { echo "  FAIL $1${2:+ — $2}"; fails=$((fails + 1)); }
    echo "=== reboot-policy.sh selftest (offline) ==="

    # 1. fresh history: a reboot with reason+diagnostic is allowed
    bash "$0" check --state "$st" --reason "test Wi-Fi after a config change" \
        --diagnostic "wifi-diag layer 2" --quiet >/dev/null 2>&1 \
      && ok "fresh policy allows a reasoned reboot" || bad "fresh policy allows a reasoned reboot"

    # 2. a reboot without a diagnostic is refused (no blind reboots)
    bash "$0" check --state "$st" --reason "just because" --quiet >/dev/null 2>&1 \
      && bad "reboot without a diagnostic refused" || ok "reboot without a diagnostic refused"

    # 3. record one that returned to Nuxel, then repeat the same diagnostic
    bash "$0" record --state "$st" --reason "r1" --diagnostic "d1" --returned-to-nuxel yes --quiet >/dev/null 2>&1 \
      && ok "recorded reboot #1 (returned to Nuxel)" || bad "recorded reboot #1"
    bash "$0" check --state "$st" --reason "r2" --diagnostic "d1" --quiet >/dev/null 2>&1 \
      && bad "identical diagnostic refused (blind repeat)" || ok "identical diagnostic refused (blind repeat)"
    bash "$0" check --state "$st" --reason "r1" --diagnostic "d2" --quiet >/dev/null 2>&1 \
      && bad "identical reason refused" || ok "identical reason refused"

    # 4. a reboot that never returned to Nuxel blocks the next one
    bash "$0" record --state "$st" --reason "r2" --diagnostic "d2" --returned-to-nuxel no --quiet >/dev/null 2>&1
    bash "$0" check --state "$st" --reason "r3" --diagnostic "d3" --quiet >/dev/null 2>&1 \
      && bad "no-return blocks the next reboot" || ok "a reboot that never returned blocks the next one"

    # 5. three same-mode failures switch off that mode
    st2="$tmp/history2.json"
    for i in 1 2 3; do bash "$0" failure --state "$st2" --mode "touch-irq" --note "attempt $i" --quiet >/dev/null 2>&1; done
    bash "$0" check --state "$st2" --reason "r" --diagnostic "d" --mode "touch-irq" --quiet >/dev/null 2>&1 \
      && bad "three-same-mode-failure guard denies the mode" || ok "three-same-mode-failure guard denies the mode"

    # 6. budget: four recorded reboots exhaust it
    st3="$tmp/history3.json"
    for i in 1 2 3; do
      bash "$0" record --state "$st3" --reason "r$i" --diagnostic "d$i" --returned-to-nuxel yes --quiet >/dev/null 2>&1
    done
    bash "$0" check --state "$st3" --reason "r4" --diagnostic "d4" --quiet >/dev/null 2>&1 \
      && bad "budget exhausted after 3 reboots" || ok "budget exhausted after 3 reboots"

    # 7. checklists exist and are addressable
    n="$("$PY" "$LIB" checklists | "$PY" -c 'import json,sys;d=json.load(sys.stdin);print(len(d["pre"])+len(d["post"]))')"
    [ "$n" -ge 10 ] && ok "pre+post reboot checklists present ($n items)" || bad "checklists present" "n=$n"
    bash "$0" pre --state "$st" --quiet >/dev/null 2>&1 && ok "pre-reboot checklist prints" || bad "pre-reboot checklist prints"

    # 8. reboot is refused without --execute --confirm, and refused with no console
    #    (fresh history: the policy allows it, so exactly the next gate decides)
    st4="$tmp/history4.json"
    rc=0
    bash "$0" reboot --state "$st4" --reason "why" --diagnostic "how" --quiet >/dev/null 2>&1 || rc=$?
    [ "$rc" -eq 3 ] && ok "reboot refused without --execute --confirm (exit 3)" \
      || bad "reboot refused without --execute --confirm" "rc=$rc"
    rc=0
    REBOOT_REACHABILITY_CMD="false" bash "$0" reboot --state "$st4" --reason "why" \
        --diagnostic "how" --execute --confirm --quiet >/dev/null 2>&1 || rc=$?
    [ "$rc" -eq 3 ] && ok "reboot refused when the console is unreachable (exit 3)" \
      || bad "reboot refused when the console is unreachable" "rc=$rc"
    # and a reachable console with REBOOT_DRY_RUN=1 must still not reboot the host
    rc=0
    REBOOT_REACHABILITY_CMD="true" REBOOT_DRY_RUN=1 bash "$0" reboot --state "$st4" \
        --reason "dry run" --diagnostic "dry run diagnostic" --execute --confirm --quiet >/dev/null 2>&1 || rc=$?
    [ "$rc" -eq 0 ] && ok "with a reachable console it prints the command (REBOOT_DRY_RUN=1)" \
      || bad "dry-run path with a reachable console" "rc=$rc"

    # 9. guards: .qq state file / root is refused
    bash "$0" status --state "$WORKSPACE/.qq/nope.json" --quiet >/dev/null 2>&1 \
      && bad "QonQrete metadata state refused" || ok "QonQrete metadata state refused"

    # 10. no reboot was issued by any of the above
    pgrep -fl "reboot" >/dev/null 2>&1 && say "  note: a process named *reboot* exists on this host" || ok "no reboot was issued"

    rm -rf "$tmp"
    echo "reboot-policy.sh selftest: $([ "$fails" -eq 0 ] && echo PASS || echo "FAIL ($fails)")"
    [ "$fails" -eq 0 ] || exit 1
    exit 0 ;;
  *) usage; exit 2 ;;
esac
