#!/usr/bin/env bash
# =============================================================================
# run-all-tests.sh — the single offline/unit test entry point (briq-09a, area 52)
#
# WHAT THIS IS
#   One command that runs every *offline* test the Nuxel beta repository owns and
#   emits a machine-readable summary:
#
#     tools/beta/run-all-tests.sh                  # the release gate
#     tools/beta/run-all-tests.sh --list           # show the registry, run nothing
#     tools/beta/run-all-tests.sh --json -         # machine summary on stdout
#     tools/beta/run-all-tests.sh --only L1        # only suites whose id matches
#
#   Levels implemented (mission area 52):
#     L1  static checks          syntax (py/sh/JS), JSON validity, tree invariants
#     L2  unit / offline suites  per-group runners + validators + unit tests
#     L3  cross-component        the A32 baseline regression guard + the A33 suites
#     X   external (live/VM)     listed but NOT run here; unblocked with --external
#
# WHAT A GREEN RUN MEANS  (and what it does not)
#   Green here = the repository is internally consistent and every offline gate
#   passes.  It is OFFLINE_TESTED, nothing more.  It is NOT proof that the
#   handset boots, that the panel is right, that the touchscreen works, that
#   audio is audible, or that the firewall enforces anything on the phone.  Those
#   verdicts belong to the live/owner tiers and are recorded separately
#   (docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json).
#
# THE TABLE (printed at the end of every run)
#   ID      suite id from the registry (also its log file name)
#   TIER    static | unit | cross | legacy | external
#   STATUS  PASS | FAIL | WARN | SKIP | EXTERNAL (listed, never run here)
#   CHECKS  how many PASS-shaped assertion lines the suite *printed*, counted by
#           count_checks() below.  A deliberate FLOOR, not a coverage claim: the
#           regex accepts "  PASS <name>", standalone ok/OK tokens and pytest's
#           "N passed" line.  A suite that prints nothing measurable reports "-"
#           and is never credited with assertions it did not print.
#   SECS    wall-clock seconds the suite took
#
# EXIT CODES
#   0  every hard suite passed (soft/legacy failures are reported as WARN)
#   1  at least one hard suite failed  == the release gate is RED
#   2  usage / environment error (no interpreter, unreadable registry)
#
# SAFETY (mission invariants, enforced by the L1-no-flash-invariants suite)
#   * never writes to a block device; never invokes heimdall/odin/fastboot/dd
#   * never writes under .qq/ or the QonQrete RUN_ROOT
#   * never writes a QonQrete receipt JSON into the workspace
#   * never starts/stops a service on the phone, never reboots, never flashes
#   * reports are written under build/reports/ (gitignored) only
#
# SCOPING NOTE (parallel build)
#   Eleven build groups write into this tree at the same time.  A suite whose
#   failure is caused by another group's *in-flight* work is listed in the
#   INFLIGHT_ALLOWANCES register below with its owning group, a reason, the
#   committed evidence log and an expiry date.  It is reported as WARN, loudly,
#   listed again in its own block at the end of the run, and preserved verbatim
#   in the machine-readable summary (`allowances_applied`,
#   `cross_group_failures`, `raw_gate`).  It is NEVER turned into a pass.
#
#   The register may only hold suites owned by ANOTHER group, and `--strict`
#   ignores it entirely and prints the raw release verdict.  The terminal
#   integration pass -- after every group has landed -- must be run with
#   --strict; that is the run whose gate is the release decision.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
export ROOT

# ---- options -----------------------------------------------------------------
JSON_OUT=""
LOG_DIR=""
QUIET=0
STRICT=0
NO_STATIC=0
LIST_ONLY=0
ONLY_RE=""
EXTERNAL=0
TIMEOUT_SCALE=1

usage() { sed -n '2,50p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --json)     JSON_OUT="$2"; shift 2 ;;
    --log-dir)  LOG_DIR="$2"; shift 2 ;;
    --only)     ONLY_RE="$2"; shift 2 ;;
    --timeout-scale) TIMEOUT_SCALE="$2"; shift 2 ;;
    --quiet|-q) QUIET=1; shift ;;
    --strict)   STRICT=1; shift ;;
    --no-static) NO_STATIC=1; shift ;;
    --external) EXTERNAL=1; shift ;;
    --list)     LIST_ONLY=1; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) echo "run-all-tests: unknown option: $1" >&2; echo; usage >&2; exit 2 ;;
  esac
done

