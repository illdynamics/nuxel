# FULL-PWNAGE-104100 — Restore a working GNSS/GPS fix on Nuxel (S10+ / beyond2lte)

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte` / Exynos 9820
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Mission type:** live regression / bring-up recovery + verification
**Workspace:** repository root (`/Users/wicked/x/nuxel`) and the live phone
**Report to produce:** `REPORT-PWNAGE-104100.md` (repo root)
**Status token required at the end:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

GPS **worked on the previous day** and must work again. Do not start a greenfield GNSS
design exercise. Find out what changed, restore the working path, and prove it with
real hardware evidence. Read the repository and the live phone before editing anything.

The deliverable is: the phone produces a genuine GNSS fix (or a genuine GNSS fix attempt
with satellites in view) that reaches the existing Nuxel Maps UI, surviving a reboot,
with no fabricated coordinates anywhere in the pipeline.

> **Hard rule:** A coordinate is only real if it came from the GNSS receiver. Cached,
> network, Wi-Fi, IP, mock, replay or manually entered coordinates are **not** a fix.
> Never report success based on a file existing, a daemon starting, or a node being
> present.

---

## 1. Known current state (verified at 2026-11-14 15:40–16:00 CET)

These facts were measured on the live device. Re-verify them; do not assume they are
still true, but treat them as the starting hypothesis.

### 1.1 Services

```
nuxel-gnss-lhd.service   inactive (dead)  ← exited 14:46:38 CET
gpsd                     inactive
nuxel-interface-state    active (exited) ← GNSS state restored at boot
```

Journal from the last run:

```
state=TRANSPORT_READY present=True power={'success': True, 'enabled': True}
handshake={'ok': False, 'gps': False, 'elapsed_s': 15.02}
fix_decoded=False
error=transport/handshake boundary reached; GNSS position decode unavailable
       (proprietary lhd/gpsd RPC map)
exit status=2 (SuccessExitStatus=2 → unit reported "deactivated successfully")
```

### 1.2 Device nodes (present)

```
crw------- root root  236,1  /dev/bbd_sensor
crw------- root root  236,2  /dev/bbd_control
crw------- root root  236,3  /dev/bbd_patch
crw------- root root  236,4  /dev/bbd_urgent_patch
crw-rw---- root audio 10,91  /dev/ttyBCM
```

### 1.3 Kernel / SSP

```
[SSP]: debug_work_func(0) - Sensor state: 0x3feff ... GPS: false
```

SSP is alive and explicitly reports `GPS: false`. Sensor-hub firmware is loaded, but
the GNSS block is not powered/armed from the sensor hub's point of view.

### 1.4 Implementations on the image

```
/usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py          (bridge, --session --observe/--handshake-timeout)
/usr/lib/nuxel/nuxel-gnss/nuxel_bbd_tl.py       (BBD transport layer)
/usr/lib/nuxel/nuxel-gnss/nuxel_control.py      (device control / power)
/etc/nuxel/gnss/gnss.json                       (policy, evidence sources, candidate drivers)
/etc/systemd/system/nuxel-gnss-lhd.service
/usr/share/doc/nuxel/docs/hardware/gps/GPS-BLOCKERS.md
/usr/share/doc/nuxel/docs/hardware/gps/GPS-IMPLEMENTATION.md
/usr/share/doc/nuxel/docs/hardware/gps/GPS-TEST-REPORT.md
/usr/share/doc/nuxel/docs/hardware/gps/gnss-bringup-probe.sh
```

### 1.5 Known historical false trails (do not repeat)

- `/dev/ttyBCM` is the **BBD packet transport**, not an NMEA serial port.
- Sensor-hub patches named `SensorHub.patch` / `bcm_sensorhub_a1.patch` /
  `bcm4773_sensorhub.patch` are not automatically valid for this device.
- An open BBD handshake is **not** a fix. A working decode path is required.
- `Restart=on-failure` previously caused an endless 30 s power-cycle loop; it was
  deliberately bounded. Do not "fix" the outage by unbounding restarts.


---

## 2. Non-negotiable operating rules

1. Work from the repository root and read `full-pwnage-gps.md`, `pwnage-gps.md`,
   `REPORT-GPS.md`, `docs/` GPS material, and the on-device docs listed in §1.4
   before changing code.
2. **No flashing, `dd`, Heimdall, TWRP, partition writes, or reboots that could brick
   the handset** without explicit operator approval. Prefer userspace fixes. If a
   kernel/firmware change is genuinely required, produce a reflash manifest and stop
   for approval.
3. Never weaken SELinux, sandboxing, `DevicePolicy`, `NoNewPrivileges`, or PAM.
4. Never `chmod 666` a GNSS node. Use the existing `audio` group / udev policy.
5. Bound every hardware test with a timeout and a guaranteed cleanup path that
   restores GNSS power. A hung test must never leave the receiver powered.
6. Every live test must be reproducible from a documented command. Record command,
   timestamp, return code, and raw output.
7. Preserve recoverability: note current service states and file hashes before edits
   so the previous state can be restored byte-for-byte.
8. Do not delete or "clean up" evidence, backups, or `.bak` files.

---

## 3. Work order

### Step 1 — Establish the regression window (most important)

GPS worked "yesterday". Find out exactly what changed.

- Inventory `/etc/nuxel/gnss/`, `/usr/lib/nuxel/nuxel-gnss/`, the unit file, and any
  `/etc/nuxel/interface-state` or `nuxel-interface-state` records with `mtime`.
- Compare against backups (`.bak-*`, `.nuxel-rollback*`, `backups/`) and repository
  history (`git log --follow` on the GPS paths).
- Check the **sensor hub firmware / SSP state**: was a different SSP patch or firmware
  loaded yesterday? Compare `/sys/class/sensors`, SSP version strings, and the
  `[SSP]` journal around the time it last worked.
- Check the kernel: `uname -a` is
  `4.14.253-gf7194c1d15ed-dirty #3 SMP PREEMPT Sat Nov 14 09:51:04 CET 2026` — the
  kernel was rebuilt **this morning**. Treat that as the prime suspect.
