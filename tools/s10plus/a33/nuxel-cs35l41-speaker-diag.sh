#!/usr/bin/env bash
# Read-only S10+ CS35L40/CS35L41 speaker-output diagnostics.
# This script NEVER writes ALSA controls, sysfs, regmap, GPIO, firmware, or
# service state. It only reads diagnostics and writes evidence files.
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: nuxel-cs35l41-speaker-diag.sh [--out DIR] [--watch-seconds N] [--interval-ms N]

READ-ONLY diagnostics for the S10+ beyond2lte CS35L40-compatible / CS35L41
speaker amplifier path. The optional watcher samples the RDMA1 PCM and read-only amp output-power
telemetry while an operator independently starts ONE agreed nuxel-pow.mp3 playback.

Options:
  --out DIR            Evidence directory (default: /tmp/nuxel-speaker-diag-UTC)
  --watch-seconds N    Also sample playback/amp telemetry for N seconds
  --interval-ms N      PCM sampling interval (default: 25 ms; min 10 ms)
  --help               Show this message

No playback is initiated. No control or register is modified.
USAGE
}
OUT=""
WATCH_SECONDS=0
INTERVAL_MS=25
while (($#)); do
  case "$1" in
    --out) OUT="${2:?--out requires a directory}"; shift 2 ;;
    --watch-seconds) WATCH_SECONDS="${2:?--watch-seconds requires seconds}"; shift 2 ;;
    --interval-ms) INTERVAL_MS="${2:?--interval-ms requires milliseconds}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ "$WATCH_SECONDS" =~ ^[0-9]+$ ]] || { echo 'watch seconds must be an integer' >&2; exit 2; }
[[ "$INTERVAL_MS" =~ ^[0-9]+$ ]] && ((INTERVAL_MS >= 10 && INTERVAL_MS <= 1000)) || {
  echo 'interval must be an integer between 10 and 1000 ms' >&2; exit 2;
}
if [[ -z "$OUT" ]]; then OUT="/tmp/nuxel-speaker-diag-$(date -u +%Y%m%dT%H%M%SZ)"; fi
mkdir -p "$OUT"
chmod 700 "$OUT" 2>/dev/null || true
umask 077

now() { date -u '+%Y-%m-%dT%H:%M:%S.%3NZ'; }
section() { printf '\n===== %s | %s =====\n' "$1" "$(now)"; }
run_ro() {
  printf '\n$'; printf ' %q' "$@"; printf '\n'
  if command -v timeout >/dev/null 2>&1; then timeout -k 1 5 "$@" 2>&1 || true; else "$@" 2>&1 || true; fi
}
read_file() {
  local f="$1"
  if [[ -r "$f" && -f "$f" ]]; then printf '%s: ' "$f"; tr '\n' ' ' < "$f" 2>/dev/null || true; printf '\n'; fi
}

# Resolve the beyond-madera card by ALSA ID rather than assuming its index.
CARD=""
if [[ -r /proc/asound/cards ]]; then
  CARD="$(awk 'tolower($0) ~ /beyond[-_ ]?madera/ {print $1; exit}' /proc/asound/cards)"
fi
if [[ -z "$CARD" && -r /proc/asound/cards ]]; then
  CARD="$(awk 'tolower($0) ~ /beyondmadera/ {print $1; exit}' /proc/asound/cards)"
fi

{
  section 'SYSTEM'
  run_ro uname -a
  run_ro cat /etc/os-release
  run_ro cat /proc/uptime
  run_ro cat /proc/asound/cards
  printf 'resolved_alsa_card=%s\n' "${CARD:-NOT_FOUND}"
  run_ro cat /proc/cmdline
  run_ro systemctl is-active pipewire.service wireplumber.service nuxel-audio-route.service nuxel-boot-sound.service
  run_ro systemctl status --no-pager nuxel-audio-route.service
  run_ro cat /run/nuxel-audio-route.state
  read_file /sys/devices/platform/18c50000.abox/calliope_version
  read_file /sys/devices/platform/18c50000.abox/power/runtime_status
  read_file /sys/devices/platform/18c50000.abox/power/control
} > "$OUT/00-system.txt"