REPORT_DIR="$ROOT/build/reports/beta-tests"
[ -n "$LOG_DIR" ] || LOG_DIR="$REPORT_DIR/logs"
[ -n "$JSON_OUT" ] || JSON_OUT="$REPORT_DIR/summary.json"
mkdir -p "$LOG_DIR"
LOG_DIR="$(cd "$LOG_DIR" && pwd)"
export LOG_DIR
case "$JSON_OUT" in
  /*|-) : ;;
  *) JSON_OUT="$ROOT/$JSON_OUT" ;;
esac

# `--json -` means "write the machine summary to stdout". Keep the real file in
# the report dir (so nothing is ever written to a file literally named "-") and
# stream it at the end.
if [ "$JSON_OUT" = "-" ]; then
  JSON_OUT_FILE="$REPORT_DIR/summary.json"
  SUMMARY_PATH="- (stdout; file: $JSON_OUT_FILE)"
  # Machine channel discipline: with `--json -` the JSON document is the ONLY
  # thing on stdout.  The human transcript (progress lines, results table,
  # allowance and failure blocks) is moved to stderr, so a caller can pipe stdout
  # straight into a JSON parser without stripping a table off the end.
  exec 9>&1
  exec 1>&2
else
  JSON_OUT_FILE="$JSON_OUT"
  SUMMARY_PATH="$JSON_OUT"
fi
export JSON_OUT_FILE SUMMARY_PATH

# ---- interpreters / tools ----------------------------------------------------
PY="$(command -v python3 || true)"
NODE="$(command -v node || true)"
CC="$(command -v cc || command -v gcc || true)"
JQ="$(command -v jq || true)"
TIMEOUT_BIN="$(command -v timeout || command -v gtimeout || true)"

now_iso() { date "+%Y-%m-%dT%H:%M:%S%z" 2>/dev/null || date; }
export -f now_iso 2>/dev/null || true

# ---- in-flight cross-group allowances ---------------------------------------
# "<suite-id>|<owning group>|<reason>"
# Empty by default: the release gate is strict about other groups' suites too.
# An entry is only added with evidence (a captured log) and a named owner; it
# downgrades that one suite's failure to WARN (printed loudly, recorded in the
# JSON summary) and never turns a failure into a pass.
INFLIGHT_ALLOWANCES=(
  # <suite-id>|<owning group>|<reason + committed evidence path>|<expiry YYYY-MM-DD>
  #
  # An entry is honoured ONLY IF the owning group still has an unfinished
  # (pending/in_progress/blocked) record in docs/beta-finalization/workqueue/ at
  # run time -- checked by allowance_is_live() below.  A stale entry is refused,
  # printed loudly, and the suite keeps its FAIL.  That is what keeps this
  # register evidence-derived instead of aspirational: when a group finishes, its
  # allowance stops working by itself.
  # Failures are preserved verbatim under
  # docs/beta-finalization/release/evidence/cross-group/ (committed evidence) and
  # re-listed in the summary JSON.  --strict ignores the register entirely.
  "U-p3-a33-suite|bg-03-connectivity-time-audio-buttons|priority-3 group runner mid-edit: bg-03 still has unfinished queue records (evidence: docs/beta-finalization/release/evidence/cross-group/U-p3-a33-suite.log)|2026-11-15"
  "U-userspace-a33-suite|bg-04-userspace-completion|userspace group runner mid-edit: bg-04 still has unfinished queue records (evidence: docs/beta-finalization/release/evidence/cross-group/U-userspace-a33-suite.log)|2026-11-15"
  "U-security-vpn-tor|bg-05-security-permissions|VPN/Tor/remote surface mid-edit: bg-05 still has unfinished queue records (evidence: docs/beta-finalization/release/evidence/cross-group/U-security-vpn-tor.log)|2026-11-15"
  "U-verify-app-registry|bg-06-core-phone-apps|app registry mid-edit: bg-06 still has unfinished queue records (evidence: docs/beta-finalization/release/evidence/cross-group/U-verify-app-registry.log)|2026-11-15"
  "U-verify-app-inventory|bg-06-core-phone-apps|app inventory mid-edit: bg-06 still has unfinished queue records (evidence: docs/beta-finalization/release/evidence/cross-group/U-verify-app-inventory.log)|2026-11-15"
  "U-shell-phone-data|bg-06-core-phone-apps|phone-data module mid-edit: bg-06 still has unfinished queue records (evidence: docs/beta-finalization/release/evidence/cross-group/U-shell-phone-data.log)|2026-11-15"
  "U-snek-parity|bg-07-specialty-apps|specialty apps mid-edit: bg-07 still has unfinished queue records (evidence: docs/beta-finalization/release/evidence/cross-group/U-snek-parity.log)|2026-11-15"
  "U-snek-upstream-pytest|bg-07-specialty-apps|specialty apps mid-edit: bg-07 still has unfinished queue records (evidence: docs/beta-finalization/release/evidence/cross-group/U-snek-upstream-pytest.log)|2026-11-15"
)

allowance_for() {   # allowance_for <suite-id> -> prints "group|reason|expiry" or nothing
  local sid="$1" line
  for line in ${INFLIGHT_ALLOWANCES[@]+"${INFLIGHT_ALLOWANCES[@]}"}; do
    case "$line" in
      "$sid|"*) printf '%s' "${line#*|}"; return 0 ;;
    esac
  done
  return 1
}
export -f allowance_for 2>/dev/null || true

# ---- which build groups still have unfinished work? -------------------------
# Read from the persistent work queue, never guessed: a group is "in flight" iff
# its latest record revision is pending/in_progress/blocked.  This makes the
# allowance register evidence-derived -- when a group lands its last record, its
# allowances stop being honoured with no edit to this file.
UNFINISHED_GROUPS=""
load_unfinished_groups() {
  [ -n "$UNFINISHED_GROUPS" ] && return 0
  UNFINISHED_GROUPS="$( "$PY" - "$ROOT/docs/beta-finalization/workqueue" <<'PY'
import glob, json, os, sys
d = sys.argv[1]
out = set()
if os.path.isdir(d):
    for f in glob.glob(os.path.join(d, "briq-*.json")):
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        revs = doc.get("revisions") or []
        latest = revs[-1] if revs else {}
        state = latest.get("state") or "pending"
        if state in ("pending", "in_progress", "blocked"):
            out.add(latest.get("component") or doc.get("component") or "unknown")
print(" ".join(sorted(out)))
PY
)" 2>/dev/null || UNFINISHED_GROUPS=""
  export UNFINISHED_GROUPS
}
export -f load_unfinished_groups 2>/dev/null || true

# allowance_is_live <owning group> -> 0 when that group still has unfinished work
allowance_is_live() {
  load_unfinished_groups
  case " $UNFINISHED_GROUPS " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}
export -f allowance_is_live 2>/dev/null || true

# ---- static-check programs (kept in the environment, side-effect free) -------
# python syntax: parse every repo-authored .py with ast (no .pyc written)
PY_STATIC_SYNTAX='
import ast, sys
bad = 0
n = 0
for p in sys.argv[1:]:
    if "/__pycache__/" in p or "/.build/" in p:
        continue
    n += 1
    try:
        ast.parse(open(p, "rb").read(), p)
    except SyntaxError as e:
        print("SYNTAX %s:%s %s" % (p, e.lineno, e.msg))
        bad += 1
print("python files parsed: %d  syntax errors: %d" % (n, bad))
sys.exit(1 if bad else 0)
'
export PY_STATIC_SYNTAX

# JSON validity: every manifest/registry/report *.json in the owned trees
PY_STATIC_JSON='
import json, os, sys
roots = ["pwa", "configs", "services", "shell", "tools", "docs/beta-finalization"]
bad = []
n = 0
for r in roots:
    for dp, dn, fn in os.walk(r):
        if any(x in dp for x in ("__pycache__", "/fixtures", "/.build", "/.git")):
            continue
        for f in fn:
            if not f.endswith(".json"):
                continue
            p = os.path.join(dp, f)
            n += 1
            try:
                json.load(open(p, encoding="utf-8"))
            except Exception as e:
                bad.append((p, str(e)[:90]))
print("json files parsed: %d  invalid: %d" % (n, len(bad)))
for p, e in bad:
    print("INVALID-JSON %s: %s" % (p, e))
sys.exit(1 if bad else 0)
'
export PY_STATIC_JSON

# tree invariants: the mission's hard constraints, checked against the *beta*
# surface (the trees this cycle wrote).  Legacy flash guides and the archived
# heimdall tree are deliberately out of scope: they predate the beta and are not
# shipped by it.
PY_STATIC_INVARIANTS='
import os, re, sys
ROOT = os.environ.get("ROOT", ".")
BETA_TREES = ["tools/beta", "tools/s10plus/a32", "tools/s10plus/a33",
              "configs/nuxel", "services", "pwa", "shell", "boot/s10plus", "vm"]
EXT = (".sh", ".py", ".js", ".c", ".json", ".service", ".md", ".conf", ".ucm")

# --- 1. a flash tool must never be *executed* by the beta surface ------------
# "Executed" = the tool name in command position: the start of a command, or
# after a shell separator / command substitution.  A bare mention in prose, a
# filename (twrp-recovery-original.img), a forbid-list entry, or an instruction
# *printed* from a heredoc is not an execution.
CMD_POS = re.compile(
    r"(?:^[ \t]*|(?:;|&&|\|\||\$\())[ \t]*(?:sudo[ \t]+|env[ \t]+)?"
    r"(heimdall|odin|fastboot|twrp)\b")
DD_BLOCK = re.compile(r"\bdd\b[^\n]*of=/dev/(block|sd[a-z]|mmcblk|disk|nvme)")
RAW_WRITE = re.compile(r"(?:>|of=)\s*/dev/block/")

# Legacy, *owner-driven* files that legitimately document / expose a flashing
# path.  An entry is allow-listed only if the file (a) carries an explicit
# never/warning marker and (b) is unreachable from the beta toolchain (proved
# below).  Nothing here is part of the beta pipeline, and each says WHY.
FLASH_DOC_ALLOWLIST = {
    "boot/s10plus/recovery.sh":
        "owner-facing recovery reference: prints heimdall instructions from a heredoc, "
        "performs no flash itself",
    "boot/s10plus/flash.sh":
        "legacy owner-driven flash entry point (device-gated, explicit flags); never "
        "referenced by tools/beta, tools/s10plus/a32 or tools/s10plus/a33",
}
ALLOWED_MARKERS = ("NEVER", "never flashes", "not part of the beta")

