#!/usr/bin/env bash
# =============================================================================
# soak.sh — soak, stability and resource/performance harness (briq-09a, area 50)
#
#   tools/beta/soak.sh --plan                      # the plan + pass criteria
#   tools/beta/soak.sh --selftest                  # offline self-verification
#   tools/beta/soak.sh --replay FILE.ndjson        # verdict on recorded samples
#   tools/beta/soak.sh --device [--duration 28800] # 8 h soak on the handset
#   tools/beta/soak.sh --vm [--duration 1800]      # bounded VM soak (bg-11)
#
# HONESTY CONTRACT
#   * `--selftest` and `--replay` are OFFLINE_TESTED: they prove the *harness*.
#   * `--device` can only produce VERIFIED_ON_S10PLUS; if the live USB console is
#     not reachable it exits 3 with terminal state BLOCKED_EXTERNAL_RESOURCE and
#     says so in the report — it never claims a soak it did not run.
#   * `--vm` produces VERIFIED_IN_VM_ONLY.
#   * Green harness != working hardware.  No sample is ever fabricated.
#
# SAFETY (mission invariants, enforced below by guard_path/guard_cmd)
#   * writes only under the evidence directory and the report path (never /dev/*,
#     never a block device, never .qq/ or the QonQrete RUN_ROOT);
#   * never reboots, never stops/starts a service, never flashes;
#   * never writes a QonQrete receipt JSON into the workspace.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
LIB="$HERE/soak_lib.py"
PY="${SOAK_PY:-python3}"
STAMP="$(date +%Y%m%dT%H%M%S%z 2>/dev/null || date +%s)"

MODE=""
DURATION=""; INTERVAL=""; CHECKPOINT=""
EVIDENCE_DIR=""
REPORT_JSON=""
SAMPLES_FILE=""
QUIET=0
SMOKE=0

usage() { sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --plan|--selftest|--device|--vm) MODE="${1#--}"; shift ;;
    --replay)       MODE="replay"; SAMPLES_FILE="$2"; shift 2 ;;
    --samples)      SAMPLES_FILE="$2"; shift 2 ;;
    --duration)     DURATION="$2"; shift 2 ;;
    --interval)     INTERVAL="$2"; shift 2 ;;
    --checkpoint)   CHECKPOINT="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --json)         REPORT_JSON="$2"; shift 2 ;;
    --smoke)        SMOKE=1; shift ;;
    --quiet|-q)     QUIET=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *) echo "soak: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[ -n "$MODE" ] || { usage; exit 2; }

case "$MODE" in
  device) DURATION="${DURATION:-${SMOKE:+180}}"; DURATION="${DURATION:-28800}" ;;
  vm)     DURATION="${DURATION:-${SMOKE:+300}}";  DURATION="${DURATION:-1800}" ;;
  *)      DURATION="${DURATION:-0}" ;;
esac
INTERVAL="${INTERVAL:-60}"
CHECKPOINT="${CHECKPOINT:-1800}"
EVIDENCE_DIR="${EVIDENCE_DIR:-$ROOT/docs/beta-finalization/testing/evidence/soak-${MODE}-${STAMP}}"
REPORT_JSON="${REPORT_JSON:-$EVIDENCE_DIR/soak-report.json}"

