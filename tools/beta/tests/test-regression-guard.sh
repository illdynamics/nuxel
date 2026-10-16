#!/usr/bin/env bash
# test-regression-guard.sh — self-test for tools/beta/regression-guard.sh (briq-00d)
#
# Hermetic: everything happens in a throw-away sandbox under $TMPDIR.  The real
# repository is only *read* (the guard script and the register are copied out of
# it).  No phone, no VM, no network, no block device, no framebuffer.
#
# It proves, by construction, that the guard actually detects regressions rather
# than always printing PASS:
#
#   1. matching file, no drift              -> exit 0, verdict PASS
#   2. one byte changed in a pinned file    -> exit 1, verdict FAIL, file named
#   2b. a file explicitly pinned soft inside a HARD invariant -> WARN, exit 0
#       (mode precedence: the per-file hash_mode wins, the invariant mode is only
#        the default - BASELINE-PROTECTION.md section 2 / section 10 rule 3)
#   2c. a file with no hash_mode inherits the invariant mode -> still exit 1
#   3. assertion regex broken in the file   -> exit 1, verdict FAIL
#   3b. same assertion marked mode:"soft"   -> exit 0, verdict PASS + WARN naming the owner
#   4. --repin <path> --reason ...          -> exit 0, new hash stored, history appended
#   5. --repin without --reason             -> exit 2
#   6. --repin on an unregistered path      -> exit 2
#   7. missing register                     -> exit 2
#   8. --json emits a single machine-readable line for a genuinely drifted file
#
# Usage: bash tools/beta/tests/test-regression-guard.sh
# Exit status = number of failed cases.

set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
GUARD="$ROOT/tools/beta/regression-guard.sh"
REGISTER="$ROOT/docs/beta-finalization/baseline-protection.json"

FAIL=0
PASS=0
ok()   { PASS=$((PASS + 1)); printf 'PASS %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf 'FAIL %s\n' "$1"; }

command -v jq >/dev/null 2>&1 || { echo "SKIP: jq required"; exit 0; }
[ -f "$GUARD" ] || { echo "FAIL guard script missing: $GUARD"; exit 1; }
[ -f "$REGISTER" ] || { echo "FAIL register missing: $REGISTER"; exit 1; }

SB="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-guard-test.XXXXXX")"
trap 'rm -rf "$SB"' EXIT

mkdir -p "$SB/tools/beta" "$SB/docs/beta-finalization/tools/s10plus/a32"
cp "$GUARD" "$SB/tools/beta/regression-guard.sh"
chmod +x "$SB/tools/beta/regression-guard.sh"
PROT="$SB/docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c"
printf 'DECON maps R@0 G@8 B@16 (ABGR_8888); XRGB8888 source word 0x00RRGGBB -> 0xff0000ff\n' > "$PROT"
H="$(shasum -a 256 "$PROT" | awk '{print $1}')"

# A register with exactly one invariant, one pinned file and two assertions
# (one byte pin, one behavioural regex) so the sandbox run cannot touch the VM.
jq -n --arg h "$H" --arg fp "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c" '{
  schema_version: 1,
  generated_at: "self-test",
  vm_host: "nuxel@192.168.64.3",
  baseline: {commit_a32: "self-test"},
  history: [],
  invariants: [{
    id: "INV-TEST-colour", title: "self-test invariant", hash_mode: "hard",
    files: [{path: $fp, sha256: $h, exists: true, role: "self-test", hash_mode: "hard"}],
    assertions: [
      {type: "sha256", path: $fp, expect: $h, on_missing: "fail", label: "self-test byte pin"},
      {type: "regex", path: $fp, pattern: "ABGR_8888", min_count: 1, label: "self-test behavioural assertion"}
    ]
  }]
}' > "$SB/docs/beta-finalization/baseline-protection.json"

run_case() { # run_case -> sets RC and OUT
  OUT="$(cd "$SB" && bash "$SB/tools/beta/regression-guard.sh" --no-tests "$@" 2>&1)"
  RC=$?
}

# --- 1. clean tree ------------------------------------------------------------
run_case
if [ "$RC" = "0" ] && printf '%s' "$OUT" | grep -q 'REGRESSION GUARD: PASS'; then
  ok "clean sandbox -> exit 0 and verdict PASS"
else
  bad "clean sandbox -> exit $RC (expected 0/PASS): $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"
fi

# --- 2. one byte changed in a hard-pinned file --------------------------------
cp "$PROT" "$PROT.orig"
printf '\n' >> "$PROT"
run_case
if [ "$RC" = "1" ] && printf '%s' "$OUT" | grep -q 'REGRESSION GUARD: FAIL' \
   && printf '%s' "$OUT" | grep -q 'hard-pinned file changed'; then
  ok "tampered pinned file -> exit 1 and FAIL names the drift"
