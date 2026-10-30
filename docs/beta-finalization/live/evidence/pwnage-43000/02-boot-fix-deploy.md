# PWNAGE-43000 — Boot fix deployment (audio decoupling)

**Date:** 2026-10-30
**Backup on device:** `/root/nuxel-43000-backup/20261030T162614/`

## Root cause
`nuxel-abox-firmware-reload.service` stopped `nuxel-wayland.service` to drop the
PipeWire ABOX runtime-PM reference, because PipeWire ran as a child of the phoc
session (`nuxel-session.sh`). Stopping wayland tore down `nuxel-wl-fb` (AMOLED
display bridge) and the launcher, causing a 3-restart boot storm and stable UI
only at ~31 s.

## Change set (deployed)
1. New `services/nuxel-s10/bin/nuxel-audio-session.sh` → `/usr/lib/nuxel/nuxel-audio-session.sh`
   (standalone PipeWire + WirePlumber + pipewire-pulse + session bus).
2. New `services/nuxel-s10/systemd/nuxel-audio-session.service` →
   `/etc/systemd/system/nuxel-audio-session.service` (enabled, WantedBy=nuxel-wayland.service).
3. `nuxel-session.sh` → audio stack startup removed; only runtime/env exports remain.
4. `nuxel-abox-firmware-reload-boot.sh` → stop/start `nuxel-audio-session.service`
   instead of `nuxel-wayland.service`.
5. `nuxel-abox-firmware-reload.service` → `After=/Wants=` `nuxel-audio-session.service`.

## Live verification BEFORE reboot
- `nuxel-audio-session.service` starts and stops cleanly; `nuxel-wayland.service`
  and `nuxel-wl-fb.service` stay `active` across an audio-session restart.
- Audio route reapplies: `state=applied`, `calliope=MUB0`, `sink=alsa_output.hw_0_1`,
  `rate=48000`, `volume_cap=0.25`.
- `wpctl` shows sink `S10+ speaker (RDMA1, 48 kHz)` vol 0.25.
- `systemd-analyze verify` RC=0; no ordering cycle in
  `nuxel-abox-firmware-reload.service` dependency graph.

## Rollback
```
# on device, as root
B=/root/nuxel-43000-backup/20261030T162614
cp -a $B/nuxel-session.sh /usr/lib/nuxel/nuxel-session.sh
cp -a $B/nuxel-abox-firmware-reload-boot.sh /usr/lib/nuxel/nuxel-abox-firmware-reload-boot.sh
cp -a $B/nuxel-abox-firmware-reload.service /etc/systemd/system/nuxel-abox-firmware-reload.service
rm -f /etc/systemd/system/nuxel-audio-session.service /usr/lib/nuxel/nuxel-audio-session.sh
systemctl disable nuxel-audio-session.service
systemctl daemon-reload
```