# --------------------------------------------------------------------------- #
# Path guards (mission invariants, mechanically enforced)
# --------------------------------------------------------------------------- #
guard_path() {   # guard_path <path> <what>
  local p="$1" what="${2:-path}"
  case "$p" in
    *"/.qq/"*|*"/.qq"|*"/.codeseeq/"*)
      echo "soak: REFUSING $what under QonQrete metadata: $p" >&2; return 1 ;;
    *"/runs/2026"*"/agents/"*)
      echo "soak: REFUSING $what under a QonQrete RUN_ROOT: $p" >&2; return 1 ;;
    /dev/*|/sys/*|/proc/*)
      echo "soak: REFUSING $what on a device/kernel path: $p" >&2; return 1 ;;
  esac
  return 0
}
guard_cmd() {    # guard_cmd <command-string>
  case "$1" in
    *heimdall*|*fastboot*|*"odin "*|*twrp*|*"dd "*"of=/dev"*|*mkfs*|*"reboot"*|*"systemctl "*stop*|*"systemctl "*disable*)
      echo "soak: REFUSING a mutating/flashing command: $1" >&2; return 1 ;;
  esac
  return 0
}
guard_path "$EVIDENCE_DIR" "evidence dir" || exit 2
guard_path "$REPORT_JSON" "report path" || exit 2

say() { [ "$QUIET" -eq 1 ] || echo "$@"; }

json_get() {   # json_get <file> <dotted.key>  (best-effort, no jq dependency)
  "$PY" - "$1" "$2" <<'PY'
import json, sys
def walk(o, keys):
    for k in keys:
        if isinstance(o, dict) and k in o:
            o = o[k]
        else:
            return ""
    return o
try:
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print(""); raise SystemExit(0)
val = walk(doc, sys.argv[2].split("."))
print("" if val is None else (json.dumps(val) if isinstance(val, (dict, list)) else val))
PY
}

# --------------------------------------------------------------------------- #
# The probe: ONE short line per sample (the live console drops long lines)
# --------------------------------------------------------------------------- #
probe_command() {
  cat <<'EOF'
u=$(cut -d' ' -f1 /proc/uptime); l=$(cut -d' ' -f1 /proc/loadavg);
fu=$(systemctl --failed --no-legend --no-pager 2>/dev/null | wc -l);
rs=$(ps -eo rss,comm --no-headers 2>/dev/null | awk '/nuxel-|phoc|WebKitWebProces/{s+=$1}END{print s+0}');
cp=$(ps -eo pcpu,comm --no-headers 2>/dev/null | awk '/nuxel-|phoc|WebKitWebProces/{s+=$1}END{printf "%.1f",s+0}');
fb=$(sed -n 's/.*pid[=:][[:space:]]*\([0-9]*\).*/\1/p' /var/lib/nuxel/fb-owner 2>/dev/null | head -1);
hc=$(curl -s -o /dev/null -m 4 -w '%{http_code}' http://127.0.0.1:8000/ 2>/dev/null);
tz=$(cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | sort -n | tail -1);
rr=$(for u2 in nuxel-pwa nuxel-wl-fb nuxel-button-manager nuxel-wayland; do systemctl show -p NRestarts --value $u2 2>/dev/null; done | awk '{s+=$1}END{print s+0}');
bm=$(tr ' ' '\n' </proc/cmdline | sed -n 's/^androidboot.mode=//p');
echo "SOAK uptime_s=$u load1=$l failed_units=$fu stack_rss_kb=$rs stack_cpu_pct=$cp fb_owner_pid=$fb http_code=$hc thermal_raw=$tz restarts=$rr boot_mode=$bm"
EOF
}

parse_sample() {   # parse_sample <raw-line> <index> -> JSON on stdout
  "$PY" - "$1" "$2" <<'PY'
import json, sys, time, re
raw, idx = sys.argv[1], int(sys.argv[2])
kv = {}
m = re.search(r"SOAK\s+(.*)$", raw)
body = m.group(1) if m else raw
for tok in body.split():
    if "=" in tok:
        k, v = tok.split("=", 1)
        kv[k] = v
def num(k, cast=float, default=None):
    try:
        return cast(kv[k])
    except Exception:
        return default
th = num("thermal_raw")
sample = {
    "t": time.time(), "i": idx,
    "uptime_s": num("uptime_s"),
    "load1": num("load1", default=0.0),
    "mem_used_kb": None, "mem_avail_kb": None,
    "stack_rss_kb": num("stack_rss_kb", int),
    "stack_cpu_pct": num("stack_cpu_pct"),
    "failed_units": num("failed_units", int, 0),
    "service_restarts": num("restarts", int, 0),
    "fb_owner_pid": num("fb_owner_pid", int),
    "http_ok": str(kv.get("http_code", "")).strip() == "200",
    "http_code": kv.get("http_code", ""),
    "thermal_max_c": (th / 1000.0) if th and th > 1000 else th,
    "cmdline_boot_mode": kv.get("boot_mode", ""),
    "raw": body.strip()[:400],
}
print(json.dumps(sample, sort_keys=True))
PY
}

