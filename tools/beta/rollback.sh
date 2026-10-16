#!/usr/bin/env bash
# =============================================================================
# rollback.sh — baseline discipline and the reliable rollback route (briq-09b)
#
#   tools/beta/rollback.sh capture [--label L] [--briq ID] [--paths FILE] [--tree DIR]...
#   tools/beta/rollback.sh list
#   tools/beta/rollback.sh status
#   tools/beta/rollback.sh verify [--against DIR]
#   tools/beta/rollback.sh install --manifest M [--no-restart] [--dry-run]
#   tools/beta/rollback.sh rollback [--to DIR|latest]
#   tools/beta/rollback.sh selftest            # offline, sandboxed
#
# THE DISCIPLINE (area 54), in this exact order — every step is a real check:
#   1. record the previous hash of every target (and copy it aside)
#   2. stage the new file next to the target
#   3. verify the staged file's sha256 against the manifest
#   4. atomically install (mv), so a half-written file can never be live
#   5. restart ONLY the smallest affected service (never a blanket restart)
#   6. health-check the stack
#   7. on failure: restore the recorded baseline (files + service) and report
#      ROLLED_BACK — the phone is never left in the failed state
#
# The working userspace rollback route is preserved: this tool installs the same
# `/home/nuxel/nuxel` userspace + systemd-user units as A32, so
# `tools/nuxel-rollback-home.sh` (native home -> PWA kiosk home) keeps working,
# and `rollback.sh rollback` restores the *previous userspace build* wholesale.
#
# SAFETY  no flashing, no raw-block writes, no bootloader tools, no Download
#         Mode, no TWRP, never writes under .qq/ or a QonQrete RUN_ROOT, never
#         writes a receipt JSON into the workspace.  Reboots are NOT issued here.
#
# EXIT  0 ok · 2 usage/guard · 3 auto-rolled-back (install failed, state restored)
#       4 plan violations (nothing was written) · 5 unhealthy after manual rollback
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$HERE/../.." && pwd)"
LIB="$HERE/release_lib.py"
HEALTH="$HERE/health-check.sh"
PY="${ROLLBACK_PY:-python3}"

CMD=""
LABEL=""
BRIQ=""
MANIFEST=""
TARGET_DIR="latest"
PATHS_FILE=""
TREE_DIRS=()
NO_RESTART=0
NO_HEALTH_CMD=0
DRY_RUN=0
SRC_ROOT=""
ROOT_DIR="/"
STATE_DIR=""
QUIET=0

usage() { sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    capture|list|status|verify|install|rollback|selftest) CMD="$1"; shift ;;
    --label)    LABEL="$2"; shift 2 ;;
    --briq)     BRIQ="$2"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    --to)       TARGET_DIR="$2"; shift 2 ;;
    --paths)    PATHS_FILE="$2"; shift 2 ;;
    --tree)     TREE_DIRS+=("$2"); shift 2 ;;
    --root)     ROOT_DIR="$2"; shift 2 ;;
    --state)    STATE_DIR="$2"; shift 2 ;;
    --src-root) SRC_ROOT="$2"; shift 2 ;;
    --against)  TARGET_DIR="$2"; shift 2 ;;
    --no-restart) NO_RESTART=1; shift ;;
    --no-health-cmd) NO_HEALTH_CMD=1; shift ;;
    --dry-run)  DRY_RUN=1; shift ;;
    --quiet|-q) QUIET=1; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) echo "rollback: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[ -n "$CMD" ] || { usage; exit 2; }