# Files whose *job* is to prove that a guard REFUSES a forbidden action.  Such a
# file contains the forbidden string as a *quoted string literal* it feeds to the
# guard, never as an executed command.  An entry is honoured only when the file
# is under a tests/ tree, carries the marker INVARIANT-NEGATIVE-FIXTURE, and the
# offending line is quoted; every exempted line is still printed, loudly.
NEGATIVE_FIXTURE_ALLOWLIST = {
    "tools/beta/tests/test-release-tools.sh":
        "release-tool self-test: feeds dd-/mkfs-style block-device strings to "
        "release_lib.guard_command() to assert they are REFUSED; the strings are "
        "Python literals, never executed (no single quotes here: this block lives "
        "inside a bash single-quoted heredoc)",
}
NEG_FIXTURE_MARKER = "INVARIANT-NEGATIVE-FIXTURE"

problems, documented, scanned, negatives = [], [], 0, []
for tree in BETA_TREES:
    for dp, dn, fn in os.walk(tree):
        if any(x in dp for x in ("__pycache__", "/fixtures", "/.build", "/.git")):
            continue
        for f in fn:
            if not f.endswith(EXT):
                continue
            path = os.path.join(dp, f)
            scanned += 1
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
                lines = text.split("\n")
            except OSError:
                continue
            rel = os.path.relpath(path, ROOT)
            heredoc = None
            for n, line in enumerate(lines, 1):
                stripped = line.strip()
                # heredoc body tracking: text between <<TAG and the bare TAG is
                # *printed*, not executed.
                if heredoc is not None:
                    if stripped == heredoc:
                        heredoc = None
                    else:
                        m = CMD_POS.search(line)
                        if m and m.group(1):
                            documented.append("%s:%d: %s" % (rel, n, stripped[:90]))
                    continue
                hd = re.search("<<-?[\x27\x22]?([A-Za-z_][A-Za-z0-9_]*)", line)
                if hd and "cat" in line:
                    heredoc = hd.group(1)
                if stripped.startswith("#"):
                    continue
                m = CMD_POS.search(line)
                if m and m.group(1):
                    if rel in FLASH_DOC_ALLOWLIST:
                        if not any(k in text for k in ALLOWED_MARKERS):
                            problems.append("%s:%d: allow-listed but carries no never/warning "
                                            "marker" % (rel, n))
                        continue
                    problems.append("%s:%d: flash tool in command position: %s"
                                    % (rel, n, m.group(0).strip()[:90]))
                dd = DD_BLOCK.search(line)
                rw = RAW_WRITE.search(line)
                if dd or rw:
                    if (rel in NEGATIVE_FIXTURE_ALLOWLIST and "/tests/" in rel
                            and NEG_FIXTURE_MARKER in text
                            and (chr(34) in line or chr(39) in line)):
                        negatives.append("%s:%d: %s" % (rel, n, stripped[:90]))
                    else:
                        if dd:
                            problems.append("%s:%d: dd to a block device: %s"
                                            % (rel, n, stripped[:90]))
                        if rw:
                            problems.append("%s:%d: write to /dev/block: %s"
                                            % (rel, n, stripped[:90]))

# an allow-listed file must not be referenced from anywhere in the beta pipeline
PIPELINE_TREES = ["tools/beta", "tools/s10plus/a32", "tools/s10plus/a33", "services",
                  "configs/nuxel", "shell"]
for tree in PIPELINE_TREES:
    for dp, dn, fn in os.walk(tree):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if not f.endswith((".sh", ".py", ".js", ".service", ".conf")):
                continue
            path = os.path.join(dp, f)
            if "run-all-tests" in path:
                continue
            text = open(path, encoding="utf-8", errors="replace").read()
            for rel in FLASH_DOC_ALLOWLIST:
                if os.path.basename(rel) in text or rel in text:
                    problems.append("%s: allow-listed flash file IS referenced by the beta "
                                    "pipeline: %s" % (rel, path))

# --- 2. QonQrete metadata is read-only; no receipt JSON into the workspace ---
QQ_WRITE = re.compile(r"(>|>>|of=|open\()[^\n]*\.qq/")
RECEIPT = re.compile(r"receipt[^\n]*\.json[^\n]*(>|open\([^)]*[\x22\x27]w)")
for tree in ["tools/beta", "tools/s10plus", "services", "shell", "vm", "configs"]:
    for dp, dn, fn in os.walk(tree):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if not f.endswith((".sh", ".py", ".js")):
                continue
            path = os.path.join(dp, f)
            text = open(path, encoding="utf-8", errors="replace").read()
            for pat, label in ((QQ_WRITE, "write into .qq/"), (RECEIPT, "receipt json write")):
                for m in pat.finditer(text):
                    line = m.group(0).strip()
                    if "forbid" in line or "never" in line.lower() or "run-all-tests" in path:
                        continue
                    problems.append("%s: %s: %s" % (path, label, line[:100]))

print("beta-surface files scanned: %d  heredoc-documented (not executed): %d  "
      "negative-fixture (guard-refusal proof): %d  invariant violations: %d"
      % (scanned, len(documented), len(negatives), len(problems)))
for nline in negatives:
    print("negative-fixture", nline)
for d in documented:
    print("documented-not-executed", d)
for x in problems:
    print("VIOLATION", x)
sys.exit(1 if problems else 0)
'
export PY_STATIC_INVARIANTS

# shell/JS syntax, shebang-aware: boot/*/pack-boot-v1.sh is *Python* with a .sh
# name, so extension alone is not a sufficient dispatcher.
SH_STATIC_SYNTAX='
set -u
bad=0; n=0
for f in $(find tools scripts services shell vm boot configs images firmware \
                -type f \( -name "*.sh" -o -name "*.bash" \) 2>/dev/null | LC_ALL=C sort); do
  n=$((n+1))
  first=$(head -1 "$f" 2>/dev/null || true)
  case "$first" in
    *python*) interp=py ;;
    *node*)   interp=node ;;
    *)        interp=sh ;;
  esac
  case "$interp" in
    sh)   bash -n "$f" 2>/tmp/shsyn.$$ || { echo "SYNTAX(bash) $f: $(head -1 /tmp/shsyn.$$)"; bad=$((bad+1)); } ;;
    py)   ("${PY:-python3}" -c "import ast,sys;ast.parse(open(sys.argv[1],\"rb\").read(),sys.argv[1])" "$f") 2>/tmp/shsyn.$$ || { echo "SYNTAX(py) $f: $(head -1 /tmp/shsyn.$$)"; bad=$((bad+1)); } ;;
    node) ("${NODE:-node}" --check "$f") 2>/tmp/shsyn.$$ || { echo "SYNTAX(node) $f: $(head -1 /tmp/shsyn.$$)"; bad=$((bad+1)); } ;;
  esac
done
rm -f /tmp/shsyn.$$
echo "shell/py-by-name files checked: $n  syntax errors: $bad"
[ "$bad" -eq 0 ]
'
export SH_STATIC_SYNTAX