{
  section 'I2C AMPLIFIER DEVICES'
  for d in /sys/bus/i2c/devices/*; do
    [[ -d "$d" ]] || continue
    name="$(cat "$d/name" 2>/dev/null || true)"
    case "${name,,} $(basename "$d")" in *cs35l40*|*cs35l41*)
      echo "device=$d name=${name:-unknown}"
      echo "driver=$(readlink -f "$d/driver" 2>/dev/null || echo unavailable)"
      echo "of_node=$(readlink -f "$d/of_node" 2>/dev/null || echo unavailable)"
      ;;
    esac
  done
  section 'LIVE DEVICE TREE PROPERTIES'
  DT=/sys/firmware/devicetree/base
  if [[ -d "$DT" ]]; then
    while IFS= read -r -d '' node; do
      echo "NODE=$node"
      for p in compatible reg status cirrus,boost-type cirrus,boost-peak-milliamp \
               cirrus,boost-ind-nanohenry cirrus,boost-cap-microfarad \
               cirrus,gpio1-output-enable cirrus,gpio1-src-select \
               cirrus,gpio1-polarity-invert cirrus,subsystem-id \
               cirrus,right-channel-amp cirrus,dsp-part-name; do
        f="$node/$p"
        [[ -r "$f" ]] || continue
        printf '  %s=' "$p"
        od -An -tx1 "$f" 2>/dev/null | tr -s ' ' | tr '\n' ' '
        printf '\n'
      done
    done < <(find "$DT" -type d \( -iname '*cs35l40*' -o -iname '*cs35l41*' \) -print0 2>/dev/null)
  else
    echo 'Live device tree filesystem unavailable.'
  fi
} > "$OUT/10-amplifier-device-tree.txt"

{
  section 'ALSA CARD / PCM'
  run_ro aplay -l
  run_ro aplay -L
  if [[ -n "$CARD" ]]; then
    for pcm in /proc/asound/card"$CARD"/pcm*p; do
      [[ -d "$pcm" ]] || continue
      echo "PCM=$pcm"
      for f in "$pcm"/info "$pcm"/sub*/hw_params "$pcm"/sub*/status; do read_file "$f"; done
    done
  fi
  section 'PIPEWIRE / PULSE COMPATIBILITY'
  RUNTIME="${NUXEL_PW_RUNTIME:-/run/nuxel-wayland}"
  echo "runtime_dir=$RUNTIME"
  if [[ -S "$RUNTIME/pipewire-0" ]]; then echo 'native_pipewire_socket=present'; else echo 'native_pipewire_socket=missing'; fi
  if command -v pactl >/dev/null 2>&1; then
    env XDG_RUNTIME_DIR="$RUNTIME" PIPEWIRE_RUNTIME_DIR="$RUNTIME" \
      PULSE_SERVER="unix:$RUNTIME/pulse/native" timeout -k 1 4 pactl info 2>&1 || true
    env XDG_RUNTIME_DIR="$RUNTIME" PIPEWIRE_RUNTIME_DIR="$RUNTIME" \
      PULSE_SERVER="unix:$RUNTIME/pulse/native" timeout -k 1 4 pactl list short sinks 2>&1 || true
    env XDG_RUNTIME_DIR="$RUNTIME" PIPEWIRE_RUNTIME_DIR="$RUNTIME" \
      PULSE_SERVER="unix:$RUNTIME/pulse/native" timeout -k 1 4 pactl get-default-sink 2>&1 || true
  fi
  if command -v wpctl >/dev/null 2>&1; then
    env XDG_RUNTIME_DIR="$RUNTIME" PIPEWIRE_RUNTIME_DIR="$RUNTIME" \
      PULSE_SERVER="unix:$RUNTIME/pulse/native" timeout -k 1 4 wpctl status 2>&1 || true
    env XDG_RUNTIME_DIR="$RUNTIME" PIPEWIRE_RUNTIME_DIR="$RUNTIME" \
      PULSE_SERVER="unix:$RUNTIME/pulse/native" timeout -k 1 4 wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1 || true
  fi
} > "$OUT/20-pcm-pipewire.txt"