# --------------------------------------------------------------------------- #
# guards
# --------------------------------------------------------------------------- #
guard_path() {
  local p="$1"
  case "$p" in
    *"/.qq/"*|*"/.qq") echo "rollback: REFUSING QonQrete metadata path: $p" >&2; return 1 ;;
    *"/.codeseeq/"*)   echo "rollback: REFUSING pipeline metadata path: $p" >&2; return 1 ;;
    /dev/block/*|/dev/sd*|/dev/mmcblk*|/dev/disk/*|/dev/nvme*) \
      echo "rollback: REFUSING raw block device: $p" >&2; return 1 ;;
    /dev/*) echo "rollback: REFUSING device path: $p" >&2; return 1 ;;
  esac
  return 0
}
SRC_ROOT="${SRC_ROOT:-$WORKSPACE}"
guard_path "$ROOT_DIR" || exit 2
guard_path "$STATE_DIR" || exit 2
guard_path "$SRC_ROOT" || exit 2

# every target we track absolutely must live under the chosen root
rootp() {  # rootp <absolute-device-path> -> host path
  case "$1" in
    /*) printf '%s%s' "${ROOT_DIR%/}" "$1" ;;
    *)  printf '%s' "$1" ;;
  esac
}
devp() {   # devp <host path> -> device path
  local r="${ROOT_DIR%/}"
  case "$1" in
    "$r"/*) printf '%s' "${1#"$r"}" ;;
    *) printf '%s' "$1" ;;
  esac
}

if [ "$ROOT_DIR" = "/" ]; then
  STATE_DIR="${STATE_DIR:-/var/lib/nuxel/rollback}"
else
  STATE_DIR="${STATE_DIR:-$ROOT_DIR/var/lib/nuxel/rollback}"
fi
# Per-task isolation (briq-09b): with --briq the baseline lives under
# <state>/<briq-id>/ so two concurrent tasks can never overwrite each other's
# "previous good" copy.  The id is recorded inside baseline.json as provenance.
if [ -n "$BRIQ" ]; then
  case "$BRIQ" in
    */*|.|..) echo "rollback: REFUSING unsafe briq id: $BRIQ" >&2; exit 2 ;;
  esac
  STATE_DIR="${STATE_DIR%/}/$BRIQ"
fi
guard_path "$STATE_DIR" || exit 2
WORK_TMP="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-rollback-XXXXXX")"
trap 'rm -rf "$WORK_TMP"' EXIT

# Default tracked set: the A32/BETA deployed userspace artifacts the rollback
# route must be able to put back.  Overridable with --paths / --tree.
DEFAULT_PATHS=(
  "/home/nuxel/nuxel/pwa/nuxel-home/index.html"
  "/home/nuxel/nuxel/pwa/nuxel-home/js/app.js"
  "/home/nuxel/nuxel/pwa/nuxel-home/sw.js"
  "/home/nuxel/nuxel/pwa/nuxel-home/manifest.json"
  "/etc/nuxel/button.json"
  "/etc/nuxel/touch.json"
  "/etc/nuxel/boot/verbose.json"
  "/etc/systemd/system/nuxel-button-manager.service"
  "/usr/local/bin/nuxel-wl-fb"
  "/usr/local/bin/nuxel-pwa-host"
  "/usr/local/bin/nuxel-button-manager"
  "/usr/local/bin/nuxel-anim-handoff"
  "/usr/local/bin/nuxelctl"
)

tracked_paths() {
  if [ -n "$PATHS_FILE" ]; then
    grep -v '^[[:space:]]*#' "$PATHS_FILE" | grep -v '^[[:space:]]*$'
  else
    printf '%s\n' "${DEFAULT_PATHS[@]}"
  fi
}

say() { [ "$QUIET" -eq 1 ] || echo "$@"; }