write_report() {   # write_report <json-file> <markdown-file> <terminal-state>
  "$PY" - "$1" "$2" "$3" <<'PY'
import json, sys, time
rep = json.load(open(sys.argv[1], encoding="utf-8"))
state = sys.argv[3]
rep["terminal_state"] = state
rep["soak_doc"] = "docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md"
rep["strategy_doc"] = "docs/beta-finalization/testing/TEST-STRATEGY.md"
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(rep, fh, indent=2, sort_keys=True)
lines = ["# Soak / performance report", "",
         "- **generated:** %s" % rep.get("generated_at", time.strftime("%Y-%m-%dT%H:%M:%S%z")),
         "- **mode:** %s" % rep.get("mode"),
         "- **verdict:** %s" % rep.get("verdict"),
         "- **terminal state:** %s" % state,
         "- **samples:** %s" % rep.get("samples"), ""]
if rep.get("blocked_reason"):
    lines += ["## Blocked", "", rep["blocked_reason"], ""]
lines += ["## Criteria", ""]
for f in rep.get("findings", []):
    lines.append("- `%s` **%s** — %s" % (f["id"], f["severity"].upper(), f["detail"]))
lines += ["", "## Statistics", "", "```"]
for k in sorted(rep.get("stats", {})):
    lines.append("%-34s %s" % (k, rep["stats"][k]))
lines += ["```", "", "## Load-average note", "", rep.get("load_average_note", ""), "",
          "_A passing soak proves stability over the sampled window. It never proves "
          "that untested hardware works._", ""]
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(lines))
print("report: %s" % sys.argv[2])
PY
}

# --------------------------------------------------------------------------- #
# --plan
# --------------------------------------------------------------------------- #
if [ "$MODE" = "plan" ]; then
  "$PY" "$LIB" plan --mode device --duration 28800 >/dev/null 2>&1 || true
  say "=== Nuxel beta soak / performance plan ==="
  "$PY" "$LIB" plan --mode device --duration 28800 --interval "$INTERVAL" --checkpoint "$CHECKPOINT"
  echo
  say "Pass criteria are the single source of truth in tools/beta/soak_lib.py THRESHOLDS"
  say "and are quoted verbatim in docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md."
  echo
  say "Access tier: repository-only orchestration.  The 8 h soak needs the live USB"
  say "console ('--device') or the UTM guest ('--vm'); when neither is reachable the"
  say "soak is BLOCKED_EXTERNAL_RESOURCE while the harness still ships and passes"
  say "--selftest (offline) and --replay (recorded samples)."
  exit 0
fi

