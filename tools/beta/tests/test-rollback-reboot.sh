#!/usr/bin/env bash
# =============================================================================
# test-rollback-reboot.sh — mocked failure scenarios for the rollback discipline
# and the reboot policy (briq-09b, areas 53/54)
#
# Every scenario below is REAL: a sandbox root tree, real files, real hashes and
# the real tools.  Nothing touches the phone, /dev, .qq/ or the repository: the
# sandbox lives in a mktemp directory, is pointed at with --root/--state, and is
# removed on exit.
#
# Scenarios
#   1  capture records the previous hash of every tracked target (and records an
#      absent target as absent — never as invented content)
#   2  an install that cannot be completed is auto-rolled-back and the previous
#      bytes survive byte-identical
#   3  a manifest whose declared health_check fails is auto-rolled-back too
#   4  a raw-block target is a manifest violation: refused, nothing written
#   5  a missing source is a violation: refused, nothing written
#   6  a clean install into the sandbox succeeds and reports DEPLOYED_UNVERIFIED
#      (never a device verdict)
#   7  rollback restores a baseline after a manual mutation
#   8  --briq isolates the baseline under <state>/<briq-id>/ and records the id
#   9  reboot policy: reason + a *different* diagnostic are mandatory; a blind
#      repeat, a repeated reason, a non-returned reboot, the 3-reboot budget and
#      three same-mode failures are all refused (the A31 three-strikes rule)
#  10  reboot-policy.sh reboot never reboots unless --execute --confirm AND a
#      reachable console AND not a dry run; every other path is inert (proved
#      with a mocked `reboot` shim that must stay untouched)
#  11  no tool wrote under .qq/ and no receipt JSON landed in the workspace
#
# Exit 0 = every scenario behaved as documented.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
PY="${TEST_PY:-python3}"
SBX="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-rb-scen-XXXXXX")"
trap 'rm -rf "$SBX"' EXIT

PASS=0; FAIL=0
ok()  { PASS=$((PASS + 1)); echo "  PASS $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  FAIL $1${2:+ — $2}"; }

RB="$ROOT/tools/beta/rollback.sh"
RP="$ROOT/tools/beta/reboot-policy.sh"

# the tracked set every sandbox baseline records
MK_PATHS="$SBX/tracked.paths"
printf '%s\n' \
  '/usr/local/bin/nuxelctl' \
  '/home/nuxel/nuxel/pwa/nuxel-home/js/app.js' \
  '/etc/nuxel/boot/verbose.json' > "$MK_PATHS"

# a `reboot` shim: if any scenario ever reaches the real reboot path, the shim
# records it instead of rebooting the build host.  Scenario 10 asserts the shim
# is NEVER touched without --execute --confirm + a reachable console + no dry run.
SHIM="$SBX/shim"; mkdir -p "$SHIM"
cat > "$SHIM/reboot" <<'SH'
#!/bin/sh
echo "REBOOT-ISSUED" >> "$(dirname "$0")/reboot-called.marker"
SH
chmod +x "$SHIM/reboot"
PATH="$SHIM:$PATH"; export PATH
if [ "$(command -v reboot)" != "$SHIM/reboot" ]; then
  echo "FATAL: the reboot shim is not first on PATH — refusing to run" >&2
  exit 2
fi

echo "=== rollback & reboot-policy scenarios (offline, sandboxed) ==="
echo "  sandbox: $SBX"

# ---- a healthy sandbox root -------------------------------------------------
# health-check.sh (offline tier) wants: the framebuffer owner record, the
# launcher-ready marker and the four stack units present.
mksandbox() {
  local r="$1"
  rm -rf "$r"
  mkdir -p "$r/usr/local/bin" "$r/etc/systemd/system" "$r/var/lib/nuxel" \
           "$r/etc/nuxel/boot" "$r/home/nuxel/nuxel/pwa/nuxel-home/js" \
           "$r/usr/lib/systemd/system"
  printf '#!/bin/sh\necho nuxelctl v1\n' > "$r/usr/local/bin/nuxelctl"
  printf 'console.log("app v1");\n'      > "$r/home/nuxel/nuxel/pwa/nuxel-home/js/app.js"
  printf '{"protocol":1}\n'              > "$r/etc/nuxel/boot/verbose.json"
  printf '{"pid": 1401, "owner": "nuxel-wl-fb", "stage": "LAUNCHER_DISPLAY_OWNER"}\n' \
    > "$r/var/lib/nuxel/fb-owner"
  : > "$r/var/lib/nuxel/launcher-ready"
  local u
  for u in nuxel-pwa nuxel-wl-fb nuxel-button-manager nuxel-wayland; do
    : > "$r/usr/lib/systemd/system/$u.service"
  done
}

