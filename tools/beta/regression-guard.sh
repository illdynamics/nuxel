#!/usr/bin/env bash
# regression-guard.sh — A32 baseline regression gate (briq-00d)
#
# The A32 build is the floor of the Nuxel beta finalization.  Eleven build groups
# are writing into this tree in parallel; this gate is what stops any of them (or
# a later cycle) from silently regressing what A32 proved on the handset:
#
#   INV-1  launcher/PWA cache invalidation (SW namespace bump + host purge + URL stamp)
#   INV-2  XRGB8888 -> DECON ABGR8888 colour conversion (source + real aarch64 selftest)
#   INV-3  ten-zone status-bar safe areas, S10+ portrait preset = zones 9,10
#   INV-4  hardware button manager as the single owner of gpio_keys
#   INV-5  live USB console keeps existing, staying executable and respawning
#   INV-6  userspace rollback route back to the known-working kiosk launcher
#   INV-7  the A32 release record itself stays byte-identical
#   INV-8  the NO-FLASHING / read-only-.qq / evidence-discipline register survives
#
# Behaviour is pinned hard; bytes are pinned hard only where this baseline owns the
# file exclusively (see docs/beta-finalization/BASELINE-PROTECTION.md section 2).
# An individual assertion may additionally declare "mode": "soft" in the register when
# the file it exercises is owned by another build group during the parallel run: a soft
# assertion that fails is reported as a WARN that names the owner, never as a FAIL and
# never as a silent pass.  Everything defaults to "hard".
#
# The same two-level rule governs FILE pins, and the precedence matters: a files[]
# entry may declare its own "hash_mode" (hard|soft|self) and THAT decides the verdict
# for that file.  The invariant-level "hash_mode" is only the DEFAULT for a file that
# declares none.  A soft file that drifts is therefore a WARN naming the owning group
# - never a FAIL - and the invariant's hard behavioural assertions (regex / json_eq /
# program / suite) still have to pass.  (Repaired by briq-02-gate-failure-repair: the
# guard used to OR the two modes, so INV-6's three bg-04-owned, explicitly soft
# shell/config/systemd-user/*.service pins failed the gate as "hard-pinned".)
#
#   regression-guard.sh                     full gate; exit 0 <=> nothing regressed
#   regression-guard.sh --quiet             print only the per-invariant summary line
#   regression-guard.sh --no-tests          skip the test-suite assertions (fast, hash-only);
#                                           soft assertions are skipped too and say so
#   regression-guard.sh --json              machine-readable result on stdout
#   regression-guard.sh --log PATH          override the log path
#   regression-guard.sh --repin PATH --reason TEXT
#                                           re-pin one protected file (the only sanctioned
#                                           way to move a hard pin; records old+new hash)
#   regression-guard.sh --help
#
# Exit codes: 0 = all enforced checks pass, 1 = at least one FAIL, 2 = usage/manifest error.
#
# SAFETY: this script never touches the phone, the framebuffer, the USB console or any
# block device.  It reads files, executes offline user-space tests, and for the colour
# leg runs the aarch64 bridge binary with --colour-selftest.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
MANIFEST="$ROOT/docs/beta-finalization/baseline-protection.json"
# aarch64 ELFs cannot be executed on this macOS host; the UTM Fedora 43 guest is the
# documented execution channel (override with NUXEL_VM=user@host).
VM_HOST="${NUXEL_VM:-$(jq -r '.vm_host // "nuxel@192.168.64.3"' "$MANIFEST" 2>/dev/null || echo nuxel@192.168.64.3)}"

QUIET=0
JSON=0
RUN_TESTS=1
LOG_OVERRIDE=""
REPIN_PATH=""
REPIN_REASON=""

while [ $# -gt 0 ]; do
  case "$1" in
    --quiet|-q)   QUIET=1; shift ;;
    --json)       JSON=1; QUIET=1; shift ;;
    --no-tests)   RUN_TESTS=0; shift ;;
    --log)        LOG_OVERRIDE="$2"; shift 2 ;;
    --repin)      REPIN_PATH="$2"; shift 2 ;;
    --reason)     REPIN_REASON="$2"; shift 2 ;;
    -h|--help)    sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "regression-guard: unknown option: $1" >&2; exit 2 ;;
  esac
done

if ! command -v jq >/dev/null 2>&1; then
  echo "regression-guard: jq is required (the register is JSON)" >&2
  exit 2
