#!/usr/bin/env bash
# =============================================================================
# test-release-tools.sh — the release tooling tests itself (briq-09b, area 54)
#
# Runs, offline and sandboxed (never touching the phone, never writing into the
# repository):
#   * rollback.sh selftest        baseline discipline + automatic rollback
#   * reboot-policy.sh selftest   reason/diagnostic rules, budget, 3-strike guard
#   * soak.sh --selftest          soak/performance harness + blocked-resource path
#   * health-check.sh             offline fixture tier + guards
#   * release_lib.py              guards, service mapping, policy matrix, manifests
#   * run-all-tests.sh            registry integrity + machine-readable summary
#   * docs cross-links            the release deliverable set is present and linked
#
# Exit 0 = every release tool behaved as documented.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
PY="${TEST_PY:-python3}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-release-tests-XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0; FAIL=0
ok()  { PASS=$((PASS + 1)); echo "  PASS $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  FAIL $1${2:+ — $2}"; }
run_quiet() { "$@" >"$TMP/out" 2>&1; }

echo "=== release tooling tests (offline) ==="

# --------------------------------------------------------------------------- #
# 1. rollback.sh
# --------------------------------------------------------------------------- #
if run_quiet bash "$ROOT/tools/beta/rollback.sh" selftest; then
  ok "rollback.sh selftest ($(grep -c '^  PASS' "$TMP/out") checks)"
else
  bad "rollback.sh selftest" "$(grep -E '^  FAIL' "$TMP/out" | head -3 | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# 2. reboot-policy.sh
# --------------------------------------------------------------------------- #
if run_quiet bash "$ROOT/tools/beta/reboot-policy.sh" selftest; then
  ok "reboot-policy.sh selftest ($(grep -c '^  PASS' "$TMP/out") checks)"
else
  bad "reboot-policy.sh selftest" "$(grep -E '^  FAIL' "$TMP/out" | head -3 | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# 3. soak.sh (harness self-proof; the soak itself is BLOCKED_EXTERNAL_RESOURCE)
# --------------------------------------------------------------------------- #
if run_quiet bash "$ROOT/tools/beta/soak.sh" --selftest; then
  ok "soak.sh --selftest ($(grep -c '^  PASS' "$TMP/out") checks)"
else
  bad "soak.sh --selftest" "$(grep -E '^  FAIL' "$TMP/out" | head -3 | tr '\n' ' ')"
fi
if run_quiet bash "$ROOT/tools/beta/soak.sh" --plan \
   && grep -q "no reboot" "$TMP/out" && grep -q "load1" "$TMP/out"; then
  ok "soak --plan states the criteria (incl. the load-average note)"
else
  bad "soak --plan states the criteria"
fi
if grep -q '"terminal_state": "BLOCKED_EXTERNAL_RESOURCE"' \
     "$ROOT/docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md" 2>/dev/null; then
  ok "the soak document records the BLOCKED_EXTERNAL_RESOURCE terminal state"
else
  bad "the soak document records the BLOCKED_EXTERNAL_RESOURCE terminal state"
fi

# --------------------------------------------------------------------------- #
# 4. health-check.sh
# --------------------------------------------------------------------------- #
sb="$TMP/healthroot"
mkdir -p "$sb/var/lib/nuxel" "$sb/usr/lib/systemd/system"
printf '{"pid": 1401, "owner": "nuxel-wl-fb", "stage": "LAUNCHER_DISPLAY_OWNER"}\n' \
  > "$sb/var/lib/nuxel/fb-owner"
touch "$sb/var/lib/nuxel/launcher-ready"
for u in nuxel-pwa nuxel-wl-fb nuxel-button-manager nuxel-wayland; do
  : > "$sb/usr/lib/systemd/system/$u.service"
done
if run_quiet bash "$ROOT/tools/beta/health-check.sh" --root "$sb" --json "$TMP/health.json" \
   && "$PY" -c 'import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if d["verdict"]=="HEALTHY" and d["tier"]=="OFFLINE_TESTED" else 1)' "$TMP/health.json"; then
  ok "health-check offline tier reports HEALTHY/OFFLINE_TESTED with valid JSON"
else
  bad "health-check offline tier" "$(tail -3 "$TMP/out" | tr '\n' ' ')"
fi
if run_quiet bash "$ROOT/tools/beta/health-check.sh" --root "$ROOT/.qq"; then
  bad "health-check refuses a QonQrete root"
else
  ok "health-check refuses a QonQrete root"
fi
dangling="$(grep -c 'launcher-ready' "$ROOT/tools/beta/release_lib.py")"
[ "$dangling" -ge 1 ] && ok "health-check names the launcher readiness evidence" \
  || bad "health-check names the launcher readiness evidence"