{
  section 'TARGETED ALSA CONTROL READBACKS'
  if [[ -n "$CARD" ]] && command -v amixer >/dev/null 2>&1; then
    controls=(
      'Right AMP Enable Switch' 'Right AMP Mute' 'Right AMP PCM Gain'
      'Right Digital PCM Volume' 'Right DSP1 Firmware' 'Right DSP1 Preload Switch'
      'Right PCM Source' 'Right Boost Enable'
      'Left AMP Enable Switch' 'Left AMP Mute' 'Left AMP PCM Gain'
      'Left Digital PCM Volume' 'Left DSP1 Firmware' 'Left DSP1 Preload Switch'
      'Left PCM Source' 'Left Boost Enable'
      'ABOX RDMA1_EN' 'ABOX SPKAMP_EN' 'ABOX SPKAMP_A' 'ABOX SPKAMP_B'
      'ABOX SPUS IN1' 'ABOX SPUS OUT1' 'ABOX SIFS1' 'ABOX UAIF1 SPK'
      'ABOX SIFS1 OUT Switch' 'ABOX UAIF1 Switch' 'ABOX Sound Type'
      'ABOX SOUNDBOOST_A' 'ABOX SOUNDBOOST_B' 'ABOX SOUNDBOOST_EN'
      'Left DSP1 Protection cd PL_SPK_OUTPUT_POWER'
      'Right DSP1 Protection cd L_SPK_OUTPUT_POWER'
    )
    for c in "${controls[@]}"; do
      echo "--- $c ---"
      timeout -k 1 3 amixer -c "$CARD" cget name="$c" 2>&1 || true
    done
  else
    echo 'ALSA card or amixer unavailable.'
  fi
} > "$OUT/30-mixer-readbacks.txt"

{
  section 'DSP1 DEBUGFS'
  ROOT_DSP=/sys/kernel/debug/asoc
  if [[ -d "$ROOT_DSP" ]]; then
    while IFS= read -r -d '' dsp; do
      echo "DSP=$dsp"
      for f in "$dsp"/*; do
        [[ -f "$f" && -r "$f" ]] || continue
        case "$(basename "$f")" in
          booted|running|fw_id|fw_id_version|wmfw_file_name|bin_file_name|state|status|halo_state)
            read_file "$f" ;;
        esac
      done
    done < <(find "$ROOT_DSP" -type d -name dsp1 -print0 2>/dev/null)
    section 'DAPM'
    for f in "$ROOT_DSP"/*/dapm; do [[ -f "$f" && -r "$f" ]] && { echo "--- $f ---"; cat "$f"; }; done
  else
    echo 'debugfs ASoC directory unavailable (not mounted or not exposed); script did not mount it.'
  fi
  section 'CIRRUS POWER / SPEAKER OUTPUT TELEMETRY'
  for d in /sys/class/cirrus/* /sys/devices/*/*cirrus* /sys/devices/platform/*cirrus*; do
    [[ -d "$d" ]] || continue
    echo "DIR=$d"
    for f in "$d"/version "$d"/status "$d"/uptime_ms "$d"/amp_power_left "$d"/amp_power_right \
             "$d"/power_left "$d"/power_right "$d"/target_temp_left "$d"/target_temp_right; do
      read_file "$f"
    done
  done
  section 'READ-ONLY REGMAP REGISTER SNAPSHOT'
  for f in /sys/kernel/debug/regmap/*/registers; do
    [[ -r "$f" ]] || continue
    echo "--- $f ---"
    grep -iE '^(00002014|00002018|0000742c|00007438|0000e010|00000040):' "$f" 2>/dev/null || true
  done
} > "$OUT/40-dsp-dapm-registers.txt"

{
  section 'KERNEL AUDIO LOG'
  if command -v journalctl >/dev/null 2>&1; then
    journalctl -k -b --no-pager 2>/dev/null | grep -iE 'cs35l4|cs35l41|cirrus|abox|calliope|rdma1|speaker|spk_out|mailbox|mbox|passport' | tail -n 1200 || true
  elif command -v dmesg >/dev/null 2>&1; then
    dmesg 2>/dev/null | grep -iE 'cs35l4|cs35l41|cirrus|abox|calliope|rdma1|speaker|spk_out|mailbox|mbox|passport' | tail -n 1200 || true
  fi
} > "$OUT/50-kernel-audio-log.txt"

