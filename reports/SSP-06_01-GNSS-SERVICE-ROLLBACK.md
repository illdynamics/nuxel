# SSP-06_01 — GNSS Service Rollback Runbook

**Audience:** owner operating the handset directly (or a follow-up prompt with an
explicit instruction). **Scope:** userspace only.

## 0. What "rollback" means here

Two independent changes were made:

| # | Change | Rollback |
|---|---|---|
| R1 | Deployed `nuxel_lhd.py` / `nuxel_bbd_tl.py` replaced with repo HEAD | copy originals back from the rollback bucket |
| R2 | Unit stopped, disabled, drop-in condition added | remove drop-in, re-enable, start |

Rolling back **R1 alone** re-installs the unsafe boot behavior *if* the unit can
start. Roll back R1 **only** together with keeping R2 in place, or with explicit
owner authorization for the GNSS RF path.

## 1. Authoritative hashes

Current (hardened, deployed):

```
aeed416dd3d1bfb6e2b3c3a28cb2d1e9c425323ab618bf314903161b01540cd1  nuxel_lhd.py      # repo HEAD
085096a99ebeb8de4feb9b2ab2ed5257927aa353ae7533cd2e15bc57997cd20d  nuxel_bbd_tl.py   # repo HEAD
72679d2e9b332555854ce6e04cb2e1456528a3015c61729e05cba3588bf3f00f  nuxel_control.py  # unchanged
```

Original on-device state, stored in `/var/lib/nuxel/ssp-06_01/rollback/`:

```
6d90a2c0106fbceb333c5d0da40293a6a0258c42cd54df82f2d5653cd377a1ca  nuxel_lhd.py      # STALE, unsafe
7af7cee849ddc22aee1ff51fa12ce7ef454c1c1ec8cdd0b3db0f054a0d947d0d  nuxel_bbd_tl.py   # STALE
72679d2e9b332555854ce6e04cb2e1456528a3015c61729e05cba3588bf3f00f  nuxel_control.py  # unchanged
eb3455dbb9137f2c86e5a87157ba75c644adebade33e1ed83a1bf218610d80bb  nuxel-gnss-lhd.service
```

`/var/lib/nuxel/ssp-06_01/rollback/SHA256SUMS` is the on-device copy of the same
list; verify it before use: `cd /var/lib/nuxel/ssp-06_01/rollback && sha256sum -c SHA256SUMS`.

## 2. Re-enable the service without reverting the code

```sh
sudo rm -f /etc/systemd/system/nuxel-gnss-lhd.service.d/90-nuxel-06_01-deny-start.conf
sudo rmdir /etc/systemd/system/nuxel-gnss-lhd.service.d 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl enable --now nuxel-gnss-lhd.service
```

With the hardened code this is **safe**: the unit will exit 2 immediately with
`FIRMWARE_UNVERIFIED` and never touch a device or the rail.

## 3. Restore the original (unsafe) userspace

Only with explicit owner acceptance that boot will assert `GPS_PWR_EN=1` (GNSS RF)
and write `ESW:READY` for ~24 s per boot:

```sh
set -e
cd /var/lib/nuxel/ssp-06_01/rollback
sha256sum -c SHA256SUMS
sudo install -m 755 -o root -g root nuxel_lhd.py     /usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py
sudo install -m 755 -o root -g root nuxel_bbd_tl.py  /usr/lib/nuxel/nuxel-gnss/nuxel_bbd_tl.py
sudo install -m 755 -o root -g root nuxel_control.py /usr/lib/nuxel/nuxel-gnss/nuxel_control.py
sudo rm -rf /usr/lib/nuxel/nuxel-gnss/__pycache__
# (then re-enable with section 2 if boot-time start is wanted)
```

Then verify `sha256sum /usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py` equals
`6d90a2c0…` and confirm the rail returns to `0` after the ~24 s session:
`cat /sys/devices/virtual/sec/gps/GPS_PWR_EN/value`.

## 4. Post-rollback verification (either direction)

```sh
sha256sum /usr/lib/nuxel/nuxel-gnss/*.py
systemctl is-enabled nuxel-gnss-lhd.service
systemctl is-active  nuxel-gnss-lhd.service
cat /sys/devices/virtual/sec/gps/GPS_PWR_EN/value      # must be 0 when idle
sudo journalctl -u nuxel-gnss-lhd.service --since -5min --no-pager
```

## 5. What there is no rollback for (and why none is needed)

Nothing outside `/usr/lib/nuxel/nuxel-gnss/`, the unit's enablement, and the
drop-in was changed. No kernel, boot image, device tree, `vdd_mcu_1p8`, firmware,
or MCU state was modified, so recovery from this task is a file restore, not a flash.