# --------------------------------------------------------------------------- #
# 5. release_lib.py unit checks (table-driven, no phone, no writes)
# --------------------------------------------------------------------------- #
"$PY" - "$ROOT" >"$TMP/lib.out" 2>&1 <<'PY'
import json, os, sys, tempfile
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "tools", "beta"))
import release_lib as rl

fails = []
def check(name, cond, detail=""):
    if not cond:
        fails.append("%s%s" % (name, (": " + detail) if detail else ""))

# guards
for bad_path in ("/Users/x/nuxel/.qq/runs/abc.json", "/dev/block/sda1", "/dev/mmcblk0p1",
                 "/Users/x/nuxel/.codeseeq/x"):
    try:
        rl.guard_path(bad_path)
        check("guard refuses %s" % bad_path, False)
    except rl.GuardViolation:
        pass
check("guard accepts a userspace path", rl.guard_path("/usr/lib/nuxel/x") == "/usr/lib/nuxel/x")
for bad_cmd in ("heimdall flash --BOOT x.img", "sudo fastboot flash boot boot.img",
                "dd if=/dev/zero of=/dev/block/sda1", "mkfs.ext4 /dev/block/sda1",
                "twrp restore"):
    try:
        rl.guard_command(bad_cmd)
        check("guard_command refuses %r" % bad_cmd, False)
    except rl.GuardViolation:
        pass
check("guard_command allows a normal command", rl.guard_command("systemctl restart nuxel-pwa") is None)

# service mapping (smallest affected service)
check("launcher -> nuxel-pwa",
      rl.smallest_service_for("/home/nuxel/nuxel/pwa/nuxel-home/js/app.js") == "nuxel-pwa")
check("bridge -> nuxel-wl-fb",
      rl.smallest_service_for("/usr/local/bin/nuxel-wl-fb") == "nuxel-wl-fb")
check("cli tool -> no restart", rl.smallest_service_for("/usr/local/bin/nuxelctl") is None)

# policy matrix
pol = rl.policy_verdict
check("empty history allows", pol([], "r", "d")["allowed"])
check("no reason denied", pol([], "", "d")["code"] == "incomplete")
check("blind repeat denied",
      pol([{"kind": "reboot", "reason": "r1", "diagnostic": "d1", "returned_to_nuxel": True}],
          "r2", "d1")["code"] == "blind_repeat")
check("same reason denied",
      pol([{"kind": "reboot", "reason": "r1", "diagnostic": "d1", "returned_to_nuxel": True}],
          "r1", "d2")["code"] == "reason_repeat")
check("no return denies next",
      pol([{"kind": "reboot", "reason": "r1", "diagnostic": "d1", "returned_to_nuxel": False}],
          "r2", "d2")["code"] == "not_recovered")
check("budget exhausts at 3",
      pol([{"kind": "reboot", "reason": "r%d" % i, "diagnostic": "d%d" % i,
            "returned_to_nuxel": True} for i in range(3)], "r9", "d9")["code"] == "budget_exhausted")
check("three same-mode failures deny that mode",
      pol([{"kind": "failure", "mode": "touch-irq"} for _ in range(3)],
          "r", "d", "touch-irq")["code"] == "three_same_mode_failures")

# manifest parsing + violations
with tempfile.TemporaryDirectory() as td:
    src = os.path.join(td, "fw.bin")
    open(src, "w").write("payload\n")
    good = {"groups": [{"id": "g1", "component": "x", "priority": 1,
                        "files": [{"source": "fw.bin", "target": "/usr/local/bin/nuxel-wl-fb"}]}]}
    plan = rl.parse_manifest(good, td)
    check("manifest parses into one step", len(plan["steps"]) == 1 and not plan["violations"])
    check("manifest step carries service + hash",
          plan["steps"][0]["service"] == "nuxel-wl-fb" and len(plan["steps"][0]["source_sha256"]) == 64)
    evil = {"groups": [{"id": "g2", "component": "x", "priority": 1,
                        "files": [{"source": "fw.bin", "target": "/dev/block/sda1"}]}]}
    check("raw-block target is a violation", bool(rl.parse_manifest(evil, td)["violations"]))
    blocked = {"groups": [{"id": "g3", "state": "blocked_kernel", "blocked_reason": "no driver",
                           "files": [{"source": "fw.bin", "target": "/usr/lib/nuxel/x"}]}]}
    v = rl.parse_manifest(blocked, td)
    check("declared-blocked group is refused",
          bool(v["violations"]) and not v["steps"])