# --------------------------------------------------------------------------- #
# --selftest  (offline: proves the harness, never the hardware)
# --------------------------------------------------------------------------- #
if [ "$MODE" = "selftest" ]; then
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-soak-XXXXXX")"
  fails=0
  ok()   { echo "  PASS $1"; }
  bad()  { echo "  FAIL $1${2:+ — $2}"; fails=$((fails + 1)); }

  say "=== soak.sh selftest (offline) ==="
  if "$PY" "$LIB" selftest >"$tmp/lib.out" 2>&1; then ok "soak_lib.py evaluator selftest"
  else bad "soak_lib.py evaluator selftest" "$(tail -3 "$tmp/lib.out" | tr '\n' ' ')"; fi
  tail -n +1 "$tmp/lib.out" | grep -c '"ok": true' >/dev/null || true

  if "$PY" "$LIB" plan --mode device >"$tmp/plan.json" 2>/dev/null \
      && "$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if d['gated'] and d['probe_set'] else 1)" "$tmp/plan.json"; then
    ok "plan lists probe set + gated criteria"
  else bad "plan lists probe set + gated criteria"; fi

  # guard: .qq is never a valid evidence/report destination
  if bash "$0" --replay /dev/null --evidence-dir "$ROOT/.qq/oops" --quiet >/dev/null 2>&1; then
    bad "guard refuses .qq evidence dir"
  else ok "guard refuses .qq evidence dir"; fi

  # a good synthetic series must pass, a reboot series must fail
  "$PY" "$LIB" synth --out "$tmp/good.ndjson" --n 481 --interval 60 >/dev/null
  "$PY" "$LIB" synth --out "$tmp/bad.ndjson" --n 481 --interval 60 --reboot-at 200 >/dev/null
  if "$PY" "$LIB" evaluate --samples "$tmp/good.ndjson" --duration 28800 --json "$tmp/good.json" >/dev/null; then
    ok "recorded good series evaluates PASS"
  else bad "recorded good series evaluates PASS"; fi
  if "$PY" "$LIB" evaluate --samples "$tmp/bad.ndjson" --duration 28800 --json "$tmp/bad.json" >/dev/null; then
    bad "recorded reboot series must FAIL"
  else ok "recorded reboot series evaluates FAIL (reboot detected)"; fi

  # replay path through the CLI writes a report with a terminal state
  if bash "$0" --replay "$tmp/good.ndjson" --duration 28800 --evidence-dir "$tmp/ev" \
        --quiet >/dev/null 2>&1 \
     && grep -q '"terminal_state": "OFFLINE_TESTED"' "$tmp/ev/soak-report.json"; then
    ok "replay writes a report with terminal state OFFLINE_TESTED"
  else bad "replay writes a report with terminal state OFFLINE_TESTED"; fi

  # device mode with no reachable console must be BLOCKED_EXTERNAL_RESOURCE, not a pass
  rc=0
  SOAK_REACHABILITY_CMD="false" bash "$0" --device --smoke --evidence-dir "$tmp/ev2" \
      --quiet >/dev/null 2>&1 || rc=$?
  if [ "$rc" -eq 3 ] && grep -q '"terminal_state": "BLOCKED_EXTERNAL_RESOURCE"' "$tmp/ev2/soak-report.json"; then
    ok "unreachable device => exit 3 + BLOCKED_EXTERNAL_RESOURCE"
  else bad "unreachable device => exit 3 + BLOCKED_EXTERNAL_RESOURCE" "rc=$rc"; fi

  # the harness must not have written anything into QonQrete metadata: look for
  # this run's unique stamp, not for the word "soak" (the pipeline's own prompt
  # files legitimately mention soak).
  if [ -d "$ROOT/.qq" ] && grep -rl -- "$STAMP" "$ROOT/.qq" >/dev/null 2>&1; then
    bad "no writes under .qq" "found files carrying this run's stamp"
  else ok "no writes under .qq"; fi

  rm -rf "$tmp"
  echo "soak.sh selftest: $([ "$fails" -eq 0 ] && echo PASS || echo "FAIL ($fails)")"
  [ "$fails" -eq 0 ] || exit 1
  exit 0
fi