if ((WATCH_SECONDS > 0)); then
  if [[ -z "$CARD" ]]; then
    echo 'Cannot watch PCM: beyond-madera card not found.' > "$OUT/60-playback-watch.txt"
  else
    PCM="/proc/asound/card${CARD}/pcm1p/sub0"
    command -v python3 >/dev/null 2>&1 || { echo 'python3 missing; watcher unavailable.' > "$OUT/60-playback-watch.txt"; exit 0; }
    export NUXEL_DIAG_PCM="$PCM" NUXEL_DIAG_SECONDS="$WATCH_SECONDS" NUXEL_DIAG_INTERVAL_MS="$INTERVAL_MS" NUXEL_DIAG_CARD="$CARD"
    python3 - "$OUT/60-playback-watch.jsonl" <<'PY'
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

out = Path(sys.argv[1])
pcm = Path(os.environ['NUXEL_DIAG_PCM'])
card = os.environ['NUXEL_DIAG_CARD']
duration = int(os.environ['NUXEL_DIAG_SECONDS'])
interval = int(os.environ['NUXEL_DIAG_INTERVAL_MS']) / 1000.0
status = pcm / 'status'
hw_params = pcm / 'hw_params'
next_mixer = 0.0
end = time.monotonic() + duration
with out.open('w', encoding='utf-8') as f:
    while time.monotonic() < end:
        mono = time.monotonic()
        row = {'utc_epoch': time.time(), 'monotonic': mono,
               'pcm_status': status.read_text(errors='replace') if status.exists() else None,
               'hw_params': hw_params.read_text(errors='replace') if hw_params.exists() else None}
        # One read-only ALSA control dump every 250 ms captures dynamic
        # speaker-power and SoundBoost telemetry without a burst of cget calls.
        if mono >= next_mixer:
            try:
                proc = subprocess.run(['amixer', '-c', card, 'contents'],
                                      capture_output=True, text=True,
                                      timeout=0.18, check=False)
                blocks = []
                current = []
                for line in proc.stdout.splitlines():
                    if line.startswith('numid=') and current:
                        block = '\n'.join(current)
                        if any(k in block for k in (
                            'PL_SPK_OUTPUT_POWER', 'L_SPK_OUTPUT_POWER',
                            'SOUNDBOOST_A', 'SOUNDBOOST_B', 'SOUNDBOOST_EN')):
                            blocks.append(block)
                        current = []
                    current.append(line)
                if current:
                    block = '\n'.join(current)
                    if any(k in block for k in (
                        'PL_SPK_OUTPUT_POWER', 'L_SPK_OUTPUT_POWER',
                        'SOUNDBOOST_A', 'SOUNDBOOST_B', 'SOUNDBOOST_EN')):
                        blocks.append(block)
                row['mixer_telemetry_rc'] = proc.returncode
                row['speaker_mixer_telemetry'] = blocks
                row['mixer_telemetry_error'] = proc.stderr[-500:] if proc.stderr else None
            except Exception as exc:
                row['speaker_mixer_telemetry'] = None
                row['mixer_telemetry_error'] = str(exc)
            next_mixer = mono + 0.25
        power = {}
        for base in ('/sys/class/cirrus/*', '/sys/devices/platform/*cirrus*'):
            for directory in glob.glob(base):
                for name in ('power_left', 'power_right', 'amp_power_left', 'amp_power_right'):
                    candidate = Path(directory) / name
                    try:
                        if candidate.is_file() and os.access(candidate, os.R_OK):
                            power[str(candidate)] = candidate.read_text(errors='replace').strip()
                    except OSError:
                        pass
        row['cirrus_power_sysfs'] = power
        f.write(json.dumps(row, separators=(',', ':')) + '\n')
        f.flush()
        time.sleep(interval)
PY
  fi
fi

cat > "$OUT/README.txt" <<EOF2
Nuxel S10+ speaker diagnostics
Captured: $(now)
Output directory: $OUT
Mode: READ-ONLY (no ALSA cset, sysfs write, register write, GPIO write, service restart, or playback)
Card: ${CARD:-NOT_FOUND}
Watch seconds: $WATCH_SECONDS

For a playback observation, start this script with --watch-seconds before
launching a single, separately controlled pw-play test. This script itself
never plays audio. The PCM watcher records status/hw_params during the window.
Review 30-mixer-readbacks.txt and 40-dsp-dapm-registers.txt alongside the
watch JSONL. The watcher samples PCM and read-only speaker-power/SoundBoost
telemetry during playback; a player rc=0 or DMA pointer movement is not
physical audibility.
EOF2

echo "Read-only speaker diagnostics written to: $OUT"
echo "No audio was played and no hardware state was changed."
