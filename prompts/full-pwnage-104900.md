# FULL-PWNAGE-104900 — Boot, session lifecycle and watchdog stability

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104900.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Make boot and session lifecycle deterministic: no unexpected kernel panic/reboot, no
silent compositor restarts that orphan the remote-desktop mirrors, no watchdog resets,
and a clean, bounded GPU fallback. The phone must come up once and stay up.

---

## 1. Current observed state (2026-11-14 16:03 CET)

```
boot time (this boot)   : ~14:46 CET
nuxel-wayland restarted : 14:48:41 and 14:55:26 (twice, same boot)
/run/nuxel-gpu-fallback : absent (GPU path is active)
systemctl --failed      : clean (0 units)
dmesg                   : "watchdog: watchdog0: watchdog did not stop!"
                          repeated s3c2410-wdt keepalive lines
journal identity        : mixes "WIN-CLIENT" and "2001-1c00-..." hostnames
```

Prior art to read:

- `evidence/live-20261114/BOOTLOOP-ROOT-CAUSE.md` — the most recent bootloop was a
  **kernel panic in `sha1_ce_transform` during NFC firmware download**
  (`s3fwrn5_fw_download`), not an initramfs/TWRP problem.
- `REFLASH-PLAN.md`, `PWNAGE-104400.md` (TEE stall), `PWNAGE-107000-USBNET-REPORT.md`
- `SYSTEMD-GRAPH.md`, `docs/` boot and recovery material.

---

## 2. Non-negotiable rules

1. No flashing without explicit operator approval; produce a manifest first.
2. Every hardening change must keep the phone recoverable (SSH, USB-net or console).
3. Never suppress a panic by unexporting the watchdog, and never mask a failing unit
   to make `systemctl --failed` clean.
4. Bound all restart logic; no unbounded `Restart=always` loops on hardware units.
5. Preserve journal evidence from the failed boots.

---

## 3. Work order

### Step 1 — Boot-cause inventory

- `journalctl --list-boots`, `journalctl -b -1 -p err`, `/proc/last_kmsg`,
  `/sys/fs/pstore/*` if present, and any `dmesg-ramoops-*` in
  `evidence/live-20261114/`.
- Classify each boot: clean / compositor restart / kernel panic / watchdog reset.
- Confirm whether the NFC crypto panic is still possible (kernel rebuilt 2026-11-14
  09:51) by reading the `sha1_ce`/`s3fwrn5` code path and the fix status.

### Step 2 — Session lifecycle

- Why did `nuxel-wayland` restart at 14:48:41 and 14:55:26?
  Journal around those timestamps: phoc exit code, GPU probe result, kbase/EGL
  failure, OOM, or a dependency restart.
- Units using `BindsTo=`/`PartOf=` on the compositor must recover correctly
  (this is exactly what broke XRDP before: the loopback mirror stayed dead).
- Verify the GPU→pixman fallback marker logic is bounded and one-shot per boot.

### Step 3 — Watchdog

- `watchdog: watchdog0: watchdog did not stop!` with keepalives suggests a
  watchdog handle left open or a reset path race. Identify which process holds
  `/dev/watchdog*` (`fuser -v`), and whether `systemd`/`nuxel` arms it correctly.
- Ensure a hung compositor triggers a *controlled* restart, not an SoC reset.

### Step 4 — Fix and verify

1. Reboot 3× — each boot reaches SSH + Wayland + remote desktop without manual help.
2. `systemctl --failed` clean after 10 min uptime.
3. Simulate compositor crash (`systemctl restart nuxel-wayland`) — every dependent
   (VNC, loopback mirror, display bridge) recovers automatically.
4. Confirm no panic/watchdog reset in the boot log.
5. Confirm the load average is not elevated by stuck kernel threads
   (`PWNAGE-104400.md`).

---

## 4. Report contract (`REPORT-PWNAGE-104900.md`)

Boot classification table, restart root cause, watchdog analysis, changes, 3× reboot
evidence, dependency-recovery test, rollback/reflash manifest. End with
`FULLY_DONE` / `PARTIAL` / `BLOCKED`.

---

## 5. 104000 addendum — boot animation + preloading video with audio

Requirements to preserve/verify:

- Boot animation plays from power-on through compositor start, uninterrupted by
  the deploy/reboot work in this mission.
- `nuxel-preloading-screen.mp4` plays **with audio** during session preload.
- No black flash / no overshoot into a frozen frame after the animation.
- Boot takes a bounded time and `systemctl --failed` is empty afterwards.

```sh
$SSH $PHONE 'systemctl list-dependencies --no-pager nuxel-preload* 2>/dev/null; \
  find / -name "nuxel-preloading-screen.mp4" 2>/dev/null; \
  find / -name "*.mp4" -path "*boot*" 2>/dev/null | head'
$SSH $PHONE 'journalctl -b -u nuxel-wayland -u nuxel-preload* --no-pager | head -80'
```
Record a cold-boot video from the Mac (or HDMI capture) and attach it plus
`ffprobe` audio-stream evidence to `evidence/pwnage-104000/boot/`. Verify the
preload video's audio actually reaches the speaker (not just muxed in the file).
Test again after the §4 reboot; if deploy changed the initramfs/boot splash,
diff it and keep the working splash.