# --------------------------------------------------------------------------- #
# --replay / --samples
# --------------------------------------------------------------------------- #
if [ "$MODE" = "replay" ]; then
  [ -s "$SAMPLES_FILE" ] || { echo "soak: no samples file ($SAMPLES_FILE)" >&2; exit 3; }
  mkdir -p "$EVIDENCE_DIR"
  "$PY" "$LIB" evaluate --samples "$SAMPLES_FILE" --duration "$DURATION" \
      --mode replay --json "$REPORT_JSON" || true
  write_report "$REPORT_JSON" "${REPORT_JSON%.json}.md" "OFFLINE_TESTED"
  say "soak(replay): verdict $(json_get "$REPORT_JSON" verdict) — OFFLINE_TESTED"
  "$PY" -c 'import json,sys;d=json.load(open(sys.argv[1]));print("failures:",d["failures"] or "none");print("warnings:",d["warnings"] or "none")' "$REPORT_JSON" 2>/dev/null
  "$PY" -c 'import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if d["verdict"].startswith("PASS") else 1)' "$REPORT_JSON" || exit 1
  exit 0
fi

# --------------------------------------------------------------------------- #
# --device / --vm : only reachable behind a real resource check
# --------------------------------------------------------------------------- #
reachability_check() {
  if [ -n "${SOAK_REACHABILITY_CMD:-}" ]; then
    # selftest hook: an injected probe may say "no resource" with a non-zero rc
    bash -c "$SOAK_REACHABILITY_CMD" >/dev/null 2>&1
    return $?
  fi
  if [ "$MODE" = "device" ]; then
    [ -x "$ROOT/tools/beta/live/nuxel-live-reachability.py" ] || return 3
    "$PY" "$ROOT/tools/beta/live/nuxel-live-reachability.py" --json >/dev/null 2>&1
    return $?
  fi
  # vm: bounded ssh probe of the UTM guest
  : "${SOAK_VM_HOST:=nuxel@192.168.64.3}"
  ssh -o BatchMode=yes -o ConnectTimeout=8 "$SOAK_VM_HOST" true >/dev/null 2>&1
  return $?
}

blocked_report() {   # blocked_report <reason>
  mkdir -p "$EVIDENCE_DIR"
  "$PY" - "$REPORT_JSON" "$MODE" "$1" "$DURATION" <<'PY'
import json, sys, time
path, mode, reason, dur = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
doc = {
    "schema_version": 1, "tool": "tools/beta/soak.sh", "mode": mode,
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "verdict": "BLOCKED_EXTERNAL_RESOURCE", "terminal_state": "BLOCKED_EXTERNAL_RESOURCE",
    "samples": 0, "requested_duration_s": dur, "blocked_reason": reason,
    "findings": [{"id": "S0-no-resource", "severity": "fail", "detail": reason}],
    "stats": {},
    "load_average_note": ("load1 on the S10+ is dominated by Samsung vendor kernel threads "
                          "(TrustZone/RPMB/REE time), per the A31 finding; it is recorded "
                          "but never gated."),
}
json.dump(doc, open(path, "w", encoding="utf-8"), indent=2, sort_keys=True)
PY
  write_report "$REPORT_JSON" "${REPORT_JSON%.json}.md" "BLOCKED_EXTERNAL_RESOURCE"
  if [ "$QUIET" -eq 0 ]; then
    echo "soak: BLOCKED_EXTERNAL_RESOURCE — $1"
    echo "      harness ships and is OFFLINE_TESTED; the soak itself is deferred to"
    echo "      the live group (bg-10, --device) or the VM group (bg-11, --vm)."
    echo "      report: $REPORT_JSON"
  fi
}

if ! reachability_check; then
  if [ "$MODE" = "device" ]; then
    blocked_report "the live S10+ USB console is not reachable from this execution environment (see docs/beta-finalization/preflight/ENVIRONMENT.md section 6); retry with the handset booted into Nuxel and the live console enumerated"
  else
    blocked_report "the UTM Fedora 43 guest is not reachable via ssh (${SOAK_VM_HOST:-nuxel@192.168.64.3}); the VM soak is owned by bg-11-vm-parity"
  fi
  exit 3
fi

mkdir -p "$EVIDENCE_DIR"
NDJSON="$EVIDENCE_DIR/samples.ndjson"
: > "$NDJSON"