fi
if [ ! -f "$MANIFEST" ]; then
  echo "regression-guard: manifest not found: $MANIFEST" >&2
  exit 2
fi
if ! jq -e '.schema_version == 1 and (.invariants | type == "array")' "$MANIFEST" >/dev/null 2>&1; then
  echo "regression-guard: manifest failed to parse as a schema_version 1 register" >&2
  exit 2
fi

RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')"
if [ -n "$LOG_OVERRIDE" ]; then
  LOG="$LOG_OVERRIDE"
else
  LOG="$ROOT/build/out/beta/regression-guard-$RUN_ID.log"
fi
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
: > "$LOG" 2>/dev/null || true

N_PASS=0
N_FAIL=0
N_WARN=0
N_INFO=0
FAILED_IDS=""
WARNED_IDS=""

to_log() { [ -n "$LOG" ] && printf '%s\n' "$1" >> "$LOG" 2>/dev/null; return 0; }
say()    { to_log "$*"; [ "$QUIET" = "1" ] || printf '%s\n' "$*"; }
raw()    { to_log "$*"; [ "$JSON" = "1" ] || printf '%s\n' "$*"; }
hdr()    { say ""; say "$*"; }

# ---- simple timeout wrapper (coreutils `timeout` when present) -----------------
with_timeout() { # with_timeout SECONDS cmd...
  local secs="$1"; shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$secs" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$secs" "$@"
  else
    "$@"
  fi
}

# judge(): an assertion may declare "mode":"soft" in the register when the file it
# exercises is *owned by another build group* during this parallel run.  A soft
# assertion that fails becomes a WARN naming the owner instead of a FAIL, because the
# hard behavioural assertions for that invariant (regex/json_eq) are the actual gate.
# Default mode is "hard" and behaviour is unchanged for every other assertion.
judge() { # judge INVARIANT LABEL DETAIL   (uses $amode / $aowner)
  if [ "$amode" = "soft" ]; then
    record WARN "$1" "$2 (soft: ${aowner:-owned by another build group})" "$3"
  else
    record FAIL "$1" "$2" "$3"
  fi
}

sha_of() { # sha_of PATH -> hex or empty
  [ -f "$1" ] || return 1
  shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
}

record() { # record STATUS INVARIANT LABEL [DETAIL]
  # DETAIL is optional: callers such as the manifest-consistency check pass 3 args.
  local st="$1" inv="$2" label="$3" detail="${4:-}"
  case "$st" in
    PASS) N_PASS=$((N_PASS + 1)); say "    PASS  $label${detail:+  [$detail]}" ;;
    FAIL) N_FAIL=$((N_FAIL + 1)); FAILED_IDS="$FAILED_IDS $inv"; say "    FAIL  $label${detail:+  [$detail]}" ;;
    WARN) N_WARN=$((N_WARN + 1)); WARNED_IDS="$WARNED_IDS $inv"; say "    WARN  $label${detail:+  [$detail]}" ;;
    INFO) N_INFO=$((N_INFO + 1)); say "    INFO  $label${detail:+  [$detail]}" ;;
  esac
  to_log "  -> $st $inv $label $detail"
}