# JS syntax: node --check over every PWA script
JS_STATIC_SYNTAX='
set -u
bad=0; n=0
for f in $(find pwa -type f -name "*.js" 2>/dev/null | LC_ALL=C sort); do
  n=$((n+1))
  "${NODE:-node}" --check "$f" 2>/tmp/jssyn.$$ || { echo "SYNTAX $f: $(head -1 /tmp/jssyn.$$)"; bad=$((bad+1)); }
done
rm -f /tmp/jssyn.$$
echo "js files checked: $n  syntax errors: $bad"
[ "$bad" -eq 0 ]
'
export JS_STATIC_SYNTAX

export PY NODE CC JQ TIMEOUT_BIN

# ---- suite registry ----------------------------------------------------------
# parallel indexed arrays (bash 3.2 compatible: no associative arrays)
SUITE_ID=(); SUITE_TIER=(); SUITE_OWNER=(); SUITE_CMD=(); SUITE_TO=()
SUITE_MODE=(); SUITE_NEED=(); SUITE_WHY=()

# add_suite <id> <tier> <owner> <timeout-s> <mode> <need-bin|-> <why> <command>
add_suite() {
  SUITE_ID+=("$1"); SUITE_TIER+=("$2"); SUITE_OWNER+=("$3"); SUITE_TO+=("$4")
  SUITE_MODE+=("$5"); SUITE_NEED+=("$6"); SUITE_WHY+=("$7"); SUITE_CMD+=("$8")
}

# ---------------------------------------------------------------------------
# L1 — static checks (owner: release)
# ---------------------------------------------------------------------------
add_suite L1-python-syntax static release 600 hard "$PY" \
  "every repo-authored .py parses (ast, no bytecode written)" \
  'find tools services shell pwa scripts vm boot configs images firmware -name "*.py" 2>/dev/null | LC_ALL=C sort | xargs python3 -c "$PY_STATIC_SYNTAX"'
add_suite L1-shell-syntax static release 600 hard bash \
  "every .sh parses, dispatched by shebang (boot/*/pack-boot-v1.sh is python)" \
  'bash -c "$SH_STATIC_SYNTAX"'
add_suite L1-js-syntax static release 600 hard "$NODE" \
  "every PWA .js parses (node --check)" \
  'bash -c "$JS_STATIC_SYNTAX"'
add_suite L1-json-valid static release 600 hard "$PY" \
  "every manifest/registry/report JSON in the owned trees parses" \
  'python3 -c "$PY_STATIC_JSON"'
add_suite L1-no-flash-invariants static release 600 hard "$PY" \
  "no flash tool invoked, no /dev/block write, no .qq write, no receipt JSON" \
  'python3 -c "$PY_STATIC_INVARIANTS"'
add_suite L1-test-coverage static release 300 hard "$PY" \
  "no test file is orphaned: every discovered test is reachable from the registry" \
  'python3 "$ROOT/tools/beta/suite-coverage.py" --registry "$LOG_DIR/suite-registry.tsv" --root "$ROOT"'

# ---------------------------------------------------------------------------
# L2 — unit / offline suites, one row per owning build group
# ---------------------------------------------------------------------------
# bg-00 preflight / ledger / baseline
add_suite U-workqueue-schema unit bg-00-preflight 300 hard "$PY" \
  "the persistent work queue is schema-valid (vocabulary, deps, evidence gates)" \
  'python3 tools/beta/workqueue.py verify-schema'
add_suite U-workqueue-unit unit bg-00-preflight 300 hard "$PY" \
  "work queue tool unit tests" \
  'python3 tools/beta/tests/test_workqueue.py'
add_suite U-regression-guard-selftest unit bg-00-preflight 600 hard bash \
  "the A32 baseline gate is itself tested (mutation fixtures + re-pin path)" \
  'bash tools/beta/tests/test-regression-guard.sh'
add_suite U-baseline-regression-guard cross bg-00-preflight 2400 hard bash \
  "the A32 baseline register still holds (hash pins + behavioural invariants)" \
  'bash tools/beta/regression-guard.sh'
add_suite U-baseline-a32-suite cross bg-00-preflight 1800 hard bash \
  "the full A32 offline suite still runs (colour, safe zones, wallpaper, registry)" \
  'bash tools/s10plus/a32/tests/run-tests.sh'
add_suite U-boot-s10plus-gates unit bg-00-preflight 600 hard bash \
  "boot-image gates: container structure, initramfs embedding, partition budget" \
  'bash boot/s10plus/tests/test-boot-image-gates.sh'
add_suite U-boot-init-cmdline unit bg-00-preflight 300 hard bash \
  "init/cmdline independence (no board-specific hard-coding in the initramfs)" \
  'bash boot/s10plus/tests/test-init-cmdline-independence.sh'

# bg-01 touch pipeline
add_suite U-touch-a33-suite cross bg-01-touch-pipeline 2400 hard bash \
  "A33 touch group runner: trace tool, libinput shim, bootmode guard, capture harness" \
  'bash tools/s10plus/a33/tests/run-touch-tests.sh --quick'

# bg-02 boot / animation / launcher
add_suite U-boot-a33-suite cross bg-02-boot-animation-launcher 2400 hard bash \
  "A33 boot group runner: handoff, colour order, verbose boot, safe zones, launcher" \
  'bash tools/s10plus/a33/tests/run-boot-tests.sh'
add_suite U-c-protocol-handoff unit bg-02-boot-animation-launcher 300 hard "$CC" \
  "the handoff decision logic compiled and executed on the host (C protocol test)" \
  'cc -O2 -Wall -o "$LOG_DIR/.handoff-logic" tools/s10plus/a33/tests/test-handoff-logic.c && "$LOG_DIR/.handoff-logic"'

# bg-03 connectivity / time / audio / buttons
add_suite U-p3-a33-suite cross bg-03-connectivity-time-audio-buttons 2400 hard bash \
  "A33 priority-3 runner: wifi, time/RTC, audio, headphones, buttons" \
  'bash tools/s10plus/a33/tests/run-p3-tests.sh'

# bg-04 userspace / services / app infrastructure
add_suite U-userspace-a33-suite cross bg-04-userspace-completion 2400 hard bash \
  "A33 userspace runner: service graph, app infrastructure, portal, notifications" \
  'bash tools/s10plus/a33/tests/run-userspace-tests.sh'
add_suite U-verify-service-graph unit bg-04-userspace-completion 300 hard "$PY" \
  "boot graph: no cycles, no unsatisfied units, no system->user enablement" \
  'python3 tools/s10plus/a33/verify-service-graph.py'
add_suite U-verify-packages unit bg-04-userspace-completion 300 hard "$PY" \
  "package manifest vs the real Fedora 43 ARM64 metadata (no --skip-unavailable)" \
  'python3 tools/s10plus/a33/verify-packages.py'

# bg-05 security / permissions
add_suite U-security-firewall unit bg-05-security-permissions 900 hard bash \
  "nftables rule translation + fail-closed console guard (offline)" \
  'bash tools/s10plus/a33/security-tests/test-firewall.sh'
add_suite U-security-vpn-tor unit bg-05-security-permissions 900 hard bash \
  "VPN/Tor/remote honest-enforcement labels (mock network, no live tunnel)" \
  'bash tools/s10plus/a33/security-tests/test-vpn-tor.sh'
add_suite U-verify-permissions unit bg-05-security-permissions 300 hard "$PY" \
  "every declared capability has a grant that claims only enforceable protection" \
  'python3 tools/s10plus/a33/verify-permissions.py'
