#!/bin/bash
# nuxel-bootmode-oneshot.sh — consume one-shot boot-mode flags at userspace boot.
# Runs once, early (before the display/launcher), from nuxel-bootmode-oneshot.service.
# Each flag is consumed exactly once and cleared so the NEXT boot is always normal.
set -u
FLAGS=/var/lib/nuxel/boot
RUN=/run/nuxel
mkdir -p "$FLAGS" "$RUN" 2>/dev/null || true

if [ -f "$FLAGS/verbose-once" ]; then
  # Verbose boot for THIS boot only. The display/bridge reads /run/nuxel/verbose-boot.
  cat > "$RUN/verbose-boot" <<STATE
EFFECTIVE=1
SOURCE=bootmode-oneshot
CONFIG=verbose-once
STATE
  rm -f "$FLAGS/verbose-once"
fi

if [ -f "$FLAGS/safe-mode-once" ]; then
  # Safe mode for THIS boot only: disable the animation handoff/launcher extras.
  echo "1" > "$RUN/safe-mode"
  rm -f "$FLAGS/safe-mode-once"
fi

if [ -f "$FLAGS/diag-once" ]; then
  mkdir -p /diag
  if [ -x /usr/local/bin/nuxel-diag-pack.sh ]; then
    /usr/local/bin/nuxel-diag-pack.sh || true
  fi
  rm -f "$FLAGS/diag-once"
fi

if [ -f "$FLAGS/debug-once" ]; then
  # Debug logging for THIS boot only. A marker the services read; never persisted.
  echo "1" > "$RUN/debug-logging"
  rm -f "$FLAGS/debug-once"
fi
exit 0