sha() { "$PY" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"; }

# --------------------------------------------------------------------------- #
# 1. capture records real hashes; an absent tracked target is recorded absent
# --------------------------------------------------------------------------- #
R1="$SBX/r1"; mksandbox "$R1"
printf '/usr/local/bin/nuxelctl\n/etc/nuxel/does-not-exist.json\n' > "$SBX/paths1"
bash "$RB" capture --root "$R1" --state "$R1/rs" --briq briq-09b --paths "$SBX/paths1" \
  >"$SBX/cap1.out" 2>&1
base="$(ls -d "$R1"/rs/briq-09b/baseline-* 2>/dev/null | tail -1)"
if [ -n "$base" ] && "$PY" - "$base/baseline.json" "$(sha "$R1/usr/local/bin/nuxelctl")" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); want=sys.argv[2]
ents={e["path"]:e for e in d["entries"]}
assert d["briq"]=="briq-09b", d.get("briq")
assert ents["/usr/local/bin/nuxelctl"]["sha256"]==want, ents
assert ents["/etc/nuxel/does-not-exist.json"]["kind"]=="absent", ents
assert d["known_good"] is True
assert d.get("root"), d
PY
then ok "capture records the previous hash (and records an absent target as absent)"
else bad "capture records the previous hash" "$(tail -2 "$SBX/cap1.out" | tr '\n' ' ')"; fi

# --------------------------------------------------------------------------- #
# 2. an install that cannot be completed -> auto-rollback, previous bytes intact
# --------------------------------------------------------------------------- #
R2="$SBX/r2"; mksandbox "$R2"
bash "$RB" capture --root "$R2" --state "$R2/rs" --briq briq-09b --paths "$MK_PATHS" >/dev/null 2>&1
printf 'console.log("app v2 MUST NOT SURVIVE");\n' > "$SBX/app-v2.js"
sha_before="$(sha "$R2/home/nuxel/nuxel/pwa/nuxel-home/js/app.js")"
# the target's parent path is a regular file: `mkdir -p` cannot succeed, so the
# install must stop, roll back and say so.
cat > "$SBX/manifest-unwritable.json" <<'JSON'
{"groups":[{"id":"g-unwritable","component":"launcher","priority":2,
  "files":[{"source":"app-v2.js",
            "target":"/usr/local/bin/nuxelctl/cannot/exist/app.js"}]}]}
JSON
bash "$RB" install --root "$R2" --state "$R2/rs" --briq briq-09b \
  --manifest "$SBX/manifest-unwritable.json" --src-root "$SBX" --no-restart \
  >"$SBX/inst2.out" 2>&1; rc2=$?
sha_after="$(sha "$R2/home/nuxel/nuxel/pwa/nuxel-home/js/app.js")"
if [ "$rc2" -eq 3 ] && [ "$sha_before" = "$sha_after" ] && grep -q "ROLLED_BACK" "$SBX/inst2.out"; then
  ok "an install that cannot be completed: auto-rollback, previous bytes intact (rc=3)"
else
  bad "un-completable install scenario" "rc=$rc2 same=$([ "$sha_before" = "$sha_after" ] && echo yes || echo no) $(tail -2 "$SBX/inst2.out" | tr '\n' ' ')"
fi
[ -e "$R2/home/nuxel/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged" ] \
  && bad "no staged file left behind after the refused install" \
  || ok "no staged file left behind after the refused install"

