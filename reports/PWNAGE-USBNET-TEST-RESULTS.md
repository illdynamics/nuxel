# PWNAGE-USBNET — Test Results

**Date:** 2026-11-14 · **Host:** macOS 15.7.9 (24G830, Darwin 24.6.0 arm64,
Apple Silicon) · **Target:** S10+ `beyond2lte`, pinned 4.14.253 source
`f7194c1d15ed`.

> `NOT TESTED` means the test was not run. No physical result is inferred from
> source review or unit tests.

---

## 1. Device reachability during this run (blocking every physical test)

| Probe | Result |
|---|---|
| `ping 192.168.178.167` | **100 % loss**, ARP `(incomplete) on en0` |
| `ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167` | `connect ... port 22: Operation timed out` |
| `system_profiler SPUSBDataType` / `ioreg -p IOUSB` | **no child USB device on any bus** (no `18d1`, no Samsung) |
| `/dev/cu.usbmodem*` | absent |
| `adb devices` | empty |
| Other LAN hosts `.250`, `.51` port 22 | closed (so the LAN itself is up; the phone is not on it) |

Consequence: **no deploy, no live service test, no NCM soak, no reboot and no
flash was possible.** Every physical row below is `NOT TESTED`; files were
prepared and verified offline.

## 2. Kernel patch / build (automated)

| Test | Result | Evidence |
|---|---|---|
| Pinned commit in `.build/src` | PASS `f7194c1d15ed…` | `git rev-parse HEAD` |
| Patch is a **real, durable artifact** (not just an edited build tree) | PASS | `kernel/s10plus/patches/0011-nuxel-usb-ncm-lifecycle.patch` + `.required` |
| Applies to **pristine** pinned `f_ncm.c` | PASS | scratch `git apply --check` + apply; test `test_patch_applies_to_pinned_pristine_source_or_tree_is_patched` |
| `f_ncm.o` compiles (aarch64 gcc, CI flags) | PASS, no `f_ncm.c` warnings | `evidence/pwnage-usbnet-114000/f_ncm-object-build.log` |
| Marker in read-only data | PASS `R nuxel_ncm_lifecycle_marker` | `evidence/.../f_ncm-object-symbols.txt` |
| Invariants pinned by tests (refcount, drain-before-free, single deregister, lock order, `ERR_PTR`, module exit) | PASS | `test_usbnet_lifecycle_gate.py` |
| Full combined `Image.gz` rebuilt this run from this patch | **NOT COMPLETED** — shared tree mid-series for NFC (`0007` required conflict); see manifest §5 |
| Physical NCM create/bind/unbind/remove ×10, pstore clean | **NOT TESTED** |

## 3. Automated userspace tests

Executed: `python3 -m pytest -q tests/pwnage_usbnet
tests/a80/test_usb_net_provider.py tools/beta/live/tests/test_tri_link.py
tests/a72/test_location_provider.py` → **116 passed** (rc=0),
`evidence/pwnage-usbnet-114000/pytest-114000.txt`.

| Suite | Tests | Result |
|---|---|---|
| `tests/pwnage_usbnet` (lifecycle gate, tether provider, host helper, single-owner adapter, tri-link truth) | 39 | PASS |
| `tests/a80/test_usb_net_provider.py` | 6 | PASS |
| `tools/beta/live/tests/test_tri_link.py` | 51 | PASS |
| `tests/a72/test_location_provider.py` | 20 | PASS |

### 3.1 Real-transition simulation (no phone)

`tests/pwnage_usbnet/support/sim_usb_mode.sh` builds a fake configfs gadget,
UDC, netdev, VBUS/Type-C and fix marker, then drives the **real**
`services/nuxel-s10/bin/nuxel-usb-mode.sh` through every transition.
Result: **31 checks, 0 failures** (`evidence/.../usb-mode-simulation.txt`),
including:

