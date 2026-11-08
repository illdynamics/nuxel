# REPORT-USBNET — Nuxel USB network / USB SSH Console

**Mission:** PWNAGE-92000  
**Report date:** 2026-11-08  
**Repository:** `/Users/wicked/x/nuxel`  
**Owner host used for this audit:** macOS 15.7.9 (24G830), Apple Silicon (`arm64`)  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Live kernel:** `4.14.253-gf7194c1d15ed-dirty` (#5 SMP PREEMPT, 2026-11-01)  
**UDC:** `10c00000.dwc3`

## 1. Executive verdict

**PARTIAL / BLOCKED for the USB data plane.**

- **Direct LAN remote desktop is WORKING and physically verified:** XRDP on TCP
  13389 with TLS, and VNC on TCP 15900 with PAM + VeNCrypt TLS/RSA-AES. Both
  were started only by explicit helper action, reached directly over WLAN, and
  closed on `stop-all`.
- **USB SSH Console is NOT WORKING and is NOT claimed READY.** NCM is blocked by
  the recorded 4.14.253 teardown panic. RNDIS is compiled and its vendor
  teardown path does **not** contain the NCM `misc_deregister` call, but it has
  not been physically tested or validated on the owner's macOS host. No USB
  configfs mutation was performed during this mission.
- **CDC-ACM serial remains present** (`acm.usb0`, UDC bound) and **WLAN SSH
  remains working** with the pinned host key.

## 2. Exact target and test environment

| Item | Value |
|---|---|
| Device | Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820 |
| Live OS | Fedora Linux 43 aarch64 |
| Kernel | `4.14.253-gf7194c1d15ed-dirty` (`#5 SMP PREEMPT Sun Nov 1 13:38:15 CET 2026`) |
| Boot ID at audit | `7c9fdaef-9a9d-4968-a76e-c541dbfcea0b` (recorded in evidence bundle) |
| UDC | `10c00000.dwc3` |
| Live gadget | `usb_gadget/nuxel`, function `acm.usb0` only |
| Host | macOS 15.7.9 build 24G830, arm64 |
| Host USB interface for Nuxel | **none exposed** |
| Recovery | WLAN SSH + CDC-ACM serial, both verified |

## 3. Current architecture

```text
macOS host
   │
   ├── USB-C cable ──► S10+ DWC3 gadget
   │                      ├── acm.usb0  (CDC-ACM serial recovery, ALWAYS present)
   │                      ├── ncm.usb0  (not present; unsafe on this kernel)
   │                      └── rndis?    (not present; compiled but unvalidated)
   │
   └── Wi-Fi ──► wlan0 192.168.178.167 ──► sshd:22 (pinned-key, working)

phone-side status: system.tri-link (read-only)
host-side CLI:    tools/beta/live/nuxel-live-ssh.py --transport {auto,wlan,usb,serial}
```

Phone-side status is intentionally separate from the GUI `system.remote-desktop`
provider. USB remote desktop is **not** offered by the GUI provider.

## 4. Kernel capability matrix (live `/proc/config.gz`)

| Mode | Compile status | Runtime function | Safety verdict |
|---|---|---|---|
| ACM | `CONFIG_USB_F_ACM=y`, `CONFIG_USB_CONFIGFS_ACM=y` | `acm.usb0` present | **WORKING recovery path** |
| NCM | `CONFIG_USB_F_NCM=y`, `CONFIG_USB_CONFIGFS_NCM=y` | absent | **BLOCKED_KNOWN_PANIC** on 4.14.253 |
| RNDIS | `CONFIG_USB_F_RNDIS=y`, `CONFIG_USB_CONFIGFS_RNDIS=y` | absent | **NEEDS_VALIDATION** |
| ECM | `# CONFIG_USB_CONFIGFS_ECM is not set` | absent | **BLOCKED_KERNEL** |
| ECM-subset | `# CONFIG_USB_CONFIGFS_ECM_SUBSET is not set` | absent | **BLOCKED_KERNEL** |
| EEM | `# CONFIG_USB_CONFIGFS_EEM is not set` | absent | **BLOCKED_KERNEL** |
| configfs / DWC3 | `CONFIG_USB_CONFIGFS=y`, `CONFIG_USB_DWC3=y`, `CONFIG_USB_DWC3_DUAL_ROLE=y` | bound | available |

Compile-time support is **not** runtime or host compatibility proof.

## 5. NCM panic evidence — do not repeat

Saved evidence: `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`.
The pstore dump (`pstore-dmesg-ramoops-0.txt`) shows `Panic#2 Part1`, faulting
task `rmdir:77554`, and this teardown stack:

```text
misc_deregister+0x48/0xc8
ncm_free_inst+0x38/0x60
usb_put_function_instance+0x20/0x40
ncm_attr_release+0xc/0x20
config_item_put.part.0+0x70/0xa0
configfs_rmdir+0x20c/0x338
...
```

The vendor source shows why this is NCM-specific:

- `kernel/s10plus/.build/src/drivers/usb/gadget/function/f_ncm.c:1764`
  `ncm_free_inst()` calls `ncm_function_cleanup()` under
  `CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE`.
- `f_ncm.c:1722` `ncm_function_cleanup()` calls
  `misc_deregister(&mirrorlink_device)`.
- `f_rndis.c:950` `rndis_free_inst()` has **no** `misc_deregister`; it calls
  `gether_cleanup()` or `free_netdev()` and then frees the options.

This mission did **not** run `nuxel-usb-net.py --apply`, did **not** create or
remove `functions/ncm.*`, did **not** rebind the UDC, and did **not** use an
unsafe override. The production `--allow-unsafe-kernel` switch was removed.

## 6. RNDIS analysis

**Verdict: source path looks independent of the NCM panic, but remains
NEEDS_VALIDATION.** RNDIS is not marked safe or READY.

- Compile options: `CONFIG_USB_F_RNDIS=y`, `CONFIG_USB_CONFIGFS_RNDIS=y`.
- Allocator: `rndis_alloc_inst()` → `gether_setup_name_default("rndis")`
  (`f_rndis.c:966-1008`).
- Teardown: `rndis_free_inst()` (`f_rndis.c:950-964`) uses
  `gether_cleanup(netdev_priv(opts->net))` when bound, otherwise
  `free_netdev(opts->net)`, then frees the RNDIS options.
- It does **not** call the Samsung NCM `ncm_function_cleanup()` →
  `misc_deregister()` path that produced the panic.

What is still unproven:

1. The exact vendor `gether_cleanup()` / netdev / DWC3 teardown sequence has not
   been exercised on this 4.14.253 build.
2. The owner's macOS 15.7.9 host exposes **no USB network interface** for the
   Nuxel VID/PID (`18d1:4ee7`) while only ACM is present, as expected. macOS does
   not guarantee a built-in RNDIS driver.
3. RNDIS on macOS would require a reviewed userspace driver such as ReRNDIS or
   TetherKit. No driver was installed and no SIP/kernel-security change was
   made. Current releases, licences, Apple Silicon support and uninstall paths
   must be checked before that becomes an owner-approved route.
4. A physical RNDIS teardown test needs a separate recovery plan and should not
   be the first experiment on the owner's only phone.

## 7. ECM / ECM-subset / EEM

ECM, ECM-subset and EEM are **not compiled**. They cannot be enabled by a JSON
flag; they require an exact-kernel config rebuild (and, for ECM, host driver
verification). They are not a practical remediation for this mission.

## 8. Host compatibility

### macOS 15.7.9 (owner Mac, Apple Silicon) — detected, blocked

`scripts/s10plus-debug-pack/nuxel-usb-net-host.sh --status --json` reports:

```json
{"status":"NO_USB_NETWORK_INTERFACE",
 "detail":"No macOS USB network interface for VID 18d1 PID 4ee7. NCM may need native support; RNDIS needs a reviewed userspace driver ...",
 "os":"Darwin","interface":"","default_route":"gateway: 192.168.178.1 / interface: en0"}
```

The adapter:
- discovers by VID/PID (`18d1:4ee7`) and hardware port;
- **never installs a driver**;
- **never changes SIP**, Wi-Fi, DNS, VPN or the default route;
- refuses `--apply` when no interface exists.

### Fedora 43 / Linux

The Linux adapter discovers the interface through sysfs `device/idVendor` and
`idProduct`, configures only the USB interface address (`10.15.19.1/24`), and
never changes the default route. It was not exercised against a live USB
network function because no safe mode is currently enabled.

## 9. CDC-ACM preservation

Before and after this mission's read-only audit:

```text
/sys/kernel/config/usb_gadget/nuxel/UDC = 10c00000.dwc3
/sys/kernel/config/usb_gadget/nuxel/functions/ = acm.usb0
configs/*/acm.usb0 -> ../../../../usb_gadget/nuxel/functions/acm.usb0
```

No network function existed, no function was created, and no UDC transition was
performed. Serial recovery was not touched.

## 10. IP and routing

Live phone routing during the audit:

```text
default via 192.168.178.1 dev wlan0 proto dhcp src 192.168.178.167 metric 600
192.168.178.0/24 dev wlan0 proto kernel scope link src 192.168.178.167 metric 600
```

- No `usb0`, `ncm0` or `rndis0` address exists.
- No default-route change was made on the phone or host.
- The reserved USB subnet remains `10.15.19.0/24` (device `.82`, host `.1`) in
  the helper configuration, subject to collision refusal.

## 11. Tri-Link CLI results

| Command | Result |
|---|---|
| `--transport wlan --host 192.168.178.167 --status` | **AVAILABLE**, pinned host key verified, public-key auth accepted |
| `--transport wlan --exec 'uname -a; id -un; ...'` | **PASS**, returned the live kernel and `nuxel`, exit 0 |
| `--transport usb --usb-host 10.15.19.82 --status` | **UNREACHABLE**, TCP connect timed out; did not fall back to WLAN/serial |
| USB file transfer / deploy | **NOT TESTED** (no USB data plane) |

Evidence: `docs/beta-finalization/live/evidence/pwnage-92000/tri-link-cli.txt`.

## 12. UI / Bridge truth

- `system.tri-link` now exposes per-mode state:
  - `ncm`: `BLOCKED_KNOWN_PANIC`;
  - `rndis`: `NEEDS_VALIDATION`;
  - `ecm`: `BLOCKED_KERNEL`;
  - `acm_preserved: true`;
  - `mutated: false`.
- Top-level USB status on this kernel is `NEEDS_VALIDATION` (not READY, not a
  blanket “NCM panic means every mode is impossible”).
- If a future interface and sshd appear without a host key-authenticated probe,
  the phone-side provider returns at most `LINK_UP_UNVERIFIED`.
- The USB SSH Console app shows mode rows, ACM preservation, the blocker and a
  link to this report. It has no Apply button for NCM.

## 13. Tests run

| Suite | Result |
|---|---|
| `tests/a80/test_remote_desktop.py`, `test_tri_link_status.py`, `test_tri_link_api.py`, `test_tri_link_console.py` | **42 passed** |
| `tools/beta/live/tests/test_tri_link.py` | **51 passed** |
| `tests/pwnage45000/test_pwnage45000.py` | **ALL PASS** |
| `tests/pwnage54000/test_pwnage54000.py` | **19 passed** |
| Workflow gates (`tests/pwnage30000`, `services/nuxel-orientation/tests`, PWNAGE-45000/49000/52000/62000 scripts) | **ALL PASS** |
| Broader `tests/` sweep excluding pre-existing script-style collectors | **622 passed, 17 pre-existing unrelated failures, 2 skipped** |
| VNC RFB probe | `RFB 003.008`, security types `[129, 5]`, type `1` not offered |
| RDP probe | X.224 negotiation + **TLSv1.3**, cipher `TLS_AES_256_GCM_SHA384` |
| USB physical data plane | **NOT RUN** |

## 14. Current blockers

1. **NCM teardown panic on 4.14.253** — hard block; never retry on this phone.
2. **RNDIS not physically validated** — vendor source path looks independent from
   the NCM `misc_deregister` bug, but no teardown test or macOS host driver.
3. **No macOS RNDIS interface/driver** — ReRNDIS/TetherKit not installed, by
   design.
4. **ECM absent from the kernel** — requires a kernel rebuild.

## 15. Recommended route to fully working USB networking

1. Obtain or build the exact vendor kernel source and add a regression test for
   the NCM `misc_deregister` lifecycle. Fix `ncm_function_cleanup()` so
   `misc_deregister()` is idempotent/safe; validate on a separate test phone or
   lab board first.
2. In parallel, source-review and then lab-test RNDIS create/bind/unbind/rmdir
   on a non-primary device. Confirm ACM survives and the host re-enumerates.
3. On macOS, evaluate a pinned ReRNDIS/TetherKit release for Apple Silicon with
   a documented uninstall path. Do not install it silently and do not require
   SIP changes.
4. Only after a mode passes source review, host preflight and physical recovery:
   enable it explicitly (`--mode rndis` or the fixed NCM-safe path), add the USB
   route and perform the full acceptance matrix in the mission spec.
5. Keep the USB SSH CLI pinned-key and explicit. `auto` may select USB only when
   the adapter proves a live interface, route, SSH listener and authenticated
   command execution.

## 16. Rollback / recovery

- **Serial recovery:** CDC-ACM `/dev/ttyGS0`, host `/dev/ttyACM*`; preserved.
- **WLAN SSH:** `nuxel@192.168.178.167:22`, pinned key; verified before and
  after the audit.
- **Current gadget:** `acm.usb0` only, UDC `10c00000.dwc3`.
- **Safe rollback command (only if a transaction exists):**
  `sudo python3 tools/beta/live/nuxel-usb-net.py --rollback`
- No transaction exists today; running rollback would be refused without a
  usable backup.

## 17. Residual gaps / honesty statement

- No USB Ethernet link was established.
- RNDIS is not proven safe merely because it compiles or because its source does
  not contain the NCM `misc_deregister` call.
- No macOS userspace driver was installed or evaluated physically.
- No file transfer, deploy or USB remote-desktop transport was tested.
- The serial console and WLAN SSH are the only verified recovery/transport paths.
