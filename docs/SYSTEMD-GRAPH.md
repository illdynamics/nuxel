# Nuxel systemd boot & shutdown analysis

> Generated from live device evidence on the Galaxy S10+ (`beyond2lte`). No timing is fabricated. Values that were not captured say `NOT_CAPTURED`. Boot IDs and raw receipts are listed in §10.

## 1. Device and collection context

| Item | Value |
|---|---|
| Target | Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820, Mali-G76 MP12 |
| Live identity | `/proc/device-tree/model` = `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` |
| Kernel | `4.14.253-gf7194c1d15ed-dirty` (`#5 SMP PREEMPT`, built 2026-11-01) |
| OS | Fedora Linux 43 (Forty Three), aarch64 |
| systemd | `systemd 258 (258.11-1.fc43)` |
| Root filesystem | ext4 on `/dev/sda31` |
| Persistent journal | yes (`journalctl --list-boots` retains boots) |
| Repo checkout | `feature/v0.7.8-beta-pwnage-88000`, HEAD `09bd0b9c670680ab7de758ca44f133815a11b1cd`, `VERSION=v0.8.0-beta` |
| Before boot ID | `5ab43e24-41c6-45c9-9f92-50d10ca58a8b` |
| After boot ID | `7c9fdaef-9a9d-4968-a76e-c541dbfcea0b` |

**Provenance tiers:** every `systemd-analyze` line below is `PASS_DEVICE_RUNTIME`; shutdown lines are `PASS_DEVICE_RUNTIME` from the previous boot journal. No host/VM timing is substituted.

## 2. Boot summary

| Phase | Before (`5ab43e24`) | After (`7c9fdaef`) | Delta |
|---|---:|---:|---:|
| kernel | 3.430 s | 3.459 s | +0.029 s |
| userspace | 12.713 s | 15.840 s | +3.127 s |
| **total** | **16.143 s** | **19.300 s** | **+3.157 s** |
| `multi-user.target` reached | 12.712 s | 13.014 s | +0.302 s |
| Launcher-ready marker | 15.722 s after boot | ≈16.2 s after boot | ≈+0.5 s |

The after boot is **not a matched-condition sample**: `NetworkManager-wait-online` took 9.139 s (vs 5.774 s) and `nuxel-audio-session` hit a pre-existing ALSA `set_hw_params: Invalid argument` race and restarted at 34.7 s. The dependency change in §6 is verified; a material boot-time gain is **not claimed**.

Nuxel readiness markers (device uptime at capture):

| Marker | Before | After |
|---|---:|---:|
| `/run/nuxel-launcher-ready` | 15.722 s | ≈16.2 s |
| `/run/nuxel/preload-cinema.receipt` | 23.402 s | 23.6 s (approx.) |
| `/run/nuxel-home.state` | written on first Home interaction | written on first Home interaction |

## 3. Critical chain

### Before (`5ab43e24`)

```
multi-user.target @12.712s
└─avahi-daemon.service @12.581s +25ms
  └─network-online.target @12.579s
    └─NetworkManager-wait-online.service @6.803s +5.774s
      └─NetworkManager.service @4.163s +2.285s
        └─dbus-daemon.service @4.010s
          └─basic.target @4.003s
```

`NetworkManager-wait-online.service` contributed **5.774 s** to the ordered path because a live-only drop-in made avahi `Wants=`/`After=network-online.target`.

### After (`7c9fdaef`)

```
multi-user.target @13.014s
└─nuxel-wifi.service @8.122s +184ms
  └─network.target @6.686s
    └─NetworkManager.service @4.479s +2.205s
      └─dbus-daemon.service @4.336s
        └─basic.target @4.332s
```

The ordered path no longer traverses `network-online.target` or `NetworkManager-wait-online`. The target still lands at 13.014 s because `nuxel-fallback.service` (a deliberate safety gate) waits for the launcher-ready marker and is ordered before `multi-user.target`. That wait is exactly the launcher's own readiness time; shortening or bypassing it would risk two framebuffer owners or a missing fallback. It is deliberately left intact (§6).

## 4. Service timing (after boot, `systemd-analyze blame`)

