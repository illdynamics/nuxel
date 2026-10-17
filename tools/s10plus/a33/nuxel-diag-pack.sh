#!/bin/bash
# nuxel-diag-pack.sh — collect a full diagnostics pack into
# /diag/<YYYY-MM-DD_HH-MM-SS_diagnostics-logs-stats.gz
# Read-only collection of logs, stats, hardware identity, versions and settings.
set -u
TS=$(date +%Y-%m-%d_%H-%M-%S)
OUTDIR=/diag
TMP=$(mktemp -d "${TMPDIR:-/tmp}/nuxel-diag.XXXXXX")
D="$TMP/$TS"
mkdir -p "$D"
{
  echo "# Nuxel diagnostics pack"
  echo "at=$TS"
  echo "hostname=$(cat /etc/hostname 2>/dev/null)"
  echo "uname=$(uname -a 2>/dev/null)"
  echo "uptime=$(cat /proc/uptime 2>/dev/null)"
  echo "cmdline=$(cat /proc/cmdline 2>/dev/null)"
  echo "fedora=$(cat /etc/fedora-release 2>/dev/null)"
  echo "nuxel_version=$(cat /VERSION 2>/dev/null)"
  echo "model=$(cat /proc/device-tree/model 2>/dev/null)"
  echo "board=$(cat /sys/firmware/devicetree/base/model 2>/dev/null)"
} > "$D/overview.txt" 2>/dev/null

# logs
mkdir -p "$D/logs"
cp -a /var/log/nuxel "$D/logs/nuxel" 2>/dev/null || true
cp -a /var/log/messages "$D/logs/messages" 2>/dev/null || true
cp -a /var/log/journal "$D/logs/journal" 2>/dev/null || true
journalctl -b --no-pager > "$D/logs/journalctl-boot.txt" 2>/dev/null || true
journalctl -b -p err --no-pager > "$D/logs/journalctl-err.txt" 2>/dev/null || true

# state
mkdir -p "$D/state"
for f in /run/nuxel/* /var/lib/nuxel/fb-owner /var/lib/nuxel/buttons /var/lib/nuxel/anim-handoff.log; do
  [ -e "$f" ] && cp -a "$f" "$D/state/" 2>/dev/null || true
done

# hardware + services
{
  echo "### systemctl failed"
  systemctl --failed --no-pager 2>&1
  echo "### systemctl running"
  systemctl list-units --type=service --state=running --no-pager 2>&1
  echo "### input devices"
  cat /proc/bus/input/devices 2>&1
  echo "### interrupts"
  grep -iE "sec_ts|tsp|touch|usb|dwc3|wlan|brcm|madera" /proc/interrupts 2>&1
  echo "### block"
  lsblk 2>&1 || cat /proc/partitions 2>&1
  echo "### cpu"
  cat /proc/cpuinfo 2>&1
  echo "### mem"
  cat /proc/meminfo 2>&1
  echo "### df"
  df -h 2>&1
  echo "### modules"
  lsmod 2>&1
  echo "### mounts"
  cat /proc/mounts 2>&1
} > "$D/hardware-services.txt" 2>/dev/null

# configs
mkdir -p "$D/etc-nuxel"
cp -a /etc/nuxel "$D/etc-nuxel/nuxel" 2>/dev/null || true

# versions + git hashes
{
  echo "rpm_packages=$(rpm -qa 2>/dev/null | wc -l)"
  rpm -qa 2>/dev/null | sort > "$D/rpmlist.txt" || true
  for b in /usr/lib/nuxel/nuxel-* /usr/local/bin/nuxel-*; do
    [ -e "$b" ] || continue
    echo "$(sha256sum "$b" 2>/dev/null) $b"
  done > "$D/binaries-sha256.txt" 2>/dev/null
} 

(cd "$TMP" && tar -czf "$OUTDIR/${TS}_diagnostics-logs-stats.gz" "$TS") 2>/dev/null
# fallback if tar missing
if [ ! -s "$OUTDIR/${TS}_diagnostics-logs-stats.gz" ]; then
  (cd "$TMP" && gzip -c -r "$TS" > "$OUTDIR/${TS}_diagnostics-logs-stats.gz") 2>/dev/null || true
fi
rm -rf "$TMP" 2>/dev/null || true
echo "DIAG_PACK=$OUTDIR/${TS}_diagnostics-logs-stats.gz"
exit 0