# ---- --repin: the only sanctioned way to move a pin --------------------------
if [ -n "$REPIN_PATH" ]; then
  if [ -z "$REPIN_REASON" ]; then
    echo "regression-guard: --repin requires --reason '<why this byte changed>'" >&2
    exit 2
  fi
  if [ ! -f "$ROOT/$REPIN_PATH" ]; then
    echo "regression-guard: --repin target does not exist: $REPIN_PATH" >&2
    exit 2
  fi
  NEW_HASH="$(sha_of "$ROOT/$REPIN_PATH")"
  OLD_HASH="$(jq -r --arg p "$REPIN_PATH" '[.invariants[].files[] | select(.path == $p) | .sha256] | first // empty' "$MANIFEST")"
  if [ -z "$OLD_HASH" ]; then
    echo "regression-guard: '$REPIN_PATH' is not a registered protected asset with a pinned hash; nothing to re-pin." >&2
    echo "                  add it to docs/beta-finalization/baseline-protection.json first." >&2
    exit 2
  fi
  REPIN_AT="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  TMP_MANIFEST="$(mktemp -t baseline-protection.XXXXXX)"
  if jq --arg p "$REPIN_PATH" --arg h "$NEW_HASH" --arg old "$OLD_HASH" \
        --arg r "$REPIN_REASON" --arg at "$REPIN_AT" \
        '(.invariants[].files[] | select(.path == $p) | .sha256) = $h
         # A re-pin must move *every* byte expectation for that path, not just the
         # file pin: a type:"sha256" assertion carries its own copy of the expected
         # hash, and leaving it stale would make the register self-contradictory and
         # the very next guard run would fail on the file it just re-pinned.
         | ([.invariants[].assertions[]? | select(.type == "sha256" and .path == $p and .expect == $old)] | length) as $nsha
         | (.invariants[].assertions[]? | select(.type == "sha256" and .path == $p and .expect == $old) | .expect) = $h
         | .history += [{at: $at, event: "repin", path: $p,
                         old_sha256: $old, new_sha256: $h, reason: $r,
                         sha256_assertions_updated: $nsha}]' \
        "$MANIFEST" > "$TMP_MANIFEST"; then
    mv "$TMP_MANIFEST" "$MANIFEST"
    echo "regression-guard: re-pinned $REPIN_PATH"
    echo "  old sha256: ${OLD_HASH:-<none>}"
    echo "  new sha256: $NEW_HASH"
    echo "  reason:     $REPIN_REASON"
    echo "  assertions moved with the pin: $(jq -r '.history[-1].sha256_assertions_updated // 0' "$MANIFEST")"
    echo "  (recorded in the manifest history; the behavioural assertions for that"
    echo "   invariant still have to pass - a re-pin is a claim, not a proof)"
  else
    rm -f "$TMP_MANIFEST"
    echo "regression-guard: re-pin failed to update the manifest" >&2
    exit 2
  fi
fi

# ==============================================================================
# 0. Manifest-integrity and repository hygiene
# ==============================================================================
hdr "== regression-guard ==  manifest: docs/beta-finalization/baseline-protection.json"
say "   root:     $ROOT"
say "   run:      $RUN_ID"
say "   log:      $LOG"
say "   register generated: $(jq -r '.generated_at' "$MANIFEST")"
say "   baseline commit:    $(jq -r '.baseline.commit_a32' "$MANIFEST")"

HYG_FAIL=0
if [ "$(cd "$ROOT" 2>/dev/null && git rev-parse --is-inside-work-tree 2>/dev/null)" != "true" ]; then
  record INFO HYGIENE "root is not inside a git work tree - ignore-rule check not applicable" "$ROOT"
else
for p in docs.zip scripts.zip tools.zip .venv; do
  if (cd "$ROOT" && git check-ignore -q "$p" 2>/dev/null); then
    :
  else
    record FAIL HYGIENE "repository hygiene: '$p' must stay gitignored (125 MB of supplied archives / 772-file virtualenv must never be committed)" "git check-ignore $p"
    HYG_FAIL=1
  fi
done
[ "$HYG_FAIL" = "1" ] || record PASS HYGIENE "repository hygiene: supplied archives and .venv stay gitignored" "docs.zip scripts.zip tools.zip .venv"
fi

# ---- manifest self-consistency: a sha256 assertion must agree with the file pin --
# A type:"sha256" assertion carries its own copy of the expected hash.  If it drifts
# away from the corresponding files[] pin the register contradicts itself (this is
# exactly the defect a --repin used to leave behind).  Detected here as a FAIL.
INCONS="$(jq -r '
  [.invariants[].files[] | select(.sha256 != null and .path != null)] as $files
  | [ .invariants[].assertions[]?
      | select(.type == "sha256" and .path != null and .expect != null)
      | .path as $ap | .expect as $ae
      | ($files | first(.[] | select(.path == $ap))) as $f
      | select($f != null and $f.sha256 != $ae)
      | "\($ap): assertion expects \($ae) but the file pin is \($f.sha256)"
    ] | .[]' "$MANIFEST" 2>/dev/null)"
if [ -n "$INCONS" ]; then
  while IFS= read -r line; do
    [ -n "$line" ] && record FAIL MANIFEST-CONSISTENCY "register is self-contradictory: $line"
  done <<< "$INCONS"
else
  record PASS MANIFEST-CONSISTENCY "sha256 assertions agree with the file pins (a --repin moves both)"
fi