else
  bad "tampered pinned file -> exit $RC (expected 1/FAIL): $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"
fi

# --- 2b/2c. hash_mode precedence (file mode wins; invariant mode is the default) --
cp "$PROT.orig" "$PROT"
run_case --repin "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c" --reason "precedence case setup" >/dev/null
python3 - "$SB/docs/beta-finalization/baseline-protection.json" <<'PYSNIP'
import json, sys
d = json.load(open(sys.argv[1]))
d['invariants'][0]['hash_mode'] = 'hard'                # invariant default: hard
d['invariants'][0]['files'][0]['hash_mode'] = 'soft'    # the FILE is explicitly soft
for a in d['invariants'][0]['assertions']:              # keep the case about the FILE pin
    if a.get('type') == 'sha256':
        a['mode'] = 'soft'
        a['owned_by'] = 'bg-04-self-test'
json.dump(d, open(sys.argv[1], 'w'), indent=2)
PYSNIP
printf 'soft-owned drift\n' >> "$PROT"
run_case
if [ "$RC" = "0" ] && printf '%s' "$OUT" | grep -q 'soft-pinned file drifted'; then
  ok "a file explicitly pinned soft inside a hard invariant -> WARN, gate stays PASS"
else
  bad "per-file soft mode ignored: rc=$RC $(printf '%s' "$OUT" | grep -E 'FAIL |WARN ' | head -2 | tr '\n' ' ')"
fi

cp "$PROT.orig" "$PROT"
run_case --repin "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c" --reason "fallback case setup" >/dev/null
python3 - "$SB/docs/beta-finalization/baseline-protection.json" <<'PYSNIP'
import json, sys
d = json.load(open(sys.argv[1]))
d['invariants'][0]['hash_mode'] = 'hard'
d['invariants'][0]['files'][0].pop('hash_mode', None)   # no per-file mode at all
json.dump(d, open(sys.argv[1], 'w'), indent=2)
PYSNIP
printf 'unowned drift\n' >> "$PROT"
run_case
if [ "$RC" = "1" ] && printf '%s' "$OUT" | grep -q 'hard-pinned file changed'; then
  ok "a file with no hash_mode inherits a hard invariant -> still a hard-pin FAIL"
else
  bad "invariant-mode fallback wrong: rc=$RC $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"
fi
# teardown: pristine bytes, file-level hard pin back, invariant mode back to hard
cp "$PROT.orig" "$PROT"
run_case --repin "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c" --reason "precedence case teardown" >/dev/null
python3 - "$SB/docs/beta-finalization/baseline-protection.json" <<'PYSNIP'
import json, sys
d = json.load(open(sys.argv[1]))
d['invariants'][0]['files'][0]['hash_mode'] = 'hard'
for a in d['invariants'][0]['assertions']:
    if a.get('type') == 'sha256':
        a['mode'] = 'hard'
        a.pop('owned_by', None)
json.dump(d, open(sys.argv[1], 'w'), indent=2)
PYSNIP

# --- 3. behavioural assertion broken, bytes re-pinned so only the regex fails --
run_case --repin "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c" --reason "self-test re-pin" >/dev/null
python3 - "$PROT" <<'PYX'
import sys
p = sys.argv[1]
t = open(p).read().replace('ABGR_8888', 'ABGR_9999')
open(p, 'w').write(t)
PYX
# re-pin the byte pin so that ONLY the behavioural (regex) assertion can fail
python3 - "$PROT" "$SB/docs/beta-finalization/baseline-protection.json" <<'PY'
import hashlib, json, sys
prot, reg = sys.argv[1], sys.argv[2]
h = hashlib.sha256(open(prot, 'rb').read()).hexdigest()
d = json.load(open(reg))
for inv in d['invariants']:
    for f in inv['files']:
        f['sha256'] = h
    for a in inv['assertions']:
        if a.get('type') == 'sha256':
            a['expect'] = h
json.dump(d, open(reg, 'w'), indent=2)
PY
run_case
if [ "$RC" = "1" ] && printf '%s' "$OUT" | grep -q 'self-test behavioural assertion'; then
  ok "broken behavioural assertion -> exit 1 even though the byte pin matches"
else
  bad "broken behavioural assertion -> exit $RC (expected 1/FAIL): $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"
fi
cp "$PROT.orig" "$PROT"