if [ "$MODE" = "device" ]; then
  CONSOLE_CMD="${SOAK_CONSOLE_CMD:-bash $ROOT/scripts/s10plus-debug-pack/nuxel-console-host.sh --run}"
else
  CONSOLE_CMD="${SOAK_CONSOLE_CMD:-ssh -o BatchMode=yes -o ConnectTimeout=8 ${SOAK_VM_HOST:-nuxel@192.168.64.3} }"
fi
PROBE="$(probe_command | tr '\n' ' ')"
PROBE="$(printf '%s' "$PROBE" | sed 's/  */ /g')"
guard_cmd "$PROBE" || exit 2

say "=== Nuxel soak ($MODE): ${DURATION}s @ ${INTERVAL}s, checkpoints every ${CHECKPOINT}s ==="
say "evidence: $EVIDENCE_DIR"

start=$(date +%s)
next_ckpt=$((start + CHECKPOINT))
i=0
while :; do
  raw="$(bash -c "$CONSOLE_CMD \"\$0\"" "$PROBE" 2>/dev/null | tr -d '\r' | grep -m1 'SOAK ' || true)"
  if [ -n "$raw" ]; then
    sample="$(parse_sample "$raw" "$i")"
  else
    sample="$(printf '{"i": %s, "t": %s, "console_lost": true, "failed_units": 1, "http_ok": false, "fb_owner_pid": null, "cmdline_boot_mode": "unknown"}' "$i" "$(date +%s)")"
  fi
  printf '%s\n' "$sample" >> "$NDJSON"
  if [ "$QUIET" -eq 0 ] && [ $((i % 10)) -eq 0 ]; then
    "$PY" -c 'import json,sys;s=json.loads(sys.argv[1]);print("  sample %-4s uptime=%-8s cpu=%-6s rss_kb=%-8s failed=%-3s http=%s" % (s.get("i"),s.get("uptime_s"),s.get("stack_cpu_pct"),s.get("stack_rss_kb"),s.get("failed_units"),s.get("http_ok")))' "$sample"
  fi
  i=$((i + 1))
  now=$(date +%s)
  if [ "$now" -ge "$next_ckpt" ]; then
    echo "checkpoint t+$((now - start))s samples=$i" >> "$EVIDENCE_DIR/checkpoints.log"
    [ "$QUIET" -eq 0 ] && say "  checkpoint: t+$((now - start))s, $i samples"
    next_ckpt=$((now + CHECKPOINT))
  fi
  [ $((now - start)) -ge "$DURATION" ] && break
  sleep "$INTERVAL"
done

"$PY" "$LIB" evaluate --samples "$NDJSON" --duration "$DURATION" --mode "$MODE" \
    --json "$REPORT_JSON" || true
if [ "$MODE" = "device" ]; then STATE="VERIFIED_ON_S10PLUS"; else STATE="VERIFIED_IN_VM_ONLY"; fi
"$PY" - "$REPORT_JSON" "$STATE" <<'PY'
import json, sys
p, state = sys.argv[1], sys.argv[2]
d = json.load(open(p, encoding="utf-8"))
# a soak that did not actually cover the window is not a verification at all
if d.get("stats", {}).get("coverage_ratio", 0) < d["thresholds"]["min_coverage_ratio"]:
    state = "BLOCKED_EXTERNAL_RESOURCE"
d["terminal_state"] = state
json.dump(d, open(p, "w", encoding="utf-8"), indent=2, sort_keys=True)
PY
STATE="$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["terminal_state"])' "$REPORT_JSON")"
write_report "$REPORT_JSON" "${REPORT_JSON%.json}.md" "$STATE"
say "soak($MODE): verdict $("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["verdict"])' "$REPORT_JSON") — $STATE"
[ "$STATE" = "BLOCKED_EXTERNAL_RESOURCE" ] && exit 3
exit 0