# ==============================================================================
# 1. Hash pins
# ==============================================================================
hdr "== 1. hash pins (hard = FAIL on drift, soft = WARN on drift) =="
HARD_TOTAL=0
HARD_OK=0
n_inv="$(jq '.invariants | length' "$MANIFEST")"
i=0
while [ "$i" -lt "$n_inv" ]; do
  inv_id="$(jq -r ".invariants[$i].id" "$MANIFEST")"
  inv_title="$(jq -r ".invariants[$i].title" "$MANIFEST")"
  inv_mode="$(jq -r ".invariants[$i].hash_mode" "$MANIFEST")"
  n_files="$(jq ".invariants[$i].files | length" "$MANIFEST")"
  j=0
  while [ "$j" -lt "$n_files" ]; do
    fpath="$(jq -r ".invariants[$i].files[$j].path" "$MANIFEST")"
    fexpect="$(jq -r ".invariants[$i].files[$j].sha256 // empty" "$MANIFEST")"
    # A file pin may carry its own hash_mode.  The MODE PRECEDENCE is the rule the
    # register documents in BASELINE-PROTECTION.md section 2 ("soft | the file is
    # shared - another build group is contractually allowed to evolve it right now
    # | drift is a WARN") and section 10 rule 3: an explicit per-file mode WINS,
    # and the invariant-level mode is only the DEFAULT for a file that does not
    # declare one.  Before briq-02-gate-failure-repair the guard ORed the two, so a
    # file explicitly marked soft inside a hard invariant (INV-6's three
    # shell/config/systemd-user/*.service units, owned by bg-04) was reported as a
    # hard-pin FAIL - i.e. another group's announced mid-flight edit could turn the
    # gate red, which is exactly what the mode exists to prevent.
    fmode="$(jq -r ".invariants[$i].files[$j].hash_mode // empty" "$MANIFEST")"
    frule="$(jq -r ".invariants[$i].files[$j].role" "$MANIFEST")"
    fmode_eff="$fmode"
    [ -n "$fmode_eff" ] || fmode_eff="$inv_mode"        # invariant mode = the default
    if [ ! -e "$ROOT/$fpath" ]; then
      record FAIL "$inv_id" "protected file MISSING: $fpath" "$frule"
    elif [ "$fmode" = "self" ]; then
      record INFO "$inv_id" "self-referential pin skipped (the register cannot be pinned to its own hash): $fpath" "$frule"
    elif [ -z "$fexpect" ]; then
      record WARN "$inv_id" "no pinned hash recorded for $fpath" "$frule"
    else
      factual="$(sha_of "$ROOT/$fpath")"
      if [ "$factual" = "$fexpect" ]; then
        [ "$fmode_eff" = "hard" ] && { HARD_TOTAL=$((HARD_TOTAL + 1)); HARD_OK=$((HARD_OK + 1)); }
        say "    ok    $fpath  (${fmode_eff} pin held)"
        to_log "  -> pin $fpath $fmode_eff OK $factual"
      elif [ "$fmode_eff" = "hard" ]; then
        HARD_TOTAL=$((HARD_TOTAL + 1))
        record FAIL "$inv_id" "hard-pinned file changed: $fpath" "want $fexpect got $factual"
      else
        # soft: the bytes moved under a file another group owns.  A WARN, printed
        # loudly with the owning group named - never a pass, never a FAIL for
        # someone else's announced work.
        record WARN "$inv_id" "soft-pinned file drifted (shared with another build group): $fpath" \
          "was $fexpect now $factual (invariant owner: $(jq -r ".invariants[$i].owner_group // \"unstated\"" "$MANIFEST"))"
      fi
    fi
    j=$((j + 1))
  done
  i=$((i + 1))
done
if [ "$HARD_TOTAL" -gt 0 ]; then
  say "   hard pins: $HARD_OK/$HARD_TOTAL held"
fi