| # | Unit | Duration | On ordered critical path? | Assessment |
|---:|---|---:|---|---|
| 1 | `nuxel-abox-firmware-reload.service` | 27.278 s | no | Periodic firmware reload; starts after UI. Not touched. |
| 2 | `NetworkManager-wait-online.service` | 9.139 s | **no** (after avahi fix) | Still pulled by Fedora `dnf-makecache.timer`; off the ordered path. |
| 3 | `nuxel-fallback.service` | 7.022 s | yes (target wait) | Safety gate: waits up to 60 s for launcher readiness. Deliberately preserved. |
| 4 | `nuxel-audio-route.service` | 4.552 s | no | Audio route after UI. |
| 5 | `nuxel-boot-sound.service` | 2.939 s | no | Boot cue after audio route. |
| 6 | `nuxel-audio-route-retry.service` | 2.225 s | no | Audio recovery. |
| 7 | `NetworkManager.service` | 2.205 s | yes | Required for Wi-Fi/SSH; preserved. |
| 8 | `nuxel-device-permissions.service` | 1.289 s | no | Device ownership setup. |
| 9 | `nuxel-soundd.service` | 1.258 s | no | Sound cue owner. |
| 10 | `nuxel-wl-fb.service` | 1.028 s | no | Panel bridge. |

`systemd-analyze blame` is duration, not critical-path contribution. The table above records both.

## 5. Failed/degraded units

| Unit | Before | After | Verdict |
|---|---|---|---|
| `nuxel-audio-session.service` | active | **failed at boot, auto-restarted, active** | Pre-existing PipeWire/ALSA `set_hw_params: Invalid argument` race. It also restarted on the previous boot (`journalctl -b -1`: stop at 20.2 s and restart at 36.2 s). Not caused by this mission; no audio unit was changed. |
| all others | none failed | none failed | `systemctl --failed` empty after recovery. |

## 6. Shutdown timeline

### Baseline boot `5ab43e24` (shutdown triggered by the controlled reboot)

| Event | Monotonic |
|---|---:|
| `Stopping avahi-daemon`, `nuxel-button-manager`, `nuxel-clockd`, `nuxel-haptics`, `nuxel-http-bridge`, `nuxel-nfcd`, `nuxel-soundd`, `nuxel-usb-mode-monitor` | 1515.826–1515.835 s |
| `Stopping nuxel-wl-fb` | 1515.947 s |
| `Stopping nuxel-orientationd` | 1515.970 s |
| `Stopping nuxel-wayland` | 1516.185 s |
| `Stopping nuxel-touch-arm`, `nuxel-web` | 1516.764 s |
| `Shutting down.` | 1516.940 s |
| `systemd-shutdown`: sync filesystems | 1517.112 s |
| `Journal stopped` | 1517.200 s |
| **Measured shutdown window** | **1.374 s** (1515.826 → 1517.200) |

### Earlier boot `0112a081` (independent sample)

| Event | Monotonic |
|---|---:|
| First final stop (`avahi-daemon`) | 114.362 s |
| `Shutting down.` | 115.653 s |
| `Journal stopped` | 115.925 s |
| **Measured shutdown window** | **1.563 s** |

Status: **CAPTURED** for the two baseline boots above; the after-boot (`7c9fdaef`) shutdown is **NOT CAPTURED**.

No timeout, unmount stall, or network-teardown delay was observed in either sample. The after-boot (`7c9fdaef`) shutdown is **`NOT_CAPTURED`** because no shutdown of that boot was performed after the evidence capture. Capture recipe:

```sh
journalctl --list-boots
journalctl -b -1 -o short-monotonic | grep -E 'Stopping|Shutting down|Journal stopped'
```

## 7. Change applied and why

**PWNAGE-91000-SYS-01 — avahi must not pull `network-online.target` into boot.**

- Source: `services/nuxel-s10/systemd/avahi-daemon.service.d/10-nuxel-boot-order.conf`
- Live target: `/etc/systemd/system/avahi-daemon.service.d/10-nuxel-boot-order.conf`
- Change: `After=NetworkManager.service wpa_supplicant.service`; removed `Wants=network-online.target` and `After=network-online.target`; kept `Restart=on-failure`, `RestartSec=3`.
- Safety: avahi still starts, still joins `wlan0`/`lo` via netlink, and still retries a transient early failure. Verified live after `daemon-reload` and `systemctl restart avahi-daemon`:
  - `systemctl show avahi-daemon -p Wants` → `Wants=` (empty)
  - `systemctl list-dependencies --reverse network-online.target` → only `dnf-makecache.timer`
  - mDNS joined `wlan0.IPv6`, `wlan0.IPv4`, `lo.IPv6`, `lo.IPv4`; “Server startup complete”.
- Result: the ordered critical chain moved from `avahi → network-online → NM-wait-online` (12.58 s) to `nuxel-wifi` (8.12 s +184 ms). The target's own completion is now gated by the launcher-readiness fallback, not by network-online.

**Candidates deliberately not changed**