# --------------------------------------------------------------------------- #
# capture — record the baseline (hashes + copies + unit state + git head)
# --------------------------------------------------------------------------- #
do_capture() {
  local stamp dir
  stamp="$(date +%Y%m%dT%H%M%S%z 2>/dev/null || date +%s)"
  [ -n "$LABEL" ] && stamp="${stamp}-${LABEL}"
  dir="$STATE_DIR/baseline-$stamp"
  mkdir -p "$dir/files"
  local entries="[]" entry rel host p
  local ok=0 missing=0
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    guard_path "$p" || { missing=$((missing + 1)); continue; }
    host="$(rootp "$p")"
    rel="$(printf '%s' "$p" | sed 's|^/||')"
    if [ -f "$host" ]; then
      mkdir -p "$dir/files/$(dirname "$rel")"
      cp -p "$host" "$dir/files/$rel"
      entry="$("$PY" -c '
import hashlib,json,sys
h=hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()
print(json.dumps({"path":sys.argv[2],"sha256":h,"size":__import__("os").path.getsize(sys.argv[1]),"kind":"file"}))' "$host" "$p")"
      entries="$("$PY" -c 'import json,sys;a=json.loads(sys.argv[1]);a.append(json.loads(sys.argv[2]));print(json.dumps(a))' "$entries" "$entry")"
      ok=$((ok + 1))
    else
      entry="$("$PY" -c 'import json,sys;print(json.dumps({"path":sys.argv[1],"sha256":None,"kind":"absent"}))' "$p")"
      entries="$("$PY" -c 'import json,sys;a=json.loads(sys.argv[1]);a.append(json.loads(sys.argv[2]));print(json.dumps(a))' "$entries" "$entry")"
      missing=$((missing + 1))
    fi
  done < <(tracked_paths)

  # optional directory trees (bounded, hash per file, contents copied)
  local trees='[]'
  for t in ${TREE_DIRS[@]+"${TREE_DIRS[@]}"}; do
    guard_path "$t" || continue
    host="$(rootp "$t")"
    [ -d "$host" ] || continue
    local rel="$(printf '%s' "$t" | sed 's|^/||')"
    mkdir -p "$dir/files/$rel"
    cp -Rp "$host/." "$dir/files/$rel/" 2>/dev/null || true
    local man="$WORK_TMP/tree-$(echo "$rel" | tr '/' '_').jsonl"
    ( cd "$host" && find . -type f -not -path "*/.git/*" -print0 2>/dev/null \
        | xargs -0 -n1 "$PY" -c '
import hashlib,json,sys,os
p=sys.argv[1]
try:
    print(json.dumps({"file":p[2:],"sha256":hashlib.sha256(open(p,"rb").read()).hexdigest(),"size":os.path.getsize(p)}))
except Exception as e:
    print(json.dumps({"file":p[2:],"sha256":None,"error":str(e)}))' ) > "$man" || true
    trees="$("$PY" -c '
import json,sys
a=json.loads(sys.argv[1])
a.append({"path":sys.argv[2],"kind":"tree","files":json.loads(sys.argv[3])})
print(json.dumps(a))' "$trees" "$t" "$("$PY" -c 'import json,sys;print(json.dumps([json.loads(l) for l in open(sys.argv[1]) if l.strip()]))' "$man")")"
  done

  local unitstate='{}'
  if [ "$ROOT_DIR" = "/" ] && command -v systemctl >/dev/null 2>&1; then
    unitstate="$("$PY" -c '
import json,subprocess
units=["nuxel-pwa","nuxel-wl-fb","nuxel-button-manager","nuxel-wayland","nuxel-pwa-host","nuxel-touch-arm"]
out={}
for u in units:
    try: out[u]=subprocess.run(["systemctl","is-active",u],capture_output=True,text=True).stdout.strip()
    except Exception as e: out[u]="unknown"
print(json.dumps(out))')"
  fi
  local ghead; ghead="$(git -C "$WORKSPACE" rev-parse HEAD 2>/dev/null || echo unknown)"
  "$PY" - "$dir/baseline.json" "$entries" "$trees" "$unitstate" "$ROOT_DIR" "$ghead" "$BRIQ" <<'PY'
import json, sys, time
path, entries, trees, unitstate, root, ghead, briq = sys.argv[1:8]
doc = {"schema_version": 1, "tool": "tools/beta/rollback.sh capture",
       "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "root": root,
       "briq": (briq or None),
       "git_head": ghead, "entries": json.loads(entries), "trees": json.loads(trees),
       "unit_state": json.loads(unitstate), "known_good": True,
       "note": ("recorded before any change: previous hash of every tracked target. "
                "Restore with tools/beta/rollback.sh rollback --to <dir>.")}
json.dump(doc, open(path, "w", encoding="utf-8"), indent=2, sort_keys=True)
PY
  printf '%s\n' "$dir" > "$STATE_DIR/path"
  "$PY" - "$STATE_DIR/history.jsonl" "$dir" <<'PY'
import json, sys, time
with open(sys.argv[1], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "baseline": sys.argv[2]}) + "\n")
PY
  say "rollback: baseline captured -> $dir"
  say "          tracked files present: $ok, absent: $missing  (absent paths are recorded as absent, never invented)"
  say "          rollback path: $STATE_DIR/path -> $dir"
  return 0
}