# ==============================================================================
# 2. Behavioural assertions from the register
# ==============================================================================
hdr "== 2. behavioural assertions =="
i=0
while [ "$i" -lt "$n_inv" ]; do
  inv_id="$(jq -r ".invariants[$i].id" "$MANIFEST")"
  inv_title="$(jq -r ".invariants[$i].title" "$MANIFEST")"
  say ""
  say "-- $inv_id : $inv_title"
  n_as="$(jq ".invariants[$i].assertions | length" "$MANIFEST")"
  j=0
  while [ "$j" -lt "$n_as" ]; do
    atype="$(jq -r ".invariants[$i].assertions[$j].type" "$MANIFEST")"
    alabel="$(jq -r ".invariants[$i].assertions[$j].label // .invariants[$i].assertions[$j].type" "$MANIFEST")"
    amode="$(jq -r ".invariants[$i].assertions[$j].mode // \"hard\"" "$MANIFEST")"
    aowner="$(jq -r ".invariants[$i].assertions[$j].owned_by // empty" "$MANIFEST")"
    case "$atype" in
      file_exists)
        apath="$(jq -r ".invariants[$i].assertions[$j].path" "$MANIFEST")"
        if [ -e "$ROOT/$apath" ]; then record PASS "$inv_id" "$alabel" "$apath"
        else judge "$inv_id" "$alabel" "missing: $apath"; fi
        ;;
      file_executable)
        apath="$(jq -r ".invariants[$i].assertions[$j].path" "$MANIFEST")"
        if [ -x "$ROOT/$apath" ]; then record PASS "$inv_id" "$alabel" "$apath"
        else judge "$inv_id" "$alabel" "not executable or missing: $apath"; fi
        ;;
      sha256)
        apath="$(jq -r ".invariants[$i].assertions[$j].path" "$MANIFEST")"
        awant="$(jq -r ".invariants[$i].assertions[$j].expect" "$MANIFEST")"
        amiss="$(jq -r ".invariants[$i].assertions[$j].on_missing // \"fail\"" "$MANIFEST")"
        if [ ! -f "$ROOT/$apath" ]; then
          case "$amiss" in
            warn) record WARN "$inv_id" "$alabel" "artefact absent: $apath (gitignored build output; rebuild with bash tools/s10plus/a32/build-a32.sh)" ;;
            info) record INFO "$inv_id" "$alabel" "artefact absent: $apath" ;;
            *)    judge "$inv_id" "$alabel" "missing: $apath" ;;
          esac
        else
          agot="$(sha_of "$ROOT/$apath")"
          if [ "$agot" = "$awant" ]; then record PASS "$inv_id" "$alabel" "$agot"
          else judge "$inv_id" "$alabel" "want $awant got $agot"; fi
        fi
        ;;
      regex)
        apath="$(jq -r ".invariants[$i].assertions[$j].path" "$MANIFEST")"
        apat="$(jq -r ".invariants[$i].assertions[$j].pattern" "$MANIFEST")"
        amin="$(jq -r ".invariants[$i].assertions[$j].min_count // 1" "$MANIFEST")"
        if [ ! -f "$ROOT/$apath" ]; then
          judge "$inv_id" "$alabel" "missing: $apath"
        else
          acount="$(grep -Ec -- "$apat" "$ROOT/$apath" 2>/dev/null || true)"
          [ -n "$acount" ] || acount=0
          if [ "$acount" -ge "$amin" ]; then record PASS "$inv_id" "$alabel" "matches=$acount"
          else judge "$inv_id" "$alabel" "pattern '$apat' matched $acount time(s), need >= $amin in $apath"; fi
        fi
        ;;
      json_eq)
        apath="$(jq -r ".invariants[$i].assertions[$j].path" "$MANIFEST")"
        apointer="$(jq -r ".invariants[$i].assertions[$j].pointer" "$MANIFEST")"
        awant="$(jq -c ".invariants[$i].assertions[$j].expect" "$MANIFEST")"
        if [ ! -f "$ROOT/$apath" ]; then
          judge "$inv_id" "$alabel" "missing: $apath"
        elif ! jq -e . "$ROOT/$apath" >/dev/null 2>&1; then
          judge "$inv_id" "$alabel" "not valid JSON: $apath"
        else
          agot="$(jq -c "$apointer" "$ROOT/$apath" 2>/dev/null || echo '<none>')"
          if [ "$agot" = "$awant" ]; then record PASS "$inv_id" "$alabel" "$apointer = $agot"
          else judge "$inv_id" "$alabel" "$apointer is $agot, want $awant"; fi
        fi
        ;;
      program)
        apath="$(jq -r ".invariants[$i].assertions[$j].path" "$MANIFEST")"
        amiss="$(jq -r ".invariants[$i].assertions[$j].on_missing // \"fail\"" "$MANIFEST")"
        an=$(jq ".invariants[$i].assertions[$j].args | length" "$MANIFEST")
        aargs=""
        k=0
        while [ "$k" -lt "$an" ]; do
          aargs="$aargs $(jq -r ".invariants[$i].assertions[$j].args[$k]" "$MANIFEST")"
          k=$((k + 1))
        done
        awant_exit="$(jq -r ".invariants[$i].assertions[$j].expect_exit // 0" "$MANIFEST")"
        areq="$(jq -r ".invariants[$i].assertions[$j].require_stdout // empty" "$MANIFEST")"
        afor="$(jq -r ".invariants[$i].assertions[$j].forbid_stdout // empty" "$MANIFEST")"
        if [ ! -x "$ROOT/$apath" ]; then
          case "$amiss" in
            warn) record WARN "$inv_id" "$alabel" "binary absent or not executable: $apath (rebuild with bash tools/s10plus/a32/build-a32.sh)" ;;
            info) record INFO "$inv_id" "$alabel" "binary absent: $apath" ;;
            *)    judge "$inv_id" "$alabel" "binary absent or not executable: $apath" ;;
          esac
        else
          afallback="$(jq -r ".invariants[$i].assertions[$j].exec_fallback // \"none\"" "$MANIFEST")"
          aout="$(cd "$ROOT" && with_timeout 120 "$ROOT/$apath" $aargs 2>&1)"
          aexit=$?
          awhere="host"
          # This host is macOS: it cannot exec an aarch64 Linux ELF ("exec format
          # error", rc=126).  When the register says exec_fallback=vm, the artefact is
          # deliberately run on the UTM Fedora 43 aarch64 guest instead - the same
          # escalation tools/s10plus/a32/tests/run-tests.sh performs.
          if [ "$afallback" = "vm" ] && { [ "$aexit" = "126" ] || printf '%s' "$aout" | grep -qi 'cannot execute binary file\|exec format error'; }; then
            awhere="$VM_HOST"
            avmout="$(with_timeout 60 scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 "$ROOT/$apath" "$VM_HOST:/tmp/a32-guard-$RUN_ID-$(basename "$apath")" 2>&1)"
            if [ $? -eq 0 ]; then
              aout="$(with_timeout 120 ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 "$VM_HOST" "chmod +x /tmp/a32-guard-$RUN_ID-$(basename "$apath") && /tmp/a32-guard-$RUN_ID-$(basename "$apath") $aargs; echo __RC=\$?" 2>&1)"
              aexit="$(printf '%s' "$aout" | sed -n 's/^__RC=//p' | tail -1)"
              aout="$(printf '%s' "$aout" | grep -v '^__RC=')"
              [ -n "$aexit" ] || aexit=255
            else
              aexit=255
              aout="scp to $VM_HOST failed: $avmout"
            fi
          fi
          aproblem=""
          if [ "$aexit" = "255" ] && [ "$awhere" != "host" ]; then
            record WARN "$inv_id" "$alabel" "aarch64 artefact cannot run here and $VM_HOST is unreachable (no aarch64 execution channel) - gate unavailable"
            to_log "$aout"
          else
            [ "$aexit" = "$awant_exit" ] || aproblem="exit=$aexit want=$awant_exit"
            if [ -n "$afor" ] && printf '%s' "$aout" | grep -q -- "$afor"; then aproblem="$aproblem; forbidden output '$afor'"; fi
            if [ -n "$areq" ] && ! printf '%s' "$aout" | grep -q -- "$areq"; then aproblem="$aproblem; required output '$areq' absent"; fi
            if [ -z "$aproblem" ]; then
              record PASS "$inv_id" "$alabel" "$(printf '%s' "$aout" | grep -c PASS) PASS line(s) on $awhere"
            else
              judge "$inv_id" "$alabel" "$aproblem (ran on $awhere)"
              to_log "$aout"
            fi
          fi
        fi
        ;;
      suite)
        if [ "$RUN_TESTS" = "0" ]; then
          record INFO "$inv_id" "$alabel" "skipped (--no-tests)"
        else
          apath="$(jq -r ".invariants[$i].assertions[$j].path" "$MANIFEST")"
          ainterp="$(jq -r ".invariants[$i].assertions[$j].interpreter // \"bash\"" "$MANIFEST")"
          awant_exit="$(jq -r ".invariants[$i].assertions[$j].expect_exit // 0" "$MANIFEST")"
          areq="$(jq -r ".invariants[$i].assertions[$j].require_stdout // empty" "$MANIFEST")"
          aneed="$(jq -r ".invariants[$i].assertions[$j].requires_build // empty" "$MANIFEST")"
          if ! command -v "$ainterp" >/dev/null 2>&1; then
            record WARN "$inv_id" "$alabel" "interpreter '$ainterp' absent - suite cannot run here"
          elif [ ! -f "$ROOT/$apath" ]; then
            judge "$inv_id" "$alabel" "missing: $apath"
          elif [ -n "$aneed" ] && [ ! -e "$ROOT/$aneed" ]; then
            record WARN "$inv_id" "$alabel" "gate unavailable: $aneed not built (run: bash tools/s10plus/a32/build-a32.sh)"
          else
            aout="$(cd "$ROOT" && with_timeout 600 "$ainterp" "$ROOT/$apath" 2>&1)"
            aexit=$?
            if [ "$aexit" != "$awant_exit" ]; then
              judge "$inv_id" "$alabel" "exit=$aexit want=$awant_exit: $(printf '%s' "$aout" | tail -3 | tr '\n' '|')"
              to_log "$aout"
            elif [ -n "$areq" ] && ! printf '%s' "$aout" | grep -q -- "$areq"; then
              judge "$inv_id" "$alabel" "required output '$areq' absent (exit=$aexit)"
              to_log "$aout"
            else
              record PASS "$inv_id" "$alabel" "exit=$aexit"
            fi
          fi
        fi
        ;;
      info)
        case "$(jq -r ".invariants[$i].assertions[$j].path // empty" "$MANIFEST")" in
          /dev)
            nodelist="$(ls /dev/cu.usbmodem* /dev/tty.usbmodem* 2>/dev/null | tr '\n' ' ')"
            if [ -n "$nodelist" ]; then
              record INFO "$inv_id" "$alabel" "console node(s) enumerated: $nodelist (reachability is an owner test, not a gate)"
            else
              record INFO "$inv_id" "$alabel" "no CDC-ACM console node enumerated right now"
            fi
            ;;
          *) record INFO "$inv_id" "$alabel" "" ;;
        esac
        ;;
      *)
        record WARN "$inv_id" "$alabel" "unknown assertion type '$atype' in the register"
        ;;
    esac
    j=$((j + 1))
  done
  i=$((i + 1))