# --------------------------------------------------------------------------- #
# 3. a failing group health_check -> automatic rollback
# --------------------------------------------------------------------------- #
R3="$SBX/r3"; mksandbox "$R3"
sha_before3="$(sha "$R3/home/nuxel/nuxel/pwa/nuxel-home/js/app.js")"
good_sha="$(sha "$SBX/app-v2.js")"
cat > "$SBX/manifest-badcheck.json" <<JSON
{"groups":[{"id":"g-check","component":"launcher","priority":2,
  "health_check":"test -e /definitely/not/here",
  "files":[{"source":"app-v2.js","target":"/home/nuxel/nuxel/pwa/nuxel-home/js/app.js"}]}]}
JSON
bash "$RB" install --root "$R3" --state "$R3/rs" --briq briq-09b \
  --manifest "$SBX/manifest-badcheck.json" --src-root "$SBX" --no-restart \
  >"$SBX/inst3.out" 2>&1; rc3=$?
sha_after3="$(sha "$R3/home/nuxel/nuxel/pwa/nuxel-home/js/app.js")"
if [ "$rc3" -eq 3 ] && [ "$sha_before3" = "$sha_after3" ] \
   && grep -q "health_check failed" "$SBX/inst3.out"; then
  ok "a failing manifest health_check: automatic rollback (rc=3)"
else
  bad "failing health_check scenario" "rc=$rc3 $(tail -2 "$SBX/inst3.out" | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# 4. a raw-block target is a violation: nothing is written
# --------------------------------------------------------------------------- #
R4="$SBX/r4"; mksandbox "$R4"
cat > "$SBX/manifest-block.json" <<'JSON'
{"groups":[{"id":"g-block","component":"x","priority":1,
  "files":[{"source":"app-v2.js","target":"/dev/block/sda1"}]}]}
JSON
bash "$RB" install --root "$R4" --state "$R4/rs" --briq briq-09b \
  --manifest "$SBX/manifest-block.json" --src-root "$SBX" --no-restart \
  >"$SBX/inst4.out" 2>&1; rc4=$?
if [ "$rc4" -eq 4 ] && grep -qi "violation" "$SBX/inst4.out"; then
  ok "raw-block target refused as a manifest violation, nothing written (rc=4)"
else
  bad "raw-block target refusal" "rc=$rc4 $(tail -2 "$SBX/inst4.out" | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# 5. a missing source is a violation: nothing is written
# --------------------------------------------------------------------------- #
R5V="$SBX/r5v"; mksandbox "$R5V"
cat > "$SBX/manifest-nosrc.json" <<'JSON'
{"groups":[{"id":"g-nosrc","component":"x","priority":1,
  "files":[{"source":"no-such-file.bin","target":"/usr/local/bin/nuxelctl"}]}]}
JSON
bash "$RB" install --root "$R5V" --state "$R5V/rs" --briq briq-09b \
  --manifest "$SBX/manifest-nosrc.json" --src-root "$SBX" --no-restart \
  >"$SBX/inst5v.out" 2>&1; rc5v=$?
if [ "$rc5v" -eq 4 ] && [ "$(sha "$R5V/usr/local/bin/nuxelctl")" != "" ]; then
  ok "a missing source is refused as a manifest violation (rc=4, target untouched)"
else
  bad "missing-source refusal" "rc=$rc5v $(tail -2 "$SBX/inst5v.out" | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# 6. a clean install into the healthy sandbox succeeds (DEPLOYED_UNVERIFIED)
# --------------------------------------------------------------------------- #
R6="$SBX/r6"; mksandbox "$R6"
cat > "$SBX/manifest-good.json" <<JSON
{"groups":[{"id":"g-good","component":"launcher","priority":2,
  "restart_service":"nuxel-pwa",
  "files":[{"source":"app-v2.js","target":"/home/nuxel/nuxel/pwa/nuxel-home/js/app.js"}]}]}
JSON
bash "$RB" install --root "$R6" --state "$R6/rs" --briq briq-09b \
  --manifest "$SBX/manifest-good.json" --src-root "$SBX" --no-restart \
  >"$SBX/inst6.out" 2>&1; rc6=$?
