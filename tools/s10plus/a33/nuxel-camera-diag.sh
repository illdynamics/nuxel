#!/usr/bin/env bash
# nuxel-camera-diag.sh — S10+ (beyond2lte) camera bring-up + pipeline diagnostic.
#
# WHAT THIS IS
#   An enumeration-first diagnostic for the Exynos/Samsung camera path. It reports
#   which V4L2/media nodes exist, which sensor/bridge names the kernel actually
#   binds, which expected firmware blobs are present, and it names the FIRST
#   failing pipeline stage. A sensor driver being bound is NOT proof that a frame
#   can be captured, so every status output carries "frame_captured_verified":
#   false and a fully-enumerated device is reported READY_UNTESTED.
#
# WHAT THIS IS NOT
#   It never claims a captured frame without one, never installs or depends on an
#   Android camera HAL, never uses a synthetic (videotestsrc) node as evidence of
#   S10+ hardware, never captures automatically, and never writes to a partition,
#   a block device, a bootloader or any modem/EFS/calibration area.
#
# Usage:
#   nuxel-camera-diag.sh status [--json]
#   nuxel-camera-diag.sh list            # per-node enumeration with real paths
#   nuxel-camera-diag.sh fw              # firmware blobs: present / missing
#   nuxel-camera-diag.sh pipeline        # stage-by-stage, first failing stage named
#   nuxel-camera-diag.sh portal          # camera-portal unit/backend, synthetic-vs-hardware
#   nuxel-camera-diag.sh capture --yes <out.jpg>   # ONE bounded still (owner action)
#   nuxel-camera-diag.sh report
#   nuxel-camera-diag.sh selftest        # offline fixtures
set -uo pipefail
SELF="$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_CAMERA_POLICY:-/etc/nuxel/camera/camera.json}"
LOG="${NUXEL_CAMERA_LOG:-/var/log/nuxel/camera-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
YES=0; JSON=0; OUT=""
for a in "$@"; do case "$a" in --yes) YES=1 ;; --json) JSON=1 ;; /*|*.jpg|*.jpeg|*.png) OUT="$a" ;; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
[ -n "$RR" ] && [ ! -r "$POLICY" ] && POLICY="$RR/configs/nuxel/camera/camera.json"
say() { printf '%s\n' "$*"; }
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
jesc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
faked_root() { [ "$ROOT" != "/" ]; }
pol_get() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    if not isinstance(cur,dict): sys.exit(0)
    cur=cur.get(k)
print("" if cur is None else cur)
PY
}
pol_list() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    if not isinstance(cur,dict): sys.exit(0)
    cur=cur.get(k)
if isinstance(cur,list):
    for x in cur:
        print(x if isinstance(x,str) else json.dumps(x))
PY
}

# ---- enumeration -----------------------------------------------------------
VIDEO=""; SUBDEV=""; MEDIA=""; NAMES=""; GRAPH_OK="no"
dedupe() { local out="" x; for x in $1; do case " $out " in *" $x "*) ;; *) out="$out $x" ;; esac; done; printf '%s' "${out# }"; }
enumerate() {
  local cand g p
  for cand in $(pol_list device_candidates.video_globs) $(pol_list device_candidates.video_nodes); do
    for p in $(abs "$cand"); do [ -e "$p" ] && VIDEO="$VIDEO ${p#$ROOT}"; done
  done
  for cand in $(pol_list device_candidates.subdev_globs) $(pol_list device_candidates.subdev_nodes); do
    for p in $(abs "$cand"); do [ -e "$p" ] && SUBDEV="$SUBDEV ${p#$ROOT}"; done
  done
  for cand in $(pol_list device_candidates.media_globs) $(pol_list device_candidates.media_nodes); do
    for p in $(abs "$cand"); do [ -e "$p" ] && MEDIA="$MEDIA ${p#$ROOT}"; done
  done
  VIDEO="$(dedupe "$VIDEO")"; SUBDEV="$(dedupe "$SUBDEV")"; MEDIA="$(dedupe "$MEDIA")"
  local rx; rx="$(pol_get device_candidates.sensor_name_regex)"
  for g in $(pol_list device_candidates.sensor_name_sources); do
    for p in $(abs "$g"); do
      [ -r "$p" ] || continue
      local n; n="$(tr -d '\r\n' < "$p" 2>/dev/null)"
      [ -z "$n" ] && continue
      if [ -n "$rx" ] && ! printf '%s' "$n" | grep -Eq "$rx"; then continue; fi
      NAMES="$NAMES $n"
    done
  done
  NAMES="$(dedupe "$NAMES")"
  if [ -n "$MEDIA" ]; then
    for m in $MEDIA; do [ -d "$(abs "$m")" ] || [ -r "$(abs "$m")" ] && GRAPH_OK="yes"; done
  fi
}
fw_report() { # sets FW_FOUND / FW_MISSING (newline separated)
  FW_FOUND=""; FW_MISSING=""
  local blob sp p found
  for blob in $(pol_list firmware_blobs.candidates); do
    found=no
    for sp in $(pol_list firmware_blobs.search_paths); do
      p="$(abs "$sp/$blob")"
      [ -e "$p" ] && { found=yes; break; }
    done
    if [ "$found" = yes ]; then FW_FOUND="$FW_FOUND $blob"; else FW_MISSING="$FW_MISSING $blob"; fi
  done
  FW_FOUND="${FW_FOUND# }"; FW_MISSING="${FW_MISSING# }"
}
verdict() { # echoes STATE|FIRST_FAILING|DETAIL
  local stage=""
  if [ -z "$VIDEO$SUBDEV$MEDIA" ]; then printf 'NO_V4L2_DEVICE|capture|no /dev/video*, /dev/v4l-subdev* or /dev/media* node exists'; return; fi
  if [ -z "$NAMES" ]; then printf 'PRESENT_UNREADABLE|sensor_names|nodes exist but no sensor/bridge name is readable from the video4linux sysfs class'; return; fi
  if [ -z "$FW_FOUND" ]; then printf 'BLOCKED_FIRMWARE|firmware|sensor identity present but none of the expected firmware blobs exist under the search paths'; return; fi
  if [ "$GRAPH_OK" != yes ]; then printf 'PRESENT_UNREADABLE|media_graph|sensor identity + firmware present but no readable media device (graph) was found'; return; fi
  printf 'READY_UNTESTED|capture|nodes, sensor identity, firmware and media graph present; a frame is the owner observation'
}
fmt_sensors() { python3 - "$POLICY" "$NAMES" <<'PY'
import json,sys
pol=sys.argv[1]; names=[n for n in sys.argv[2].split() if n]
try: d=json.load(open(pol))
except Exception: print("policy unreadable"); sys.exit(0)
exp=d.get("device",{}).get("expected_sensors",{})
rows=[]
for side in ("rear","front"):
    for s in exp.get(side,[]):
        hit="observed" if any(s["name"].split("_")[0] in n for n in names) else "not-observed"
        rows.append("%-9s %-18s %s" % (side, s["name"], hit))
print("\n".join(rows))
PY
}
json_status() {
  local v state ff detail; IFS='|' read -r state ff detail <<EOF
$(verdict)
EOF
  local jv="[]" js="[]" jm="[]" jn="[]" jf="[]" jx="[]"
  [ -n "$VIDEO" ] && jv="$(printf '%s\n' $VIDEO | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')"
  [ -n "$SUBDEV" ] && js="$(printf '%s\n' $SUBDEV | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')"
  [ -n "$MEDIA" ] && jm="$(printf '%s\n' $MEDIA | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')"
  [ -n "$NAMES" ] && jn="$(printf '%s\n' $NAMES | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')"
  [ -n "$FW_FOUND" ] && jf="$(printf '%s\n' $FW_FOUND | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')"
  [ -n "$FW_MISSING" ] && jx="$(printf '%s\n' $FW_MISSING | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')"
  printf '{"device":"beyond2lte","tool":"nuxel-camera-diag","state":"%s","verdict":"%s","first_failing_stage":"%s","detail":"%s","video_nodes":%s,"subdev_nodes":%s,"media_nodes":%s,"sensor_names":%s,"firmware_found":%s,"firmware_missing":%s,"media_graph_readable":%s,"synthetic_chain_proof":{"portal_unit":"shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service","synthetic_is_hardware_evidence":false},"frame_captured_verified":false,"owner_test":"docs/beta-finalization/manual-proof/15-camera.md"}\n' \
    "$state" "$state" "$ff" "$(jesc "$detail")" "$jv" "$js" "$jm" "$jn" "$jf" "$jx" \
    "$([ "$GRAPH_OK" = yes ] && printf true || printf false)"
}
cmd_status() {
  enumerate; fw_report
  if [ "$JSON" = 1 ]; then json_status; return; fi
  local v state ff detail; IFS='|' read -r state ff detail <<EOF
$(verdict)
EOF
  say "device            : beyond2lte (S10+ SM-G975F, Exynos 9820)"
  say "video nodes       : ${VIDEO:-NONE}"
  say "subdev nodes      : ${SUBDEV:-NONE}"
  say "media nodes       : ${MEDIA:-NONE}"
  say "sensor names      : ${NAMES:-NONE readable}"
  say "media graph       : $GRAPH_OK"
  say "expected sensors  : (expected_on_s10plus = shipped hardware, NOT an observation)"
  fmt_sensors | sed 's/^/                    /'
  say "firmware present  : ${FW_FOUND:-none}"
  say "firmware missing  : ${FW_MISSING:-none}"
  say "first failing st. : $ff  ($detail)"
  say "verdict           : $state"
  say "frame captured    : NO — a frame is the owner's observation (NEEDS_OWNER_TEST); nothing is ever claimed."
  say "portal            : shell/nuxel-camera-portal (session unit; synthetic videotestsrc on the VM proves the CHAIN, never the S10+ camera)"
  say "owner procedure   : docs/beta-finalization/manual-proof/15-camera.md"
}
cmd_list() {
  enumerate
  say "video nodes  :"; for p in $VIDEO; do say "  $p  name=$([ -r "$(abs "$p")" ] && echo readable || echo 'node-only')"; done
  [ -z "$VIDEO" ] && say "  (none)"
  say "subdev nodes :"; for p in $SUBDEV; do say "  $p"; done
  [ -z "$SUBDEV" ] && say "  (none)"
  say "media nodes  :"; for p in $MEDIA; do say "  $p"; done
  [ -z "$MEDIA" ] && say "  (none)"
  say "sensor names :"; for n in $NAMES; do say "  $n"; done
  [ -z "$NAMES" ] && say "  (none readable)"
  if ! faked_root && command -v v4l2-ctl >/dev/null 2>&1; then
    say "v4l2-ctl     : present — run 'v4l2-ctl --list-devices' and 'v4l2-ctl -d <node> --list-formats-ext'"
  else
    say "v4l2-ctl     : not used here (v4l-utils may be absent); enumeration above is sysfs/dev only"
  fi
}
cmd_fw() { fw_report; say "search paths : $(pol_list firmware_blobs.search_paths | tr '\n' ' ')"; say "present      : ${FW_FOUND:-none}"; say "missing      : ${FW_MISSING:-none}"; [ -z "$FW_FOUND" ] && say "verdict      : BLOCKED_FIRMWARE — no expected firmware blob is present under the search paths"; return 0; }
cmd_pipeline() {
  enumerate; fw_report
  local v state ff detail; IFS='|' read -r state ff detail <<EOF
$(verdict)
EOF
  say "pipeline stages (first failing stage is named):"
  say "  1 dev_nodes    : $([ -n "$VIDEO$SUBDEV$MEDIA" ] && echo present || echo FAIL)"
  say "  2 sensor_names : $([ -n "$NAMES" ] && echo present || echo FAIL)"
  say "  3 firmware     : $([ -n "$FW_FOUND" ] && echo present || echo FAIL)"
  say "  4 media_graph  : $([ "$GRAPH_OK" = yes ] && echo present || echo FAIL)"
  say "  5 capture      : not attempted here (owner action: capture --yes)"
  say "first failing stage: $ff"
  say "verdict            : $state"
}
# repo_path: a policy path may be repo-relative (developer tree) or absolute
# (installed). Never assume which: print what was found and where.
repo_path() { # $1 path -> prints the first existing location, or nothing
  local p="$1"
  [ -z "$p" ] && return 0
  case "$p" in
    /*) [ -e "$(abs "$p")" ] && { printf '%s%s' "$ROOT" "$p"; return; } ;;
  esac
  if [ -n "$RR" ] && [ -e "$RR/$p" ]; then printf '%s' "$RR/$p"; return; fi
  [ -e "$p" ] && { printf '%s' "$p"; return; }
  return 0
}
cmd_portal() {
  local unit backend iunit iback iface
  unit="$(pol_get pipeline.portal.unit)"; backend="$(pol_get pipeline.portal.backend)"
  iunit="$(pol_get pipeline.portal.install_unit)"; iback="$(pol_get pipeline.portal.install_backend)"
  iface="$(pol_get pipeline.portal.interface)"
  local u_found b_found iu_found ib_found; u_found="$(repo_path "$unit")"; b_found="$(repo_path "$backend")"
  iu_found=""; ib_found=""
  [ -n "$iunit" ] && iu_found="$(repo_path "$iunit")"
  [ -n "$iback" ] && ib_found="$(repo_path "$iback")"
  local app app_manifest app_ok=0
  app="$(pol_get gallery.capture_app.path)"; app_manifest="$app/manifest.json"
  [ -n "$(repo_path "$app_manifest")" ] && app_ok=1
  say "interface     : ${iface:-org.freedesktop.portal.Camera}  methods: $(pol_list pipeline.portal.methods | tr '\n' ' ')"
  say "portal unit   : ${unit:-<unset>}  -> ${u_found:-MISSING in repository}   (installs to ${iunit:-<unset>}${iu_found:+, present})"
  say "backend       : ${backend:-<unset>}  -> ${b_found:-MISSING in repository}   (installs to ${iback:-<unset>}${ib_found:+, present})"
  say "capture app   : ${app:-<unset>} -> $([ $app_ok = 1 ] && printf present || printf MISSING)"
  # the app's own manifest is the contract the bridge must satisfy
  if [ $app_ok = 1 ]; then
    local declared want; declared="$(python3 - "$(repo_path "$app_manifest")" 2>/dev/null <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
print(" ".join(d.get("nuxel",{}).get("bridge_verbs",[])))
PY
)"
    want="$(pol_list gallery.bridge_verbs | tr '\n' ' ' | sed 's/ *$//')"
    say "bridge verbs  : policy=[${want}] app=[${declared}] $([ "$want" = "$declared" ] && echo '(match)' || echo '(MISMATCH — the app asks for verbs the policy does not declare)')"
  fi
  say "synthetic     : enabled=$(pol_get pipeline.portal.synthetic_when_no_hardware.enabled) — a GStreamer videotestsrc node proves the CHAIN works and is NEVER evidence that the S10+ camera works ($(pol_get pipeline.portal.synthetic_when_no_hardware.reported_as))"
  # first failing stage of the PORTAL chain (independent of the V4L2 chain)
  local stage="pipeline_open"
  if [ -z "$u_found$iu_found" ]; then stage="unit_installed"
  elif [ -z "$b_found$ib_found" ]; then stage="backend_installed"
  elif [ $app_ok != 1 ]; then stage="app_installed"; fi
  say "first failing : $stage"
  if [ "$stage" = pipeline_open ]; then
    say "state         : PORTAL_READY_UNTESTED (every hop is present; opening a stream needs a live session and, for a real frame, a real camera)"
  else
    say "state         : PORTAL_INCOMPLETE ($stage) — install the missing hop; no /dev/videoN is ever hard-coded as a fallback"
  fi
  say "privacy       : indicator required; no stealth recording; no hidden mic/camera bypass; background recording is user-controlled with a visible status; stop control always available"
  say "install check : systemctl --user status nuxel-camera-portal"
  if ! faked_root; then say "live check    : $(systemctl --user is-enabled nuxel-camera-portal 2>/dev/null || echo 'not-installed-in-user-manager')"; fi
  say "note          : the CAMERA half of this report is chain evidence only — a captured frame is claimed nowhere without a real capture."
}
cmd_capture() {
  enumerate
  [ -n "$VIDEO" ] || { say "refused: no /dev/video* node exists (NO_V4L2_DEVICE). Nothing to capture; no frame is claimed."; return 2; }
  [ "$YES" = 1 ] || { say "refused: capturing a still is an owner action. Re-run with: $SELF capture --yes <out.jpg>"; return 4; }
  faked_root && { say "refused: offline/faked root — no real capture device is sampled under --root."; return 5; }
  command -v v4l2-ctl >/dev/null 2>&1 || { say "refused: v4l2-ctl (v4l-utils) is not installed; install it or capture from the camera app. No frame claimed."; return 6; }
  local out="${OUT:-}"
  [ -n "$out" ] || out="$(pol_get output.stills_dir)/owner-test-$(date -u +%Y%m%dT%H%M%SZ).jpg"
  [ -e "$out" ] && { say "refused: $out already exists — refusing to overwrite. Pick another name."; return 7; }
  local dev; dev="$(printf '%s' "$VIDEO" | tr ' ' '\n' | head -1)"
  mkdir -p "$(dirname "$out")" 2>/dev/null || true
  say "capture one still: $dev -> $out (bounded, single frame)"
  if v4l2-ctl -d "$dev" --stream-mmap --stream-count=1 --stream-to="$out" >/dev/null 2>&1 && [ -s "$out" ]; then
    say "captured: $(wc -c < "$out" | tr -d ' ') bytes. Verify visually in the gallery, then record PASS/FAIL in the manual-proof fragment."
  else
    say "capture FAILED at the V4L2 layer — report FAIL with the node, the format list and dmesg; no frame is claimed."
    return 1
  fi
}
selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got
  for f in "$fixdir"/camera-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); exp="$(sed -n 's/^state=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | sed -n 's/.*"state":"\([A-Z0-9_]*\)".*/\1/p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-24s state=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-24s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  list) cmd_list ;;
  fw) cmd_fw ;;
  pipeline) cmd_pipeline ;;
  portal) cmd_portal ;;
  capture) cmd_capture ;;
  report) { say "=== nuxel-camera report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || cmd_status; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,30p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