# --- 3b. an assertion marked mode:soft fails as a WARN naming the owner --------
printf 'soft-drift\n' >> "$PROT"
run_case --repin "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c" --reason "soft-mode case setup" >/dev/null
python3 - "$SB/docs/beta-finalization/baseline-protection.json" <<'PYSNIP'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
a = d['invariants'][0]['assertions'][1]          # the regex assertion
a['mode'] = 'soft'
a['owned_by'] = 'bg-02-self-test'
a['pattern'] = 'TOKEN_THAT_IS_NOT_THERE'
json.dump(d, open(p, 'w'), indent=2)
PYSNIP
run_case
if [ "$RC" = "0" ] && printf '%s' "$OUT" | grep -q 'soft: bg-02-self-test'; then
  ok "mode:soft assertion -> WARN naming the owning group, and the gate stays PASS"
else
  bad "soft assertion mode wrong: rc=$RC $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"
fi
# teardown: pristine bytes back, mode back to hard, re-pin so the sandbox is clean
cp "$PROT.orig" "$PROT"
run_case --repin "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c" --reason "soft-mode case teardown" >/dev/null
python3 - "$SB/docs/beta-finalization/baseline-protection.json" <<'PYSNIP'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
a = d['invariants'][0]['assertions'][1]
a['mode'] = 'hard'
a.pop('owned_by', None)
a['pattern'] = 'ABGR_8888'
json.dump(d, open(p, 'w'), indent=2)
PYSNIP

# --- 4/5/6. re-pin protocol ---------------------------------------------------
printf 'drift\n' >> "$PROT"
run_case --repin "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c" --reason "self-test re-pin after tamper"
NEWP="$(jq -r '.invariants[0].files[0].sha256' "$SB/docs/beta-finalization/baseline-protection.json")"
ACT="$(shasum -a 256 "$PROT" | awk '{print $1}')"
if [ "$NEWP" = "$ACT" ] && [ "$(jq -r '.history[-1].event' "$SB/docs/beta-finalization/baseline-protection.json")" = "repin" ]; then
  ok "re-pin stores the new hash and appends a history entry"
else
  bad "re-pin did not store the new hash / history entry"
fi
if [ "$RC" = "0" ]; then ok "run after re-pin is green again (exit 0)"
else bad "run after re-pin -> exit $RC (expected 0)"; fi

run_case --repin "docs/beta-finalization/tools/s10plus/a32/nuxel-wl-fb.c"
[ "$RC" = "2" ] && ok "re-pin without --reason -> exit 2" || bad "re-pin without --reason -> exit $RC (expected 2)"

run_case --repin "not/registered/file.c" --reason "nope"
[ "$RC" = "2" ] && ok "re-pin of an unregistered path -> exit 2" || bad "re-pin of unregistered path -> exit $RC (expected 2)"

# --- 7. missing register ------------------------------------------------------
mv "$SB/docs/beta-finalization/baseline-protection.json" "$SB/reg.bak"
run_case
[ "$RC" = "2" ] && ok "missing register -> exit 2" || bad "missing register -> exit $RC (expected 2)"
mv "$SB/reg.bak" "$SB/docs/beta-finalization/baseline-protection.json"

# --- 8. --json ---------------------------------------------------------------
# Create a real drift first: after the fixed --repin protocol the sandbox tree is
# consistent again, so the "does --json still report the failure" assertion needs a
# tampered file rather than the (now-absent) leftover inconsistency.
printf 'post-repin drift\n' >> "$PROT"
OUT="$(cd "$SB" && bash "$SB/tools/beta/regression-guard.sh" --no-tests --json 2>&1)"
RC=$?
if [ "$RC" = "1" ] && [ "$(printf '%s\n' "$OUT" | wc -l | tr -d ' ')" = "1" ] \
   && printf '%s' "$OUT" | jq -e '.tool == "regression-guard" and .fail > 0' >/dev/null 2>&1; then
  ok "--json emits exactly one machine-readable line (and still fails on the current drift)"
else
  bad "--json output unusable: rc=$RC out=$(printf '%s' "$OUT" | head -2 | tr '\n' ' ')"
fi

# --- 9. the real repository gate is green ------------------------------------
# (this is the acceptance criterion of briq-00d: guard green on the untouched tree)
OUT="$(cd "$ROOT" && bash "$GUARD" 2>&1)"
RC=$?
if [ "$RC" = "0" ]; then
  ok "real repository: regression guard green on the untouched tree (exit 0)"
else
  bad "real repository gate is not green: exit $RC -> $(printf '%s' "$OUT" | grep -E 'FAIL|REGRESSION' | tail -3 | tr '\n' ' ')"
fi

echo "== $FAIL failing self-test(s), $PASS passing =="
exit "$FAIL"