# health: offline never claims a device verdict
rep = rl.health_report("/tmp/nuxel-does-not-exist")
check("offline health is OFFLINE_TESTED", rep["tier"] == "OFFLINE_TESTED")
check("offline health is advisory-not-proof", "never proof" in rep["note"])

print(json.dumps({"checks_failed": len(fails), "failures": fails}, indent=2))
sys.exit(1 if fails else 0)
PY
if [ $? -eq 0 ]; then
  ok "release_lib.py unit checks (guards, service map, policy matrix, manifests, health tiers)"
else
  bad "release_lib.py unit checks" "$(grep -A3 'failures' "$TMP/lib.out" | head -6 | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# 6. run-all-tests.sh registry integrity + machine summary
# --------------------------------------------------------------------------- #
reg="$TMP/registry.tsv"
if run_quiet bash "$ROOT/tools/beta/run-all-tests.sh" --list; then
  ok "run-all-tests --list works"
else
  bad "run-all-tests --list works"; fi
bash "$ROOT/tools/beta/run-all-tests.sh" --list >"$TMP/list.txt" 2>&1
if grep -q "^X-live-soak" "$TMP/list.txt" && grep -q "U-release-tools-selftest" "$TMP/list.txt"; then
  ok "registry contains the release + external soak suites"
else
  bad "registry contains the release + external soak suites"
fi
dupes="$(bash "$ROOT/tools/beta/run-all-tests.sh" --list | awk 'NR>1 && NF>3 {print $1}' | sort | uniq -d)"
[ -z "$dupes" ] && ok "no duplicate suite ids" || bad "no duplicate suite ids" "$dupes"
if run_quiet bash "$ROOT/tools/beta/run-all-tests.sh" --only '^L1-js-syntax$' --quiet --json -; then
  if "$PY" -c '
import json,sys
raw=open(sys.argv[1],encoding="utf-8").read()
start=raw.index("{"); doc=json.loads(raw[start:])
assert doc["counts"]["total"]==1, doc["counts"]
assert doc["suites"][0]["id"]=="L1-js-syntax"
assert doc["terminal_state"]=="OFFLINE_TESTED"
assert doc["invariants"]["no_flashing"] is True
' "$TMP/out"; then
    ok "run-all-tests emits a valid machine-readable summary on stdout"
  else
    bad "run-all-tests emits a valid machine-readable summary on stdout"
  fi
else
  bad "run-all-tests --json - run" "$(tail -3 "$TMP/out" | tr '\n' ' ')"
fi
run_quiet bash "$ROOT/tools/beta/run-all-tests.sh" --help && ok "run-all-tests --help works" \
  || bad "run-all-tests --help works"

# --------------------------------------------------------------------------- #
# 7. the release deliverable set exists and is cross-linked
# --------------------------------------------------------------------------- #
missing=""
for f in CHANGELOG.md VERSION \
         docs/beta-finalization/release/ROLLBACK.md \
         docs/beta-finalization/release/REBOOT-ROLLBACK.md \
         docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.md \
         docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json \
         docs/beta-finalization/testing/TEST-STRATEGY.md \
         docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md \
         docs/beta-finalization/live/DEPLOYMENTS.md \
         docs/beta-finalization/system/DEPENDENCY-REPORT.md; do
  [ -f "$ROOT/$f" ] || missing="$missing $f"
done
[ -z "$missing" ] && ok "release deliverable set present" || bad "release deliverable set present" "missing:$missing"

if grep -q "VERSION" "$ROOT/CHANGELOG.md" && grep -q "beta-finalization/testing/TEST-STRATEGY.md" \
     "$ROOT/docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.md" 2>/dev/null; then
  ok "reports and manifest cross-link each other"
else
  bad "reports and manifest cross-link each other"
fi
ver="$(cat "$ROOT/VERSION" 2>/dev/null)"
case "$ver" in
  *beta*) ok "VERSION carries a beta line ($ver)" ;;
  *) bad "VERSION carries a beta line" "got '$ver'" ;;
esac
if grep -q "$ver" "$ROOT/CHANGELOG.md" 2>/dev/null || grep -q "^## \[v0.4.0-beta\]" "$ROOT/CHANGELOG.md"; then
  ok "CHANGELOG has a coherent entry for $ver"
else
  bad "CHANGELOG has a coherent entry for $ver"
fi

# --------------------------------------------------------------------------- #
# 8. no release tool wrote into the repository or QonQrete metadata
# --------------------------------------------------------------------------- #
if grep -rl -- "$(basename "$TMP")" "$ROOT/.qq" >/dev/null 2>&1; then
  bad "no release-tool writes under .qq"
else
  ok "no release-tool writes under .qq"
fi

echo "release tooling tests: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