- Check `/proc/modules`, `/sys/module/*/parameters`, and dmesg for GNSS, `ssp`,
  `bcm`, `gps`, `spi`, `sensorhub`.
- Check whether the GNSS rails (`GPS_PWR_EN`, regulators, GPIO) are currently off and
  whether `nuxel_control.py` arms them correctly on this kernel.

Write the regression window conclusion **before** attempting fixes. If the kernel is
the cause, the correct fix may be a boot-image revert, which requires operator
approval — say so plainly rather than hacking around it.

### Step 2 — Reproduce the failure deterministically

```sh
systemctl restart nuxel-gnss-lhd.service
journalctl -u nuxel-gnss-lhd -b -f
```

Expected current output: `TRANSPORT_READY`, `power enabled=True`,
`handshake.ok=False`, `gps=False`, `fix_decoded=False`, exit 2.

Instrument the path (without editing production yet) using the debug helpers:

```sh
/usr/share/doc/nuxel/docs/hardware/gps/gnss-bringup-probe.sh
python3 /usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py --help
```

Capture: BBD transport open result, raw BBD TL frames, SSP `GPS:` field over ~30 s,
power rail state, and the exact point where the handshake times out.

### Step 3 — Diagnose the handshake boundary

Determine which layer fails:

| Layer | Evidence to collect | Failure looks like |
|---|---|---|
| Power | `GPS_PWR_EN`, regulator, GPIO state | rail low / never enabled |
| SSP link | `[SSP] ... GPS:` flips to true | stays `false` |
| BBD transport | `nuxel_bbd_tl` open + ping | open OK, no reply |
| BBD handshake | vendor lhd RPC exchange | timeout / bad magic / version |
| Decode | position report decoded | handshake ok but no fix decoded |

Do not move to the next step until you can state which layer is failing and why.

### Step 4 — Restore the working path

Prefer, in order:

1. Re-enable a previously working userspace configuration (config/unit/script from a
   backup or earlier commit).
2. Fix a regression in `nuxel_lhd.py` / `nuxel_bbd_tl.py` / `nuxel_control.py`
   (bounded, unit-tested).
3. Restore the SSP/sensor-hub state machine to the known-good sequence.
4. Only if the kernel rebuild is proven to be the cause: prepare a boot-image revert
   and request approval. Do not flash autonomously.

Every code change needs a test in `tests/` (the repo already has GNSS tests under
`/usr/lib/nuxel/nuxel-gnss/test_*.py` and repo-side suites). Run them.

### Step 5 — Prove a real fix

Acceptance requires **all** of:

1. `nuxel-gnss-lhd` reaches a state where a decoded position report is produced (or,
   if decode is genuinely blocked, a documented raw NMEA/BBD evidence stream showing
   satellites and a computed fix).