* charging idempotent, ACM preserved;
* NCM refused without the fix marker (ACM restored, no NCM dir created);
* USB network on: ACM+NCM links, kernel-named netdev, phone `.1/24` added;
* **10 × off/on cycles** with no leaked function and ACM always present;
* selection + persisted mode file correct;
* tethering composition distinct from plain USB network;
* interrupted transaction → boot recovery to ACM-only;
* subnet overlap refusal (real prefix math) with the gadget untouched;
* physical-detach model (VBUS off while UDC stale `configured`) clears "linked";
* two concurrent transitions serialise; no partial state files;
* malformed journal tolerated; **no `ifname` write**.

Known unrelated failures in the shared tree: `tools/beta/live/tests/test_live_deploy_plan.py`
coverage tests fail because the repository-wide deploy manifest lags ~200
untracked files from other agents (`configs/nuxel/*`, `pwa/nuxel-apps/*`, ...).
USBNET has its own deploy path; see the manifest §5 item 4.

Static: `bash -n` on manager/monitor/host/deploy/accept; `py_compile` on all changed
Python; `node --check` on `qs.js`, `lockscreen-indicators.js`,
`usb-network-settings.js` — all PASS.

## 4. Host-side (real Mac)

| Check | Result |
|---|---|
| `ioreg -a` (no `-l`) carries no `idVendor`/`BSD Name` | confirmed — this was why the old helper found nothing |
| `ioreg -a -l` shape: BSD interface is a **child** of the driver; `IONetworkStack` is elsewhere | confirmed on this Mac |
| Discovery with native IORegistry plist, no device | `NO_USB_NETWORK_INTERFACE`, empty interface (rc=3) — no unrelated port selected |
| Synthetic plist: `AppleUSBDeviceNCM` → `AppleUSBDeviceNCMData` → `IOEthernetInterface{en7}` + decoy en9 | selects **en7 only**; wrong PID selects nothing |
| `--interface en4` (not under the device) | refused, and **not** replaced by auto-discovery |
| Default probe target | phone `10.15.19.1` (host is `.2`), derived from `--address` prefix unless explicitly overridden |
| `--tether-test` without a link/address | `TETHER_NOT_CONFIGURED` / `NO_USB_NETWORK_INTERFACE` |
| `--apply` idempotent when address present | does **not** claim ownership (cannot remove what it did not add) |
| `--tether-test` route policy | adds one `/32` host route via the phone and deletes it; never touches the default route |

No physical USB interface existed, so `--apply`, ping, SSH and
`--tether-test` end-to-end are `NOT TESTED` (they need the device).

## 5. Physical tests — NOT TESTED (no device)

| Test | Status |
|---|---|
| ACM serial in each composition | NOT TESTED |
| NCM create → enumerate → unbind → remove ×10 / ×50, pstore clean | NOT TESTED |
| Mac sees the exact Nuxel USB interface | NOT TESTED |
| Only that interface configured; default route/Wi-Fi/DNS/VPN/ZeroTier unchanged | NOT TESTED |
| `ping 10.15.19.1`, SSH with pinned key, hash-verified transfer | NOT TESTED |
| Physical unplug/replug state clear + restore | NOT TESTED |
| USB tether end-to-end from the Mac (`--tether-test`) + host evidence report | NOT TESTED |
| Wi-Fi hotspot capability probe and second-device join | NOT TESTED (AP support unprobed — the tile shows `n/a` until proven) |
| Bridge deploy + service restart on the phone | NOT TESTED |
| Reboot verification (Nuxel vs TWRP) | NOT TESTED |

## 6. Honest verdicts

| Layer | Verdict |
|---|---|
| Kernel NCM lifecycle fix | **PASS (source + object)**; physical soak NOT TESTED |
| Single gadget owner (one script, journal, flock, rollback, boot recovery) | **PASS (simulation)** |
| Bridge tether provider | **PASS (unit)**; end-to-end NOT TESTED |
| Host helper discovery | **PASS (real Mac + fixtures)** |
| USB local data plane / USB SSH / USB tethering | **NEEDS_VALIDATION** |
| Wi-Fi hotspot | **UNSUPPORTED until probed on the device** (never painted ON) |