| Candidate | Why not |
|---|---|
| `nuxel-fallback.service` 7.0 s wait | It is the fallback UI safety gate. It waits for the real launcher-ready marker; removing/weakening it could leave no panel owner or start two framebuffer owners. |
| `dnf-makecache.timer` `Wants=network-online.target` | A drop-in `Wants=` is merged, not replaced, by systemd 258 (verified live). A full Fedora unit override would be fragile; the job is off the ordered path after the avahi fix. |
| `nuxel-abox-firmware-reload.service` 27 s | Off the UI path; touches firmware reload behavior. Not optimized. |
| `nuxel-audio-session` retry | Audio hardware/route race; changing it risks speaker/headset behavior. Reported, not altered. |
| WebKit launcher spawn (~5 s) | The first UI is gated by WebKit process start and page commit, not by a service timeout. No safe source-only change was proven in this mission. |

## 8. Optimization opportunities ranked

| Rank | Opportunity | Measured impact | Risk | Decision |
|---:|---|---|---|---|
| 1 | Remove avahi's `network-online` pull-in | 5.774 s removed from the ordered chain (before); target now gated elsewhere | R2, verified live | **Applied** |
| 2 | Make `nuxel-fallback` non-blocking for the target | 7.022 s target wait | R2, safety-gate risk | **Not applied** (deliberate safety gate) |
| 3 | Remove Fedora dnf-cache network-online pull | 9.139 s background job | R2, unit-override fragility | **Not applied** (off critical path) |
| 4 | Shorten launcher/WebKit spawn | ~5–7 s of first-UI path | R2/R3, renderer risk | **Not applied** (no safe proof) |
| 5 | Fix audio-session ALSA retry | 20 s background churn | R2, audio risk | **Reported only** |

## 9. Service preservation matrix

| Protected function | Service | Before | After | Check |
|---|---|---|---|---|
| Visible interactive session | `nuxel-wayland.service` | active | active | `systemctl is-active`; phoc + `nuxel-pwa-host` processes present |
| Panel output | `nuxel-wl-fb.service` | active | active | active, 1440×3040 fb0 |
| SSH/LAN | `sshd.service` | active/enabled | active/enabled | reconnected after controlled reboot |
| Wi-Fi/DNS | `NetworkManager`, `wpa_supplicant` | active | active | Wi-Fi autoconnect `yes`; SSH on 192.168.178.167 |
| Seat/input | `seatd.service` | active | active | active |
| mDNS | `avahi-daemon.service` | active | active | mDNS joined all interfaces |
| NFC OFF-by-default | `nuxel-nfcd.service` | active | active | status remains OFF/BLOCKED_FIRMWARE |
| Bridge/PWA | `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-web` | active | active | RPC and static server respond |
| Audio | `nuxel-audio-session`, `nuxel-soundd`, `nuxel-audio-route` | active | active after retry | pre-existing retry preserved |
| Orientation | `nuxel-orientationd.service` | active | active | active; manual modes intact |
| Watchdog | `nuxel-watchdog-keep.service` | active | active | active |
| Fingerprint fallback | bridge provider | fail-closed | fail-closed | `BLOCKED_SECURE_PROVIDER`, PIN fallback required |
| Torch OFF | LED provider | OFF | OFF | no torch at boot |

No service was disabled, masked, removed, or hidden by this change.

## 10. Raw evidence and reproduction

| Artifact | Path |
|---|---|
| Before systemd dump | `diagnostics/pwnage-91000/baseline/systemd.txt` |
| Before shutdown capture | `diagnostics/pwnage-91000/baseline/shutdown-capture.txt` |
| Before shutdown window | `diagnostics/pwnage-91000/baseline/shutdown-window.txt` |
| After systemd dump | `diagnostics/pwnage-91000/after/systemd.txt` |
| After shutdown window | `diagnostics/pwnage-91000/after/shutdown.txt` |
| Boot SVG (before) | `diagnostics/systemd/boot-5ab43e24-41c6-45c9-9f92-50d10ca58a8b.svg` |
| Boot SVG (after) | captured on device; copy into `diagnostics/systemd/boot-7c9fdaef-*.svg` when needed |
| Existing graph artifacts | `diagnostics/systemd/SYSTEMD-BOOT.svg`, `SYSTEMD-SHUTDOWN.svg` |

Reproduce:

```sh
systemd-analyze time
systemd-analyze blame
systemd-analyze critical-chain multi-user.target
systemd-analyze plot > boot.svg
systemctl list-units --all
systemctl list-unit-files
systemctl --failed
journalctl --list-boots
journalctl -b -1 -o short-monotonic
```

## 11. Limitations

- The before/after boots are not thermally or workload matched; the after boot had a slower Wi-Fi online transition and an audio-session retry.
- `systemd-analyze` does not include bootloader/initramfs time.
- The after-boot shutdown is `NOT_CAPTURED`.
- The fallback safety gate means `multi-user.target` is not a proxy for first interactive frame; launcher-ready is the better UI milestone.