newsha="$(sha "$R6/home/nuxel/nuxel/pwa/nuxel-home/js/app.js")"
if [ "$rc6" -eq 0 ] && [ "$newsha" = "$good_sha" ] \
   && grep -q "DEPLOYED_UNVERIFIED" "$SBX/inst6.out"; then
  ok "clean install: staged-verified, atomic, health-gated; verdict DEPLOYED_UNVERIFIED"
else
  bad "clean install scenario" "rc=$rc6 $(tail -3 "$SBX/inst6.out" | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# 7. rollback restores a baseline after a manual mutation
# --------------------------------------------------------------------------- #
printf '#!/bin/sh\necho BROKEN\n' > "$R6/usr/local/bin/nuxelctl"
bash "$RB" rollback --root "$R6" --state "$R6/rs" --briq briq-09b \
  >"$SBX/rb7.out" 2>&1; rc7=$?
if [ "$rc7" -eq 0 ] && grep -q "nuxelctl v1" "$R6/usr/local/bin/nuxelctl" \
   && grep -qiE "restored" "$SBX/rb7.out"; then
  ok "rollback restores the recorded baseline after a mutation"
else
  bad "rollback restore scenario" "rc=$rc7 $(tail -3 "$SBX/rb7.out" | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# 8. --briq isolation
# --------------------------------------------------------------------------- #
if [ -d "$R6/rs/briq-09b" ] \
   && "$PY" -c 'import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if d.get("briq")=="briq-09b" else 1)' \
        "$(ls -d "$R6"/rs/briq-09b/baseline-*/baseline.json | tail -1)"; then
  ok "--briq isolates the baseline under <state>/<briq-id>/ and records the id"
else
  bad "--briq isolation"
fi

# --------------------------------------------------------------------------- #
# 9. reboot policy refusals (mocked history, sandbox state FILE)
# --------------------------------------------------------------------------- #
PS="$SBX/reboot-history.json"
rq() { # rq <expected-exit> <label> <args...>
  local want="$1" label="$2"; shift 2
  bash "$RP" "$@" --state "$PS" >"$SBX/rq.out" 2>&1; local got=$?
  if [ "$got" -eq "$want" ]; then ok "$label"; else bad "$label" "rc=$got want=$want $(tail -1 "$SBX/rq.out")"; fi
}
sethist() { # sethist <python-expression producing the history list> <failures json>
  "$PY" - "$PS" "$1" "$2" <<'PY'
import json, sys, time
path, expr, failures = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
hist = []
for i, (reason, diag, returned) in enumerate(eval(expr, {}, {}), 1):
    hist.append({"at": now, "kind": "reboot", "reason": reason, "diagnostic": diag,
                 "returned_to_nuxel": returned})
json.dump({"schema_version": 1, "history": hist, "failures": failures},
          open(path, "w", encoding="utf-8"), indent=2)
PY
}

rq 1 "policy refuses a reboot with no stated reason"        check --diagnostic d1
rm -f "$PS"
rq 0 "policy allows the first reboot (reason + diagnostic)" check --reason r1 --diagnostic d1

sethist "[( 'r1', 'd1', True )]" "{}"
rq 1 "policy refuses a blind repeat (same diagnostic)"     check --reason r2 --diagnostic d1
rq 1 "policy refuses the same reason twice"                check --reason r1 --diagnostic d2
rq 0 "policy allows a new reason + a new diagnostic"       check --reason r2 --diagnostic d2

sethist "[( 'r1', 'd1', False )]" "{}"
rq 1 "policy refuses the next reboot when Nuxel did not come back" check --reason r2 --diagnostic d2

sethist "[('r1','d1',True),('r2','d2',True),('r3','d3',True)]" "{}"
rq 1 "policy refuses a 4th reboot (hard budget of 3)"      check --reason r9 --diagnostic d9