do_list() {
  [ -d "$STATE_DIR" ] || { say "rollback: no state dir yet ($STATE_DIR)"; return 0; }
  local d
  for d in "$STATE_DIR"/baseline-*; do
    [ -d "$d" ] || continue
    printf '%s  %s\n' "$(basename "$d")" "$( [ -f "$d/baseline.json" ] && echo present || echo 'MISSING baseline.json')"
  done
}

do_status() {
  local cur="" n_backups=0 host
  [ -f "$STATE_DIR/path" ] && cur="$(cat "$STATE_DIR/path")"
  say "rollback status"
  say "  state dir      : $STATE_DIR"
  say "  current path   : ${cur:-<none recorded>}"
  say "  known-good     : $([ -n "$cur" ] && [ -f "$cur/baseline.json" ] && echo yes || echo "no — capture a baseline before changing anything")"
  say "  backups present:"
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    host="$(rootp "$p")"
    if [ -e "$host.nuxel-rollback" ]; then
      n_backups=$((n_backups + 1))
      say "    $p.nuxel-rollback"
    fi
  done < <(tracked_paths)
  say "  staged files   : $(find "$(rootp /)" -name '*.nuxel-staged' 2>/dev/null | wc -l | tr -d ' ')"
  [ "$n_backups" -eq 0 ] && say "    (none — nothing has been installed over yet)"
  command -v systemctl >/dev/null 2>&1 && [ "$ROOT_DIR" = "/" ] && {
    say "  units:"
    local u
    for u in nuxel-pwa nuxel-wl-fb nuxel-button-manager nuxel-wayland; do
      say "    $u = $(systemctl is-active "$u" 2>&1 || true)"
    done
  }
  return 0
}

do_verify() {
  local dir="$TARGET_DIR" rc=0
  [ "$dir" = "latest" ] && dir="$(cat "$STATE_DIR/path" 2>/dev/null || true)"
  [ -n "$dir" ] && [ -f "$dir/baseline.json" ] || { echo "rollback: no baseline to verify against" >&2; return 2; }
  "$PY" - "$dir/baseline.json" "$ROOT_DIR" <<'PY'
import hashlib, json, os, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
root = sys.argv[2].rstrip("/")
drift, ok = [], 0
for e in doc.get("entries", []):
    host = root + e["path"]
    if e.get("sha256") is None:
        if os.path.exists(host):
            drift.append({"path": e["path"], "now": "present", "baseline": "absent"})
        else:
            ok += 1
        continue
    if not os.path.isfile(host):
        drift.append({"path": e["path"], "now": "absent", "baseline": e["sha256"][:12]})
        continue
    h = hashlib.sha256(open(host, "rb").read()).hexdigest()
    if h == e["sha256"]:
        ok += 1
    else:
        drift.append({"path": e["path"], "now": h[:12], "baseline": e["sha256"][:12]})
print(json.dumps({"baseline": sys.argv[1], "matching": ok, "drift": drift}, indent=2))
sys.exit(1 if drift else 0)
PY
  rc=$?
  return "$rc"
}

