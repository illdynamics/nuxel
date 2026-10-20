#!/bin/sh
# A44 device evidence capture. Synthetic touch is labelled; it is not physical acceptance.
set -eu
D=/var/tmp/nuxel-a44-evidence
mkdir -p "$D"
shot() {
  env XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
      /usr/local/sbin/nuxel-wl-snapshot "$D/$1.ppm" 2>"$D/$1.log"
  gzip -f "$D/$1.ppm"
}
shot home
if [ -e /dev/uinput ]; then
  python3 /var/tmp/nuxel-uinput-touch-probe.py --swipe 2048 80 2048 900 >/tmp/a44-swipe1.log 2>&1 || true
  sleep 1
  shot qs-open
  python3 /var/tmp/nuxel-uinput-touch-probe.py --swipe 2048 900 2048 80 >/tmp/a44-swipe2.log 2>&1 || true
  sleep 1
  python3 /var/tmp/nuxel-uinput-touch-probe.py --swipe 2048 80 2048 900 >/tmp/a44-swipe3.log 2>&1 || true
  sleep 1
  shot qs-reopen
  printf 'home\n' > /run/nuxel-pwa-host.cmd
  sleep 2
else
  echo NO_UINPUT
fi
printf 'launch nuxel-settings\n' > /run/nuxel-pwa-host.cmd
sleep 3
shot settings
printf 'home\n' > /run/nuxel-pwa-host.cmd
sleep 2
printf 'launch org.nuxel.Browser\n' > /run/nuxel-pwa-host.cmd
sleep 3
shot browser
printf 'home\n' > /run/nuxel-pwa-host.cmd
sleep 2
shot home-final
sha256sum "$D"/*.gz
ls -l "$D"