2. `/sys`/journal show `GPS: true` while powered.
3. A coordinate that changes over time (not a single cached value) is exposed through
   the Nuxel location API.
4. The existing Maps app shows the correct current position.
5. A scroll/pan/move test in Maps shows the marker updating with movement.
6. Reboot, wait, and confirm the same result without manual intervention.
7. `systemctl --failed` is clean.

Record raw coordinates, timestamps, satellite/CN0 data if available, and a
screenshot/`grim` capture of Maps.

### Step 6 — Deployment, backup and rollback

- Back up every file you replace (`cp -a file file.bak-104000-$TS`).
- Deploy userspace changes to the live phone and to the repo (`services/`, `tools/`,
  `configs/`, `tests/` as applicable).
- Provide exact rollback commands in the report.
- Update `CHANGELOG.md` / `RELEASE-NOTES.md` only if the repo convention calls for it.

---

## 4. Forbidden shortcuts

- Do not set a default coordinate, "last known location", or seeded position.
- Do not use `geoclue`, `gpsd` with a fake input, or an NMEA replay file as evidence.
- Do not change `SuccessExitStatus`/`Restart=` to make the unit look healthy.
- Do not lower the "GNSS PASS" bar in `gnss.json` or the test suite.
- Do not claim `FULLY_DONE` from indoor/assisted/network results.

---

## 5. Report contract (`REPORT-PWNAGE-104100.md`)

Must contain:

1. Executive result and status token.
2. Regression window: what changed, with evidence.
3. Layer-by-layer diagnosis table from §3 Step 3, filled in.
4. Files changed (path, why, hash before/after).
5. Exact commands run and exact outputs for the acceptance checks in §3 Step 5.
6. Maps acceptance evidence (capture + coordinates + timestamps).
7. Reboot-persistence evidence.
8. Rollback procedure.
9. Remaining blockers, if any, with the precise missing component and a reproducible
   acquisition procedure (never invented firmware).

End with one of:

```
FULLY_DONE — real GNSS fix, Maps verified, survives reboot
PARTIAL    — <what works> / <what is still blocked and why>
BLOCKED    — <exact blocker, evidence, needed approval/component>
```

---

## 6. 104000 addendum — "GPS worked yesterday, today it does not"

Measured 2026-11-14 16:25 CET:

```
nuxel-gnss-lhd.service  inactive (dead), exit 2 after 23.7 s
state=TRANSPORT_READY present=True power={'success': True, 'enabled': True}
handshake={'ok': False, 'gps': False, 'elapsed_s': 15.02}  fix_decoded=False
[SSP]: debug_work_func(0) - Sensor state: 0x3feff ... GPS: false
```

### Regression hunt (do this before any code change)

1. Diff what changed since the last *working* GPS day:
   ```sh
   $SSH $PHONE 'ls -la /etc/nuxel/gnss/ /usr/lib/nuxel/nuxel-gnss/; \
     stat -c "%y %n" /etc/nuxel/gnss/gnss.json /usr/lib/nuxel/nuxel-gnss/*.py'
   $SSH $PHONE 'journalctl -u nuxel-gnss-lhd --since "2 days ago" --no-pager' \
     > evidence/pwnage-104000/gps/journal-2d.txt
   ```
   Look for: config edits on 2026-11-13 23:00 (files show that mtime), SSP/USB-net
   work on 11-13/11-14, power management changes, or a missing GNSS firmware blob.
2. Check the SSP path: is the sensor hub armed for GNSS, and did something
   (usbnet/camera/audio work) power-cycle or re-flash SSP firmware?
3. Check whether the previous good state depended on an **open USB/ADB-side
   session** or a specific boot (e.g. before the `nuxel-postboot.sh` change).
4. Compare current `gnss.json` against `gnss.json.bak-pwnage42000-*` — the 23:00
   edit is the prime suspect.

### Acceptance

- Real fix: lat/lon plus `num_sats_used >= 4`, `fix_quality` > 0, source
  `gnss`/`lhd`, written with timestamps to `evidence/pwnage-104000/gps/`.
- Visible in Nuxel Maps (screenshot, not just a JSON file).
- Survives reboot (§4 of `full-pwnage-104000.md`).
- No mock/network/cache source in the evidence chain.

If firmware/firmware-map is genuinely missing, report `BLOCKED` with the exact
missing artefact and a reproducible acquisition path — never invent coordinates.