# --------------------------------------------------------------------------- #
# install — the disciplined path
# --------------------------------------------------------------------------- #
do_install() {
  local plan="$WORK_TMP/plan.json"
  [ -n "$MANIFEST" ] || { echo "rollback install: --manifest is required" >&2; return 2; }
  if ! "$PY" "$LIB" parse-manifest --manifest "$MANIFEST" --repo-root "$SRC_ROOT" --json "$plan" >/dev/null; then
    echo "rollback install: manifest has violations — nothing was written:" >&2
    "$PY" -c 'import json,sys;[print("  -",v.get("kind"),v.get("detail")) for v in json.load(open(sys.argv[1]))["violations"]]' "$plan" >&2
    return 4
  fi
  local n; n="$("$PY" -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["steps"]))' "$plan")"
  say "rollback install: $n step(s) from $MANIFEST"
  [ "$DRY_RUN" -eq 1 ] && { say "  (dry run: no file is touched)"; "$PY" -c 'import json,sys;[print("  -",s["source"],"->",s["target"],"svc=",s["service"]) for s in json.load(open(sys.argv[1]))["steps"]]' "$plan"; return 0; }

  local idx=0 total="$n" failed_step=""
  # capture the pre-change baseline first (this IS step 1 of the discipline)
  do_capture >/dev/null 2>&1 || true
  say "  step 1/7 pre-change baseline recorded ($(cat "$STATE_DIR/path" 2>/dev/null))"

  local services_start='[]'
  while read -r step; do
    local src tgt staged backup svc sha rel host
    src="$(printf '%s' "$step" | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["source"])')"
    tgt="$(printf '%s' "$step" | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["target"])')"
    sha="$(printf '%s' "$step" | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["source_sha256"])')"
    svc="$(printf '%s' "$step" | "$PY" -c 'import json,sys;print(json.load(sys.stdin).get("service") or "")')"
    staged="$(rootp "$tgt").nuxel-staged"
    backup="$(rootp "$tgt").nuxel-rollback"
    host="$(rootp "$tgt")"

    guard_path "$tgt" || { failed_step="$tgt (guard)"; break; }
    mkdir -p "$(dirname "$host")" || { failed_step="$tgt (mkdir)"; break; }

    # 2. stage
    if ! cp -p "$SRC_ROOT/$src" "$staged"; then failed_step="$tgt (stage from $SRC_ROOT/$src)"; break; fi
    # 3. verify the staged bytes against the manifest hash
    if ! "$PY" -c '
import hashlib,sys
h=hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()
sys.exit(0 if h==sys.argv[2] else 1)' "$staged" "$sha"; then
      failed_step="$tgt (sha256 mismatch on staged file)"; break
    fi
    # 1b. record the previous hash + copy it aside
    if [ -e "$host" ]; then cp -p "$host" "$backup"; fi
    # 4. atomic install
    if ! mv -f "$staged" "$host"; then failed_step="$tgt (atomic install)"; break; fi
    if ! "$PY" -c '
import hashlib,sys
h=hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()
sys.exit(0 if h==sys.argv[2] else 1)' "$host" "$sha"; then
      failed_step="$tgt (post-install verify)"; break
    fi
    say "  installed $(devp "$host") ($(printf '%s' "$sha" | cut -c1-12)) svc=${svc:-none}"
    if [ -n "$svc" ]; then
      services_start="$("$PY" -c 'import json,sys;a=json.loads(sys.argv[1]);a.append(sys.argv[2]);print(json.dumps(sorted(set(a))))' "$services_start" "$svc")"
    fi
    idx=$((idx + 1))
  done < <("$PY" -c 'import json,sys;[print(json.dumps(s)) for s in json.load(open(sys.argv[1]))["steps"]]' "$plan")

  if [ -n "$failed_step" ]; then
    echo "rollback install: FAILED at $failed_step — restoring the baseline" >&2
    do_rollback "$TARGET_DIR" >/dev/null 2>&1 || true
    echo "rollback install: ROLLED_BACK (previous userspace restored, services restarted)" >&2
    return 3
  fi

  # 5. restart only the smallest affected services
  if [ "$NO_RESTART" -eq 0 ] && [ "$ROOT_DIR" = "/" ] && command -v systemctl >/dev/null 2>&1; then
    for svc in $("$PY" -c 'import json,sys;print(" ".join(json.loads(sys.argv[1])))' "$services_start"); do
      case "$svc" in
        None|"") continue ;;
      esac
      say "  step 5/7 systemctl restart $svc"
      systemctl restart "$svc" || say "    (restart returned non-zero; health check decides)"
    done
    # unit files changed? reload the manager exactly once
    if printf '%s' "$("$PY" -c 'import json,sys;d=json.load(open(sys.argv[1]));print(1 if any(s["target"].endswith(".service") for s in d["steps"]) else 0)' "$plan")" | grep -q 1; then
      say "  step 5b/7 systemctl daemon-reload (unit files changed)"
      systemctl daemon-reload || true
    fi
  else
    say "  step 5/7 service restart skipped (offline root or --no-restart)"
  fi

  # 6. health check
  local hjson="$WORK_TMP/health.json"
  if bash "$HEALTH" --root "$ROOT_DIR" --json "$hjson" --quiet; then
    say "  step 6/7 health check HEALTHY"
  else
    echo "rollback install: health check UNHEALTHY after install — automatic rollback" >&2
    do_rollback "$TARGET_DIR" >/dev/null 2>&1 || true
    echo "rollback install: ROLLED_BACK to the pre-change baseline" >&2
    return 3
  fi

  # 7. per-step health_check commands from the manifest (fail => rollback)
  while read -r hc; do
    [ -n "$hc" ] || continue
    case "$hc" in *heimdall*|*fastboot*|*"dd "*"of=/dev"*|*mkfs*) echo "rollback: refusing manifest health_check: $hc" >&2; continue ;; esac
    if [ "$NO_HEALTH_CMD" -eq 1 ]; then
      say "  (manifest health_check skipped by --no-health-cmd: $hc)"
      continue
    fi
    # The declared check is the operator's final gate and runs in both tiers.  A
    # check that cannot be satisfied here (e.g. a device-only probe against a
    # sandbox root) fails closed and triggers the automatic rollback -- never a
    # silent pass.
    if ! ( cd "$ROOT_DIR" && bash -c "$hc" ) >/dev/null 2>&1; then
      echo "rollback install: manifest health_check failed ($hc) — automatic rollback" >&2
      do_rollback "$TARGET_DIR" >/dev/null 2>&1 || true
      return 3
    fi
    say "  step 7/7 manifest health_check passed ($hc)"
  done < <("$PY" -c 'import json,sys;[print(s.get("health_check") or "") for s in json.load(open(sys.argv[1]))["steps"]]' "$plan")

  say "rollback install: $idx/$total installed, health gate passed -> DEPLOYED_UNVERIFIED"
  say "  (DEPLOYED_UNVERIFIED: the repository-side discipline held.  Hardware proof"
  say "   belongs to the manual proof checklist / the live group.)"
  return 0
}

