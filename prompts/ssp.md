codex
All patches are consistent with the built source. Final check that the phone is healthy and running the delivered image:
exec
/bin/zsh -c "adb devices -l; ssh -T -o StrictHostKeyChecking=no root@192.168.178.167 'uname -r; systemctl is-system-running 2>&1; systemctl is-active nuxel-wayland nuxel-orientationd nuxel-ssp-bridge nuxel-bridge 2>&1' > /tmp/health.log 2>&1; sed -n 9,20p /tmp/health.log; ping -c 2 -W 1000 192.168.178.167 2>&1 | tail -2" in /Users/wicked/x/nuxel
 succeeded in 1716ms:
                  Mobile Linux for Control Freaks
4.14.253-gf7194c1d15ed-dirty
running
active
active
active
active
2 packets transmitted, 2 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 8.638/88.937/169.235/80.299 ms

codex
Nuxel is healthy: system `running`, wayland/orientation/bridge/ssp-bridge all `active`, no recovery device. Recording the final note in the report.
exec
/bin/zsh -c "cd /Users/wicked/x/nuxel
cat >> PWNAGE-SSP-REPORT.md <<'EOF'

---

## 9. Final live state (13:16 CET)

"'```
$ uname -r                 4.14.253-gf7194c1d15ed-dirty   (#48)
$ systemctl is-system-running   running
$ systemctl is-active nuxel-wayland nuxel-orientationd nuxel-ssp-bridge nuxel-bridge
active active active active
$ cat /sys/class/sensors/ssp_sensor/nuxel_hub_diag
mcu_probe=1 shutdown=1 resetting=0 sensor_state=0x3feff enable=0x0 shub_irq=443
$ cat accelerometer_sensor/raw_data   -> 0,0,0
$ cat gyro_sensor/raw_data            -> 0,0,0
$ su - nuxel -c "unshare -U true"     -> rc=0
$ nft (meta cgroup classid rule)      -> rc=0
```

The phone is live on the delivered image with no recovery fallback, and the
persisted bridge keeps the transport open for the sensor-hub bring-up attempt.

## 10. Honest completion statement

Two capabilities were actually **fixed and hardware-verified** in this run:

* **per-app firewalling kernel flag** — unprivileged user namespaces now work
  (`unshare -U` rc=0 as the user) and nftables classid matching loads;
* **native BBD/SSP bring-up path** — the kernel registers the SSP device,
  performs recovery, and carries AP↔MCU frames through a glibc peer without
  Bionic.

Automated rotation is **not** achieved because the BCM47752 MCU does not stream
until vendor firmware is downloaded, and that proprietary RPC has no
implementation available to Nuxel.  Per the mission'"'s definition of done this is
reported as **FAIL** for live accelerometer/gyro and **NOT TESTED — OPERATOR
REQUIRED** for the physical rotation cycles.  No synthetic data was used.
EOF
ls -la PWNAGE-SSP-*.md" in /Users/wicked/x/nuxel
 succeeded in 0ms:
-rw-r--r--  1 wicked  staff   1508 Nov 13 12:53 PWNAGE-SSP-BOOT-MANIFEST.md
-rw-r--r--  1 wicked  staff   2441 Nov 13 12:52 PWNAGE-SSP-HARDWARE-MAP.md
-rw-r--r--  1 wicked  staff  14040 Nov 13 12:52 PWNAGE-SSP-REFLASH-LOG.md
-rw-r--r--  1 wicked  staff  12558 Nov 13 12:53 PWNAGE-SSP-REPORT.md
-rw-r--r--  1 wicked  staff   1945 Nov 13 12:52 PWNAGE-SSP-RUNTIME-INVENTORY.md
-rw-r--r--  1 wicked  staff   3676 Nov 13 12:53 PWNAGE-SSP-TEST-RESULTS.md

codex
Done for this continuation. Here's the measured state.

## What was actually fixed and verified on hardware

**Per-app firewalling kernel flag — PASS.** This was the long-standing ENOSPC blocker, and it's now solved, not worked around:
- Root cause found by tracing `create_user_ns()`: Nuxel's PID 1 chroots into the Fedora root, so upstream `current_chrooted()` flagged *every* process as chrooted → ENOSPC. I refined it to accept a chroot reachable inside the mount namespace (`fs/namespace.c`, patch 0016).
- Also fixed a genuine uninitialised-pointer bug in `inc_ucount()` (patch 0014).
- Live: `su - nuxel -c "unshare -U true"` → **rc=0**, `unshare -Ur` → rc=0, `kernel.unprivileged_userns_clone=1`.
- nftables: **`meta cgroup <classid>` loads and counts** (rc=0). Note: this Samsung 4.14 tree has **no `nft_socket` expression**, so `socket cgroup*` can never work here; the classid form is the correct mechanism.

**Native SSP/BBD path — PARTIAL (real progress, not done).** The kernel now registers the SSP device at probe, recovers from failed bring-ups, and carries AP↔MCU frames through the glibc bridge with no Bionic. `/dev/bbd_sensor` is bidirectional and the bridge relays real frames (`dmesg: Nuxel peer tx hdr=0f … -> 11`).

## What is still blocking sensors — measured

The hub receives the handshake frames (SPI TX/RX = 1) but **never answers**: `PZC: rx stat 0xff(PE)`, `get_chipid … timeout`, `raw_data 0,0,0`. The BCM47752 only streams after its application firmware is downloaded. The kernel *serves* that image (`/dev/bbd_patch`, `AsicVersion=0x004775B0`, 438895 B, CRC verified), but the download RPC exists only in vendor `lhd` — which needs `liblog/libutils/libz/libhardware_legacy/libc++/libc/libm/libdl` plus the Android sensor HAL, and the kernel's `bbd_rpc_lh.c` implements only the receive side. I won't fabricate that proprietary framing.

**Live status:** `PARTIAL` — service works, display transform verified (`wlr-randr --transform 270` → readback, then normal). **`FAIL`** for accel/gyro live data. **`NOT TESTED — OPERATOR REQUIRED`** for the physical rotation cycles.

## Flashes

12 verified boot-only flashes (`boot-ssp-v4` → `v14`), each with identity check, backup, on-device hash, write, readback. Nuxel booted every time; recovery was only re-entered via explicit `reboot recovery`. Live: kernel **#48**, `boot-ssp-v14.img` SHA256 `7ad5183a…5e2a`, system `running`, wayland/orientation/ssp-bridge/bridge all `active`, no recovery device.

The five deliverables plus the boot manifest are updated with the measured evidence and explicit statuses. The shortest path to green is a lawful implementation (or isolated Android-compat run) of lhd's patch-download RPC — that's the single remaining gate.
Done for this continuation. Here's the measured state.

## What was actually fixed and verified on hardware

**Per-app firewalling kernel flag — PASS.** This was the long-standing ENOSPC blocker, and it's now solved, not worked around:
- Root cause found by tracing `create_user_ns()`: Nuxel's PID 1 chroots into the Fedora root, so upstream `current_chrooted()` flagged *every* process as chrooted → ENOSPC. I refined it to accept a chroot reachable inside the mount namespace (`fs/namespace.c`, patch 0016).
- Also fixed a genuine uninitialised-pointer bug in `inc_ucount()` (patch 0014).
- Live: `su - nuxel -c "unshare -U true"` → **rc=0**, `unshare -Ur` → rc=0, `kernel.unprivileged_userns_clone=1`.
- nftables: **`meta cgroup <classid>` loads and counts** (rc=0). Note: this Samsung 4.14 tree has **no `nft_socket` expression**, so `socket cgroup*` can never work here; the classid form is the correct mechanism.

**Native SSP/BBD path — PARTIAL (real progress, not done).** The kernel now registers the SSP device at probe, recovers from failed bring-ups, and carries AP↔MCU frames through the glibc bridge with no Bionic. `/dev/bbd_sensor` is bidirectional and the bridge relays real frames (`dmesg: Nuxel peer tx hdr=0f … -> 11`).

## What is still blocking sensors — measured

The hub receives the handshake frames (SPI TX/RX = 1) but **never answers**: `PZC: rx stat 0xff(PE)`, `get_chipid … timeout`, `raw_data 0,0,0`. The BCM47752 only streams after its application firmware is downloaded. The kernel *serves* that image (`/dev/bbd_patch`, `AsicVersion=0x004775B0`, 438895 B, CRC verified), but the download RPC exists only in vendor `lhd` — which needs `liblog/libutils/libz/libhardware_legacy/libc++/libc/libm/libdl` plus the Android sensor HAL, and the kernel's `bbd_rpc_lh.c` implements only the receive side. I won't fabricate that proprietary framing.

**Live status:** `PARTIAL` — service works, display transform verified (`wlr-randr --transform 270` → readback, then normal). **`FAIL`** for accel/gyro live data. **`NOT TESTED — OPERATOR REQUIRED`** for the physical rotation cycles.

## Flashes

12 verified boot-only flashes (`boot-ssp-v4` → `v14`), each with identity check, backup, on-device hash, write, readback. Nuxel booted every time; recovery was only re-entered via explicit `reboot recovery`. Live: kernel **#48**, `boot-ssp-v14.img` SHA256 `7ad5183a…5e2a`, system `running`, wayland/orientation/ssp-bridge/bridge all `active`, no recovery device.

The five deliverables plus the boot manifest are updated with the measured evidence and explicit statuses. The shortest path to green is a lawful implementation (or isolated Android-compat run) of lhd's patch-download RPC — that's the single remaining gate.
tokens used
168,972,234
[codeseeq] stopping owned bridge process (pid=87163)
(base) ╭─[ꝖꝖ]─wicked↯infranux in ~/x/nuxel
╰─❯❯❯ 