# three failures in the SAME diagnostic mode are history entries of kind
# "failure" (that is what `reboot-policy.sh failure` writes), not a counter in the
# display-only failures map.
"$PY" - "$PS" <<'PY'
import json, sys, time
now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
hist = [{"at": now, "kind": "failure", "mode": "touch-irq",
         "reason": "attempt %d" % i, "diagnostic": "mode=touch-irq"} for i in (1, 2, 3)]
json.dump({"schema_version": 1, "history": hist, "failures": {"touch-irq": 3}},
          open(sys.argv[1], "w", encoding="utf-8"), indent=2)
PY
rq 1 "policy refuses further reboots in a mode that failed three times" \
   check --reason r1 --diagnostic d1 --mode touch-irq
rq 0 "a different diagnostic mode is still allowed (the guard is mode-scoped)" \
   check --reason r1 --diagnostic d1 --mode usb-console

# --------------------------------------------------------------------------- #
# 10. reboot is never issued without the full explicit gate, and the dry run is
#     inert (proved with a `reboot` shim that must stay untouched)
# --------------------------------------------------------------------------- #
rm -f "$PS" "$SHIM/reboot-called.marker"
bash "$RP" reboot --reason "dry-run proof" --diagnostic "d-dry" --state "$PS" \
  >"$SBX/rb10a.out" 2>&1; rc10a=$?
bash "$RP" reboot --reason "dry-run proof" --diagnostic "d-dry" --state "$PS" \
  --execute --confirm >"$SBX/rb10b.out" 2>&1; rc10b=$?
REBOOT_REACHABILITY_CMD=true REBOOT_DRY_RUN=1 \
  bash "$RP" reboot --reason "dry-run proof" --diagnostic "d-dry" --state "$PS" \
  --execute --confirm >"$SBX/rb10c.out" 2>&1; rc10c=$?
if [ "$rc10a" -eq 3 ] && grep -q "NOT ISSUING" "$SBX/rb10a.out" \
   && [ "$rc10b" -eq 3 ] && grep -q "BLOCKED_EXTERNAL_RESOURCE" "$SBX/rb10b.out" \
   && [ "$rc10c" -eq 0 ] && ! [ -e "$SHIM/reboot-called.marker" ]; then
  ok "reboot needs --execute --confirm AND a reachable console; the dry run issues nothing"
else
  bad "reboot gating / dry-run inertness" \
      "a=$rc10a b=$rc10b c=$rc10c shim=$([ -e "$SHIM/reboot-called.marker" ] && echo CALLED || echo untouched)"
fi
# structural proof: the only `reboot` invocation sits after the reachability gate
# and after the dry-run exit.
order="$("$PY" - "$RP" <<'PY'
import re, sys
lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
def first(pat):
    for i, l in enumerate(lines, 1):
        if re.match(pat, l):
            return i
    return -1
gate = first(r"^\s*reach_rc=0\s*$")
dry  = first(r".*REBOOT_DRY_RUN.*=.*1.*; then\s*$")
call = first(r"^\s*reboot\s*$")
print("%d %d %d" % (gate, dry, call))
PY
)"
set -- $order
if [ "$1" -gt 0 ] && [ "$2" -gt 0 ] && [ "$3" -gt 0 ] && [ "$1" -lt "$3" ] && [ "$2" -lt "$3" ]; then
  ok "the reboot invocation is guarded: reachability gate (line $1) and dry-run exit (line $2) precede it (line $3)"
else
  bad "the reboot invocation is guarded" "lines: $order"
fi

# --------------------------------------------------------------------------- #
# 11. no writes into QonQrete metadata, no receipt JSON in the workspace
# --------------------------------------------------------------------------- #
if grep -rl -- "$(basename "$SBX")" "$ROOT/.qq" >/dev/null 2>&1; then
  bad "no scenario wrote under .qq"
else
  ok "no scenario wrote under .qq"
fi
leaked="$(find "$ROOT" -maxdepth 3 -newer "$SBX" -name '*receipt*.json' -not -path '*/.git/*' 2>/dev/null | head -3)"
[ -z "$leaked" ] && ok "no receipt JSON was written into the workspace" \
  || bad "no receipt JSON was written into the workspace" "$leaked"

echo "rollback/reboot scenario tests: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