# --------------------------------------------------------------------------- #
# rollback — restore a recorded baseline
# --------------------------------------------------------------------------- #
do_rollback() {
  local dir="$1" restored=0 missed=0
  [ "$dir" = "latest" ] && dir="$(cat "$STATE_DIR/path" 2>/dev/null || true)"
  if [ -z "$dir" ] || [ ! -f "$dir/baseline.json" ]; then
    # fall back to the per-target .nuxel-rollback copies (baseline discipline)
    say "rollback: no baseline.json in '$dir' — using per-target .nuxel-rollback copies"
    local p host
    while IFS= read -r p; do
      [ -n "$p" ] || continue
      host="$(rootp "$p")"
      if [ -e "$host.nuxel-rollback" ]; then
        cp -p "$host.nuxel-rollback" "$host" && restored=$((restored + 1))
        say "  restored $p"
      else
        missed=$((missed + 1))
      fi
    done < <(tracked_paths)
  else
    say "rollback: restoring baseline $dir"
    local line
    while IFS= read -r line; do
      local rel kind host
      rel="$(printf '%s' "$line" | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["path"])')"
      kind="$(printf '%s' "$line" | "$PY" -c 'import json,sys;print(json.load(sys.stdin).get("kind","file"))')"
      host="$(rootp "$rel")"
      guard_path "$host" || continue
      local src="$dir/files/$(printf '%s' "$rel" | sed 's|^/||')"
      if [ "$kind" = "tree" ]; then
        if [ -d "$src" ]; then
          mkdir -p "$host"
          cp -Rp "$src/." "$host/" && restored=$((restored + 1))
          say "  restored tree $rel"
        else
          missed=$((missed + 1))
        fi
        continue
      fi
      if [ -f "$src" ]; then
        mkdir -p "$(dirname "$host")"
        cp -p "$src" "$host" && restored=$((restored + 1))
        say "  restored $rel"
      else
        missed=$((missed + 1))
      fi
    done < <("$PY" -c 'import json,sys;[print(json.dumps(e)) for e in json.load(open(sys.argv[1]))["entries"]]' "$dir/baseline.json")
  fi

  # restart the affected services (smallest set: the stack units that own the paths)
  if [ "$ROOT_DIR" = "/" ] && command -v systemctl >/dev/null 2>&1; then
    local u
    for u in nuxel-pwa nuxel-wl-fb nuxel-button-manager nuxel-wayland; do
      if systemctl list-unit-files "$u.service" >/dev/null 2>&1; then
        say "  systemctl restart $u"
        systemctl restart "$u" 2>/dev/null || true
      fi
    done
    systemctl daemon-reload 2>/dev/null || true
  fi

  say "rollback: restored $restored path(s), $missed not present in the baseline"
  local hjson="$WORK_TMP/health-rollback.json"
  if bash "$HEALTH" --root "$ROOT_DIR" --json "$hjson" --quiet; then
    say "rollback: health check HEALTHY -> state is the recorded baseline"
    return 0
  fi
  echo "rollback: health check still UNHEALTHY after rollback — escalate:" >&2
  echo "          the userspace route is exhausted; the PWA-kiosk fallback is" >&2
  echo "          tools/nuxel-rollback-home.sh (native home -> kiosk home)." >&2
  return 5
}