done

# ==============================================================================
# 3. Summary
# ==============================================================================
hdr "== summary =="
say "   PASS=$N_PASS  FAIL=$N_FAIL  WARN=$N_WARN  INFO=$N_INFO"
if [ -n "$WARNED_IDS" ]; then
  say "   warned invariants:$WARNED_IDS"
  say "   (soft = a parallel build group changed a shared, protected file, or an assertion"
  say "    marked mode:soft could not be satisfied by the in-flight tree.  The hard behavioural"
  say "    assertions above are the actual gate; a soft signal is never a pass and never a"
  say "    baseline regression.)"
fi
if [ "$N_FAIL" -gt 0 ]; then
  raw "   REGRESSION GUARD: FAIL — failing invariants:$(printf ' %s' $FAILED_IDS | tr ' ' '\n' | sort -u | tr '\n' ' ')"
  say "   A hard pin moves only via: tools/beta/regression-guard.sh --repin <path> --reason '<why>'"
  VERDICT="FAIL"
  RC=1
else
  raw "   REGRESSION GUARD: PASS — the A32 baseline is intact (no failing checks)."
  VERDICT="PASS"
  RC=0
fi
to_log "SUMMARY PASS=$N_PASS FAIL=$N_FAIL WARN=$N_WARN INFO=$N_INFO verdict=$VERDICT"

if [ "$JSON" = "1" ]; then
  printf '{"tool":"regression-guard","run":"%s","verdict":"%s","pass":%d,"fail":%d,"warn":%d,"info":%d,"failed_invariants":"%s","warned_invariants":"%s","log":"%s","baseline_commit":"%s"}\n' \
    "$RUN_ID" "$VERDICT" "$N_PASS" "$N_FAIL" "$N_WARN" "$N_INFO" \
    "$(printf '%s' "$FAILED_IDS" | tr -s ' ' ' ' | sed 's/^ //')" \
    "$(printf '%s' "$WARNED_IDS" | tr -s ' ' ' ' | sed 's/^ //')" \
    "$LOG" "$(jq -r '.baseline.commit_a32' "$MANIFEST")"
fi

exit "$RC"