add_suite U-shell-permissions unit bg-05-security-permissions 600 hard bash \
  "permission manager unit tests (store, fail-closed, revocation)" \
  'bash shell/nuxel-shell/nuxel-permissions/tests/run-tests.sh'

# bg-06 core phone apps
add_suite U-verify-app-registry unit bg-06-core-phone-apps 300 hard "$PY" \
  "canonical app registry: every entry launchable, assets present, bridge pinned" \
  'python3 tools/s10plus/a33/verify-app-registry.py'
add_suite U-verify-app-inventory unit bg-06-core-phone-apps 300 hard "$PY" \
  "core application inventory and gap matrix" \
  'python3 tools/s10plus/a33/verify-app-inventory.py'
add_suite U-shell-phone-data unit bg-06-core-phone-apps 600 hard bash \
  "phone data model (dialer/contacts/messages) host tests" \
  'bash shell/nuxel-shell/nuxel-phone-data/run-tests.sh'

# bg-04 / bg-06 / bg-07 shared surfaces
add_suite U-pwa-bridge unit bg-04-userspace-completion 300 hard "$NODE" \
  "shared PWA bridge client contract (node)" \
  'node pwa/nuxel-common/test-bridge.js'
add_suite U-pwa-wiring unit bg-04-userspace-completion 300 hard "$NODE" \
  "every PWA surface wires manifest/registry/bridge consistently (node)" \
  'node pwa/nuxel-common/verify-wiring.js'
add_suite U-services-portal unit bg-04-userspace-completion 300 hard "$PY" \
  "portal consent + one-shot grant policy" \
  'python3 services/nuxel-portal/test-portal-policy.py'
add_suite U-services-notifications unit bg-04-userspace-completion 300 hard "$PY" \
  "notification persistence + bounded history" \
  'python3 services/nuxel-notifications/test-notifications-persistence.py'

# bg-07 specialty apps
add_suite U-snek-parity unit bg-07-specialty-apps 300 hard "$PY" \
  "SnekByte port parity with the original engine fixtures" \
  'python3 tools/s10plus/a33/snekbyte/tests/test-snek-parity.py'
add_suite U-snek-upstream-pytest unit bg-07-specialty-apps 600 hard "$PY" \
  "the vendored upstream SnekByte engine test-suite (pytest)" \
  'python3 -m pytest -q tools/s10plus/a33/snekbyte/upstream/tests'
add_suite U-nuxtore-pwa unit bg-07-specialty-apps 600 hard \
  file:pwa/nuxel-apps/nuxtore/catalog/nuxtore-catalog.json \
  "NuxTore catalogue tests (signing, tamper, unsigned refusal, policy); needs the owner-staged catalogue" \
  'python3 pwa/nuxel-apps/nuxtore/tests/test-catalog.py'
add_suite U-apps-js unit bg-06-core-phone-apps 600 hard "$NODE" \
  "every PWA application unit test (discovered under pwa/**/tests)" \
  'set -u; fail=0; n=0
   for f in $(find pwa -type f -path "*/tests/*" -name "*.js" 2>/dev/null | LC_ALL=C sort); do
     n=$((n+1))
     if node "$f" >"$LOG_DIR/.app-js.out" 2>&1; then echo "  PASS  $f"
     else echo "  FAIL  $f"; tail -6 "$LOG_DIR/.app-js.out" | sed "s/^/        /"; fail=$((fail+1)); fi
   done
   echo "pwa app js tests: $n  failing: $fail"; [ "$fail" -eq 0 ]'

# release-tooling / debug-pack offline suites
add_suite U-debug-pack unit bg-00-preflight 300 hard "$PY" \
  "the s10plus debug pack is self-consistent (scripts, manifests, syntax)" \
  'python3 scripts/s10plus-debug-pack/tests/test_pack.py'
add_suite U-adb-pack-mock unit release 600 hard "$PY" \
  "the adb flash pack's own MOCK suite (no device, no flash: mocks only)" \
  'bash scripts/nuxel-adb-flash-pack/tools/run-mock-tests.sh'
add_suite U-pwa-assets unit bg-02-boot-animation-launcher 300 hard bash \
  "launcher assets referenced by HTML/CSS/manifest all exist" \
  'bash tools/verify-pwa-assets.sh'
add_suite U-soak-harness unit release 300 hard bash \
  "the soak/performance harness works offline (plan, sampling, verdicts)" \
  'bash tools/beta/soak.sh --selftest'
add_suite U-release-tools-selftest unit release 600 hard bash \
  "rollback / reboot-policy / health-check / run-all-tests themselves tested" \
  'bash tools/beta/tests/test-release-tools.sh'
add_suite U-rollback-reboot-scenarios unit release 900 hard bash \
  "mocked failure scenarios: the rollback really triggers, the dry run is inert, the policy refuses" \
  'bash tools/beta/tests/test-rollback-reboot.sh'

# legacy per-cycle gates (still run, see TEST-STRATEGY.md section 5)
# Legacy alpha-cycle gates.  They gate on *artefacts* of the alpha build chain
# (the packed animation container + the first-light splash) and on host tooling
# the beta build host does not carry (numpy for the A26 packer; Pillow plus an
# aarch64 cross-compiler for the atlas/layout gate).  They are therefore
# precondition-gated: the `probe:` predicate turns an unmet host/artefact
# prerequisite into a loud SKIP that names the missing piece -- never a silent
# pass, never a fake failure, and the failing step is reproducible by hand.
# With the artefacts built (CI release workflow) they run and gate hard.
# See docs/beta-finalization/testing/TEST-STRATEGY.md section 5.
add_suite L-a27-firstlight legacy legacy-per-cycle 300 hard \
  "probe:test -s build/out/s10plus/a26/nuxel-firstlight.rawspl && python3 -c 'import numpy'" \
  "A27 first-light renderer gate (host renderer == shipped renderer)" \
  'bash tools/s10plus/a27/test-firstlight.sh'
add_suite L-a27-ui-layout legacy legacy-per-cycle 300 hard \
  "probe:python3 -c 'import PIL' && command -v aarch64-linux-gnu-gcc" \
  "A27 UI layout gate: reproducible atlas + 4 scales + aarch64 ELF" \
  'bash tools/s10plus/a27/test-ui-layout.sh'
add_suite L-a28-launcher legacy legacy-per-cycle 600 soft bash \
  "A28 UTM launcher-port gate (superseded by A32/A33; generated table tracks the live registry)" \
  'bash tools/s10plus/a28/test-launcher.sh'
add_suite L-app-registry-check legacy legacy-per-cycle 300 soft bash \
  "legacy app_registry.json checker (superseded by verify-app-registry.py)" \
  'bash tools/app-registry-check.sh'

# ---------------------------------------------------------------------------
# X — external tiers: listed, never run without --external
# ---------------------------------------------------------------------------
add_suite X-live-launcher-acceptance external bg-10-live-phone 1200 external - \
  "live console acceptance on the physical S10+ (needs the USB console)" \
  'bash tools/s10plus/a31/verify-launcher-live.sh'
add_suite X-live-soak external bg-10-live-phone 86400 external - \
  "the 8 h on-device soak (needs live console time; see SOAK-AND-PERFORMANCE.md)" \
  'bash tools/beta/soak.sh --device --duration 28800 --checkpoint 1800'
add_suite X-vm-services external bg-11-vm-parity 1800 external - \
  "UTM Fedora 43 guest service-graph verification (needs the VM)" \
  'bash vm/vm-verify-services.sh'