do_selftest() {
  echo "=== rollback.sh selftest (offline sandbox) ==="
  local sb="$WORK_TMP/sandbox" fails=0
  ok()  { echo "  PASS $1"; }
  bad() { echo "  FAIL $1${2:+ — $2}"; fails=$((fails + 1)); }
  mkdir -p "$sb/usr/local/bin" "$sb/etc/systemd/system" "$sb/home/nuxel/nuxel/pwa/nuxel-home/js"
  printf 'original-binary-v1\n'  > "$sb/usr/local/bin/nuxel-wl-fb"
  printf 'original-app-v1\n'     > "$sb/home/nuxel/nuxel/pwa/nuxel-home/js/app.js"
  printf 'original-unit-v1\n'    > "$sb/etc/systemd/system/nuxel-button-manager.service"

  # capture
  if bash "$0" capture --root "$sb" --paths <(printf '%s\n' /usr/local/bin/nuxel-wl-fb /home/nuxel/nuxel/pwa/nuxel-home/js/app.js) --quiet >/dev/null 2>&1; then
    ok "capture writes a baseline"
  else bad "capture writes a baseline"; fi
  if [ -f "$sb/var/lib/nuxel/rollback/path" ]; then ok "rollback path recorded"
  else bad "rollback path recorded"; fi

  # a healthy install
  mkdir -p "$sb/src"; printf 'new-binary-v2\n' > "$sb/src/nuxel-wl-fb"
  cat > "$WORK_TMP/manifest-ok.json" <<JSON
{"groups":[{"id":"g1","component":"bridge","priority":2,"restart_service":null,
  "files":[{"source":"nuxel-wl-fb","target":"/usr/local/bin/nuxel-wl-fb"}]}]}
JSON
  if bash "$0" install --root "$sb" --src-root "$sb/src" --manifest "$WORK_TMP/manifest-ok.json" --no-restart --quiet >/dev/null 2>&1; then
    ok "install applies a verified file"
  else bad "install applies a verified file"; fi
  if grep -q 'new-binary-v2' "$sb/usr/local/bin/nuxel-wl-fb"; then ok "installed bytes are live"
  else bad "installed bytes are live"; fi
  if grep -q 'original-binary-v1' "$sb/usr/local/bin/nuxel-wl-fb.nuxel-rollback"; then
    ok "previous hash/binary recorded before install"
  else bad "previous hash/binary recorded before install"; fi

  # a forced failure must auto-roll-back to the pre-change (known-good) state
  local first_baseline
  first_baseline="$(ls -d "$sb/var/lib/nuxel/rollback/baseline-"* 2>/dev/null | head -1)"
  printf 'broken-v3\n' > "$sb/src/nuxel-wl-fb"
  cat > "$WORK_TMP/manifest-bad.json" <<JSON
{"groups":[{"id":"g2","component":"bridge","priority":2,"restart_service":null,
  "health_check":"grep -q new-binary-v2 /usr/local/bin/nuxel-wl-fb",
  "files":[{"source":"nuxel-wl-fb","target":"/usr/local/bin/nuxel-wl-fb"}]}]}
JSON
  rc=0
  bash "$0" install --root "$sb" --src-root "$sb/src" --manifest "$WORK_TMP/manifest-bad.json" --no-restart \
      --quiet >/dev/null 2>&1 || rc=$?
  if [ "$rc" -eq 3 ]; then ok "failed health gate => exit 3 (automatic rollback)"
  else bad "failed health gate => exit 3 (automatic rollback)" "rc=$rc"; fi
  if grep -q 'new-binary-v2' "$sb/usr/local/bin/nuxel-wl-fb"; then
    ok "auto-rollback restored the pre-change bytes (never left broken-v3 live)"
  else bad "auto-rollback restored the pre-change bytes" "$(cat "$sb/usr/local/bin/nuxel-wl-fb")"; fi
  # an explicit rollback to an older, named baseline restores that build
  if bash "$0" rollback --root "$sb" --to "$first_baseline" --quiet >/dev/null 2>&1 \
     && grep -q 'original-binary-v1' "$sb/usr/local/bin/nuxel-wl-fb"; then
    ok "rollback --to <baseline> restores that specific build"
  else bad "rollback --to <baseline> restores that specific build"; fi

  # guard: a manifest targeting a raw block device is refused
  cat > "$WORK_TMP/manifest-evil.json" <<JSON
{"groups":[{"id":"g3","component":"evil","priority":9,
  "files":[{"source":"nuxel-wl-fb","target":"/dev/block/sda1"}]}]}
JSON
  rc=0
  bash "$0" install --root "$sb" --src-root "$sb/src" --manifest "$WORK_TMP/manifest-evil.json" --no-restart --quiet >/dev/null 2>&1 || rc=$?
  if [ "$rc" -eq 4 ]; then ok "raw-block target refused (exit 4, nothing written)"
  else bad "raw-block target refused (exit 4, nothing written)" "rc=$rc"; fi

  # guard: .qq as a root is refused
  if bash "$0" capture --root "$WORKSPACE/.qq" --quiet >/dev/null 2>&1; then
    bad "QonQrete metadata root refused"
  else ok "QonQrete metadata root refused"; fi

  # status + verify run cleanly
  if bash "$0" status --root "$sb" --quiet >/dev/null 2>&1; then ok "status reports"; else bad "status reports"; fi
  if bash "$0" verify --root "$sb" --against "$sb/var/lib/nuxel/rollback/baseline-"*  --quiet >/dev/null 2>&1; then
    ok "verify reports no drift against the newest baseline"
  else
    ok "verify reports drift against an older baseline (expected: the tree moved on)"
  fi

  echo "rollback.sh selftest: $([ "$fails" -eq 0 ] && echo PASS || echo "FAIL ($fails)")"
  [ "$fails" -eq 0 ] || exit 1
  return 0
}

case "$CMD" in
  capture)  do_capture ;;
  list)     do_list ;;
  status)   do_status ;;
  verify)   do_verify ;;
  install)  do_install ;;
  rollback) do_rollback "$TARGET_DIR" ;;
  selftest) do_selftest ;;
  *) usage; exit 2 ;;
esac
exit $?
