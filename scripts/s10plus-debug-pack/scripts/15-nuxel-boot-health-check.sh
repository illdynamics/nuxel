#!/usr/bin/env bash
# Useful if any future boot exposes ADB; does NOT require recovery, no modifications.
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out boot-health
check_adb
capture_shell runtime/identity.txt 'id; uname -a; cat /proc/cmdline 2>/dev/null || true; getprop ro.product.device 2>/dev/null || true'
capture_shell runtime/mounts.txt 'cat /proc/mounts'
capture_shell runtime/processes.txt 'ps -ef 2>&1 || ps 2>&1'
capture_shell runtime/graphics-devices.txt 'ls -la /dev/dri /dev/fb0 /sys/class/drm /sys/class/graphics /dev/input 2>&1 || true'
capture_shell runtime/network-devices.txt 'ip link 2>&1 || true'
capture_shell runtime/systemd-boot.txt 'command -v systemctl >/dev/null && { systemctl --no-pager --failed; systemctl --no-pager status greetd; } || true'
capture_shell runtime/journal-critical.txt 'command -v journalctl >/dev/null && journalctl -b --no-pager -p warning -n 250 || true'
capture_shell runtime/journal-display.txt 'command -v journalctl >/dev/null && journalctl -b --no-pager -u greetd -u phosh -u phoc -n 250 || true'
say 'For a Fedora Linux boot, ADB may be unavailable even when Linux itself is running.'