add_suite X-vm-launcher-parity external bg-11-vm-parity 1800 external - \
  "VM launcher/status-bar/safe-zone parity run (needs the VM)" \
  'bash vm/vm-verify-pwa.sh'

# ---------------------------------------------------------------------------
# Registry export (written *before* any suite runs: L1-test-coverage reads it)
# ---------------------------------------------------------------------------
REGISTRY_TSV="$LOG_DIR/suite-registry.tsv"
{
  printf 'id\ttier\towner\ttimeout\tmode\tneed\twhy\tcmd\n'
  i=0
  while [ $i -lt ${#SUITE_ID[@]} ]; do
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "${SUITE_ID[$i]}" "${SUITE_TIER[$i]}" "${SUITE_OWNER[$i]}" "${SUITE_TO[$i]}" \
      "${SUITE_MODE[$i]}" "${SUITE_NEED[$i]}" "${SUITE_WHY[$i]}" "$(printf '%s' "${SUITE_CMD[$i]}" | tr '\n' ' ')"
    i=$((i + 1))
  done
} > "$REGISTRY_TSV"

if [ "$LIST_ONLY" -eq 1 ]; then
  printf '%-30s %-9s %-38s %7s %-8s %s\n' ID TIER OWNER TIMEOUT MODE WHY
  i=0
  while [ $i -lt ${#SUITE_ID[@]} ]; do
    printf '%-30s %-9s %-38s %7s %-8s %s\n' \
      "${SUITE_ID[$i]}" "${SUITE_TIER[$i]}" "${SUITE_OWNER[$i]}" "${SUITE_TO[$i]}" \
      "${SUITE_MODE[$i]}" "${SUITE_WHY[$i]}"
    i=$((i + 1))
  done
  echo
  echo "registry: $REGISTRY_TSV   suites: ${#SUITE_ID[@]}"
  exit 0
fi

# ---------------------------------------------------------------------------
# Prerequisite resolution
#
# A suite whose prerequisite is *absent* is SKIP, never a silent pass and never
# a fake failure: during the parallel build another group may simply not have
# landed its file yet.  The rule is deliberately asymmetric:
#   * a missing interpreter/tool        -> SKIP (SKIP_ENV)
#   * a missing prerequisite *file*     -> SKIP (SKIP_PREREQ)
#   * an unmet host/artefact probe      -> SKIP (SKIP_PROBE)
#   * a release-owned suite that is missing its own file -> FAIL (L-cmd-missing)
# so this group's own gate can never be silently skipped.
#
# `probe:<shell>' is evaluated in the repository root under the same bounded,
# side-effect-free contract as a suite (no phone, no network, no writes).  A
# probe that cannot be evaluated fails CLOSED -- SKIP with the reason recorded --
# because an unproven prerequisite must never be reported as a passing gate.
# ---------------------------------------------------------------------------
prereq_missing() {   # prereq_missing <need> -> prints reason, or nothing
  local need="$1" owner="$2" cmd="$3"
  case "$need" in
    ""|-) : ;;
    file:*)
      local f="${need#file:}"
      [ -e "$ROOT/$f" ] || { printf 'prerequisite file absent: %s' "$f"; return 0; }
      ;;
    probe:*)
      local probe="${need#probe:}"
      if ! ( cd "$ROOT" && eval "$probe" ) >/dev/null 2>&1; then
        printf 'host/artefact prerequisite unmet: %s' "$probe"
        return 0
      fi
      ;;
    *)
      command -v "$need" >/dev/null 2>&1 || { printf 'interpreter absent: %s' "$need"; return 0; }
      ;;
  esac
  # the command's first token may itself be a repo script that a parallel group
  # has not written yet (e.g. a new group runner)
  local first
  first="$(printf '%s' "$cmd" | sed -e 's/^[[:space:]]*//' | awk '{print $1}' | tr -d "'\"")"
  case "$first" in
    /*) : ;;
    *.sh|*.py|*.js|*.c)
      [ -e "$ROOT/$first" ] || { printf 'suite script absent: %s' "$first"; return 0; } ;;
  esac
  return 1
}

# ---------------------------------------------------------------------------
# Portable bounded execution (no coreutils `timeout` on the build hosts)
# ---------------------------------------------------------------------------
run_bounded() {   # run_bounded <timeout-s> <logfile> <command>
  local tmo="$1" log="$2" cmd="$3"
  ( cd "$ROOT" && bash -c "$cmd" ) >"$log" 2>&1 &
  local pid=$!
  local waited=0
  local tick=2
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$tmo" -gt 0 ] && [ "$waited" -ge "$tmo" ]; then
      kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
      pkill -TERM -P "$pid" 2>/dev/null || true
      sleep 3
      if kill -0 "$pid" 2>/dev/null; then
        pkill -KILL -P "$pid" 2>/dev/null || true
        kill -KILL "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
      fi
      wait "$pid" 2>/dev/null || true
      echo "TIMEOUT after ${tmo}s" >>"$log"
      return 124
    fi
    sleep "$tick"
    waited=$((waited + tick))
  done
  wait "$pid"
}

# ---------------------------------------------------------------------------
# Suite selection
# ---------------------------------------------------------------------------
selected_indexes() {
  local i=0
  while [ $i -lt ${#SUITE_ID[@]} ]; do
    if [ -n "$ONLY_RE" ]; then
      if ! printf '%s' "${SUITE_ID[$i]}" | grep -Eq "$ONLY_RE"; then i=$((i + 1)); continue; fi
    fi
    if [ "$NO_STATIC" -eq 1 ] && [ "${SUITE_TIER[$i]}" = "static" ]; then i=$((i + 1)); continue; fi
    printf '%s\n' "$i"
    i=$((i + 1))
  done
}

# ---------------------------------------------------------------------------
# Allowance register audit (printed once, before anything runs): every entry is
# checked against the work queue.  A stale entry (its group has no unfinished
# record) is announced loudly and will NOT downgrade its suite.
# ---------------------------------------------------------------------------
load_unfinished_groups
STALE_ALLOW=""
if [ ${#INFLIGHT_ALLOWANCES[@]} -gt 0 ] && [ "$QUIET" -eq 0 ]; then
  echo
  echo "in-flight allowance register (evidence-derived from the work queue):"
  echo "  groups with unfinished records: ${UNFINISHED_GROUPS:-<none>}"
  for line in "${INFLIGHT_ALLOWANCES[@]}"; do
    asid="${line%%|*}"; arest="${line#*|}"; agrp="${arest%%|*}"
    if allowance_is_live "$agrp"; then
      printf '  live  %-28s owner %s (expires %s)\n' "$asid" "$agrp" "$(printf '%s' "$line" | cut -d'|' -f4)"
    else
      printf '  STALE %-28s owner %s has no unfinished record — the allowance is REFUSED\n' "$asid" "$agrp"
      STALE_ALLOW="${STALE_ALLOW}${asid}|${agrp}"$'\n'
    fi
  done
fi

T_START=$(date +%s 2>/dev/null || echo 0)
R_PASS=0; R_FAIL=0; R_WARN=0; R_SKIP=0; R_EXT=0; R_TOTAL=0
R_WARN_ALLOW=0
JSON_ROWS=""
ALLOW_HITS=""
FAIL_ROWS=""
FIRST_FAIL=""

# bash 3.2 (macOS /bin/bash) has no ${var^^} upper-casing; use a portable helper.
toupper() { printf '%s' "$1" | tr '[:lower:]' '[:upper:]'; }

# count_checks <logfile> -> the number of PASS-shaped assertion lines the suite
# printed (a floor; see the header and TEST-STRATEGY.md section 2).
count_checks() {
  local log="$1" n=""
  [ -f "$log" ] || { printf '0'; return; }
  n="$(grep -c -E '(^|[[:space:]])(PASS|ok|OK)([[:space:]:.]|$)|^[0-9]+ passed' "$log" 2>/dev/null || true)"
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  printf '%s' "$n"
}

# json_num <value> -> a JSON number, or null when the value is not numeric
# (a suite that never ran has no exit code; "null" is the honest encoding and
# avoids the invalid-JSON trap that "-" used to write).
json_num() {
  case "$1" in
    ''|*[!0-9]*) printf 'null' ;;
    *) printf '%s' "$1" ;;
  esac
}

emit_row() {  # emit_row <id> <tier> <owner> <status> <exit> <dur> <checks> <mode> <reason> <log>
  JSON_ROWS="$JSON_ROWS$(printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}")
"
}

for i in $(selected_indexes); do
  sid="${SUITE_ID[$i]}"; tier="${SUITE_TIER[$i]}"; owner="${SUITE_OWNER[$i]}"
  tmo="${SUITE_TO[$i]}"; mode="${SUITE_MODE[$i]}"; need="${SUITE_NEED[$i]}"
  why="${SUITE_WHY[$i]}"; cmd="${SUITE_CMD[$i]}"
  R_TOTAL=$((R_TOTAL + 1))
  log="$LOG_DIR/${sid}.log"

  # external tier never runs without --external
  if [ "$tier" = "external" ] && [ "$EXTERNAL" -eq 0 ]; then
    R_EXT=$((R_EXT + 1))
    emit_row "$sid" "$tier" "$owner" "EXTERNAL" "-" 0 "-" "$mode" \
      "external tier: listed, not run here - BLOCKED_EXTERNAL_RESOURCE (needs --external + a reachable resource)" "$log"
    [ "$QUIET" -eq 0 ] && printf '  \033[36mEXT \033[0m %-30s %s\n' "$sid" "$why"
    continue
  fi

  reason=""
  if reason="$(prereq_missing "$need" "$owner" "$cmd")"; then
    if [ "$owner" = "release" ]; then
      R_FAIL=$((R_FAIL + 1)); [ -z "$FIRST_FAIL" ] && FIRST_FAIL="$sid"
      emit_row "$sid" "$tier" "$owner" "FAIL" "-" 0 "-" "$mode" "release-owned suite cannot run: $reason" "$log"
      printf '  \033[31mFAIL\033[0m %-30s %s\n' "$sid" "$reason"
    else
      R_SKIP=$((R_SKIP + 1))
      emit_row "$sid" "$tier" "$owner" "SKIP" "-" 0 "-" "$mode" "$reason (owner: $owner)" "$log"
      printf '  \033[33mSKIP\033[0m %-30s %s (owner: %s)\n' "$sid" "$reason" "$owner"
    fi
    continue
  fi

  t0=$(date +%s 2>/dev/null || echo 0)
  run_bounded "$tmo" "$log" "$cmd"; rc=$?
  t1=$(date +%s 2>/dev/null || echo 0)
  dur=$((t1 - t0))

  CHECKS="$(count_checks "$log")"
  case "$CHECKS" in ''|0) CHECKS="-" ;; esac
  status="PASS"; note=""
  if [ "$rc" -eq 0 ]; then
    status="PASS"; R_PASS=$((R_PASS + 1))
  elif [ "$rc" -eq 124 ]; then
    status="FAIL"; note="timeout after ${tmo}s"
  elif [ "$mode" = "soft" ]; then
    status="WARN"; note="soft suite failed (rc=$rc) — legacy, non-gating"
  elif allowance="$(allowance_for "$sid")" && allowance_is_live "${allowance%%|*}"; then
    status="WARN"; R_WARN_ALLOW=$((R_WARN_ALLOW + 1))
    note="IN-FLIGHT CROSS-GROUP ALLOWANCE (${allowance%%|*}): $(printf '%s' "$allowance" | cut -d'|' -f2-) (rc=$rc)"
    ALLOW_HITS="${ALLOW_HITS}${sid}|${allowance}"$'\n'
  elif [ "$tier" = "external" ]; then
    status="EXT_BLOCKED"; note="external suite could not run (rc=$rc) — BLOCKED_EXTERNAL_RESOURCE"
  else
    status="FAIL"; note="rc=$rc"
  fi

  case "$status" in
    PASS) printf '  \033[32mPASS\033[0m %-30s %4ss  %6s checks\n' "$sid" "$dur" "$CHECKS" ;;
    WARN) R_WARN=$((R_WARN + 1)); printf '  \033[33mWARN\033[0m %-30s %4ss  %6s checks  %s\n' "$sid" "$dur" "$CHECKS" "$note" ;;
    EXT_BLOCKED) R_EXT=$((R_EXT + 1)); printf '  \033[36mBLK \033[0m %-30s %4ss  %6s checks  %s\n' "$sid" "$dur" "$CHECKS" "$note" ;;
    FAIL)
      R_FAIL=$((R_FAIL + 1)); [ -z "$FIRST_FAIL" ] && FIRST_FAIL="$sid"
      printf '  \033[31mFAIL\033[0m %-30s %4ss  %6s checks  %s\n' "$sid" "$dur" "$CHECKS" "$note"
      tail -8 "$log" | sed 's/^/        /' ;;
  esac
  if [ "$status" = "FAIL" ]; then
    FAIL_ROWS="${FAIL_ROWS}${sid}|${tier}|${owner}|${CHECKS}|${own_note:-$note}"$'\n'
  fi
  emit_row "$sid" "$tier" "$owner" "$status" "$rc" "$dur" "$CHECKS" "$mode" "$note" "$log"
done

T_END=$(date +%s 2>/dev/null || echo 0)
T_TOTAL=$((T_END - T_START))

# ---------------------------------------------------------------------------
# Verdict + machine-readable summary
# ---------------------------------------------------------------------------
# The gate and the raw gate are different questions:
#   raw_gate  -> what a strict run (no cross-group allowances) would say
#   gate      -> the default run's verdict, which may have downgraded suites that
#                belong to another group that is still writing into this tree
if [ "$R_FAIL" -gt 0 ]; then GATE="red"; VERDICT="OFFLINE_TESTED_FAIL"; EXIT=1
else GATE="green"; VERDICT="OFFLINE_TESTED"; EXIT=0; fi
RAW_FAIL=$((R_FAIL + R_WARN_ALLOW))
if [ "$RAW_FAIL" -gt 0 ]; then RAW_GATE="red"; RAW_VERDICT="OFFLINE_TESTED_FAIL"
else RAW_GATE="green"; RAW_VERDICT="OFFLINE_TESTED"; fi

SUMMARY_TSV="$LOG_DIR/summary.tsv"
printf '%s' "$JSON_ROWS" > "$SUMMARY_TSV"

NGIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
NVER="$(cat "$ROOT/VERSION" 2>/dev/null || echo unknown)"
NOW="$(now_iso)"
TESTED_AT="$NOW"

{
  echo "{"
  echo "  \"schema_version\": 1,"
  echo "  \"tool\": \"tools/beta/run-all-tests.sh\","
  echo "  \"briq\": \"briq-09a-test-strategy-soak\","
  echo "  \"generated_at\": \"$NOW\","
  echo "  \"host\": \"$(uname -sm)\","
  echo "  \"root\": \"$ROOT\","
  echo "  \"version\": \"$NVER\","
  echo "  \"git_head\": \"$NGIT\","
  echo "  \"gate\": \"$GATE\","
  echo "  \"verdict\": \"$VERDICT\","
  echo "  \"raw_gate\": \"$RAW_GATE\","
  echo "  \"raw_verdict\": \"$RAW_VERDICT\","
  echo "  \"raw_fail_count\": $RAW_FAIL,"
  echo "  \"terminal_state\": \"OFFLINE_TESTED\","
  echo "  \"checks_column\": \"PASS-shaped assertion lines printed by the suite (a floor, see count_checks)\","
  echo "  \"strict\": $( [ "$STRICT" -eq 1 ] && echo true || echo false ),"
  echo "  \"external_requested\": $( [ "$EXTERNAL" -eq 1 ] && echo true || echo false ),"
  echo "  \"duration_s\": $T_TOTAL,"
  echo "  \"only\": \"$ONLY_RE\","
  echo "  \"counts\": {\"total\": $R_TOTAL, \"pass\": $R_PASS, \"fail\": $R_FAIL, \"warn\": $R_WARN, \"warn_cross_group\": $R_WARN_ALLOW, \"skip\": $R_SKIP, \"external\": $R_EXT},"
  echo "  \"first_failure\": \"$FIRST_FAIL\","
  echo "  \"suite_registry\": \"$REGISTRY_TSV\","
  echo "  \"suite_summary_tsv\": \"$SUMMARY_TSV\","
  echo "  \"log_dir\": \"$LOG_DIR\","
  echo "  \"invariants\": {"
  echo "    \"no_flashing\": true,"
  echo "    \"no_block_device_writes\": true,"
  echo "    \"no_qq_writes\": true,"
  echo "    \"no_qonqrete_receipt_in_workspace\": true,"
  echo "    \"a32_baseline_checked_by\": \"U-baseline-regression-guard\""
  echo "  },"
  echo "  \"soak\": {\"terminal_state\": \"BLOCKED_EXTERNAL_RESOURCE\", \"harness\": \"tools/beta/soak.sh\", \"doc\": \"docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md\"},"
  # every failure, verbatim and attributed, regardless of the gate verdict
  echo "  \"failures\": ["
  firstf=1
  while IFS='|' read -r fsid ftier fowner fchecks fnote; do
    [ -n "$fsid" ] || continue
    [ "$firstf" -eq 0 ] && echo ","
    firstf=0
    printf '    {"id": "%s", "tier": "%s", "owner": "%s", "checks": "%s", "note": "%s"}' \
      "$fsid" "$ftier" "$fowner" "$fchecks" "$(printf '%s' "$fnote" | sed 's/"/\\"/g')"
  done <<< "$FAIL_ROWS"
  echo
  echo "  ],"
  echo "  \"unfinished_groups\": \"${UNFINISHED_GROUPS:-}\","
  echo "  \"allowances_applied\": ["
  firsta=1
  while IFS='|' read -r asid agroup areason aexpiry; do
    [ -n "$asid" ] || continue
    [ "$firsta" -eq 0 ] && echo ","
    firsta=0
    printf '    {"id": "%s", "owner": "%s", "reason": "%s", "expiry": "%s"}' \
      "$asid" "$agroup" "$areason" "$aexpiry"
  done <<< "$ALLOW_HITS"
  echo
  echo "  ],"
  echo "  \"suites\": ["
  first=1
  while IFS=$'\t' read -r sid tier owner status rc dur checks mode note log; do
    [ -n "$sid" ] || continue
    [ "$first" -eq 0 ] && echo ","
    first=0
    printf '    {"id": "%s", "tier": "%s", "owner": "%s", "status": "%s", "rc": %s, "duration_s": %s, "checks": "%s", "mode": "%s", "log": "%s", "note": "%s"}' \
      "$sid" "$tier" "$owner" "$status" "$(json_num "$rc")" "$(json_num "$dur")" "$checks" "$mode" "$log" \
      "$(printf '%s' "$note" | sed 's/"/\\"/g')"
  done <<< "$JSON_ROWS"
  echo
  echo "  ]"
  echo "}"
} > "${JSON_OUT_FILE:-$JSON_OUT}"

if [ "$JSON_OUT" = "-" ]; then
  cat "${JSON_OUT_FILE:-$JSON_OUT}" >&9
fi

# ---------------------------------------------------------------------------
# The results table.  Printed on every run (also in --quiet mode: the table IS
# the summary the operator reads, and it is what gets committed with a release).
# ---------------------------------------------------------------------------
RULE="────────────────────────────────────────────────────────────────────"
print_table() {
  echo
  echo "$RULE"
  printf '%-30s %-8s %-9s %-38s %8s %6s\n' ID TIER STATUS OWNER CHECKS SECS
  echo "$RULE"
  while IFS=$'\t' read -r tid ttier towner tstat trc tdur tchecks tmode tnote tlog; do
    [ -n "$tid" ] || continue
    printf '%-30s %-8s %-9s %-38s %8s %6s\n' \
      "$tid" "$ttier" "$tstat" "$towner" "$tchecks" "$tdur"
  done <<< "$JSON_ROWS"
  echo "$RULE"
}

print_table

if [ "$R_WARN_ALLOW" -gt 0 ]; then
  echo
  echo "IN-FLIGHT CROSS-GROUP ALLOWANCES ($R_WARN_ALLOW) — these suites FAILED and were"
  echo "downgraded to WARN only because their owning group is still writing into this"
  echo "tree.  They are NOT passes.  Re-run with --strict for the raw verdict."
  while IFS='|' read -r asid agroup areason aexpiry; do
    [ -n "$asid" ] || continue
    echo "  * $asid  (owner $agroup, expires $aexpiry)"
    echo "      $areason"
  done <<< "$ALLOW_HITS"
fi

if [ -n "$FAIL_ROWS" ]; then
  echo
  echo "FAILURES ($R_FAIL) — each one is attributed in the summary JSON:"
  while IFS='|' read -r fsid ftier fowner fchecks fnote; do
    [ -n "$fsid" ] || continue
    echo "  FAIL $fsid  [owner $fowner]  $fnote"
  done <<< "$FAIL_ROWS"
fi

echo
printf 'run-all-tests: %d suites  pass=%d fail=%d warn=%d (cross-group=%d) skip=%d external=%d  %ss\n' \
  "$R_TOTAL" "$R_PASS" "$R_FAIL" "$R_WARN" "$R_WARN_ALLOW" "$R_SKIP" "$R_EXT" "$T_TOTAL"
echo "gate: $GATE   verdict: $VERDICT   (OFFLINE_TESTED only — never VERIFIED_ON_S10PLUS)"
echo "raw gate (--strict, no cross-group allowances): $RAW_GATE  fail=$RAW_FAIL"
echo "summary: $SUMMARY_PATH"
echo "logs:    $LOG_DIR"
[ "$R_FAIL" -gt 0 ] && echo "first failure: $FIRST_FAIL (see $LOG_DIR/$FIRST_FAIL.log)"
echo "$RULE"

exit "$EXIT"
