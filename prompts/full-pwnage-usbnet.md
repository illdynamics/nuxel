# FULL PWNAGE — Nuxel USB Networking, USB Tethering, Wi-Fi Hotspot & Quick Settings

the full pwnage pack for fixing usb networking and tethering is located in ./usbnet

**Project:** Nuxel  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**OS:** Nuxel / Fedora Linux ARM64  
**Kernel baseline:** Samsung-derived Linux 4.14.253; exact source commit is pinned by `kernel/s10plus/build-kernel.sh`  
**Primary development host:** Apple Silicon Mac, macOS 15.7.9  
**Secondary validation host:** Fedora/Linux where available  
**Mission:** Finish the USB Ethernet data plane, reliable USB SSH/deploy transport, optional USB Internet tethering, Wi-Fi hotspot controls, and real Quick Settings/Settings integration.  
**Reflash strategy:** Prepare this as part of the single controlled A/B reflash batch in `REFLASH-PLAN.md`. Do not perform an independent USBNET flash.

---

# 0. MISSION AND NON-NEGOTIABLE COMPLETION RULE

This is an implementation-and-verification mission, not a design-only report. Work through the existing Nuxel implementation, fix the actual blockers, integrate the feature with the existing architecture, test it, and leave it ready for the next single combined reflash.

The target outcome is a working USB network interface from the S10+ to the owner's Mac, with authenticated Nuxel SSH/deploy access, plus real internet-sharing controls and Quick Settings UI. Where the handset's Wi-Fi AP or upstream-routing capabilities do not support a requested mode, prove the limitation and report it honestly rather than drawing a fake ON switch.

**Do not flash, reboot, or change any phone partition during this mission.** NFC and other kernel-gated work is being prepared in parallel for one controlled batch. Your job is to make the source, tests, configuration, deployment payload and reflash manifest complete and coherent. Any physical runtime testing must be done only when the operator explicitly makes the current test build available over the existing supported method and approves the test. No standalone USBNET reflash.

## 0.1 Definition of DONE

The mission is complete only when all applicable items are verified:

- [ ] Existing USB CDC-ACM recovery console remains present and works in every USB composition.
- [ ] A real USB Ethernet gadget mode is selected on evidence, implemented and source-reviewed.
- [ ] The Samsung 4.14.253 NCM teardown panic is fixed in the exact pinned kernel source, or a separately validated alternative mode is selected with a clear Mac compatibility answer.
- [ ] Gadget create/bind/configure/unbind/remove/recreate cycles pass without panic, hang, watchdog reset, leaked function, stale netdev or lost ACM.
- [ ] The Mac exposes a network interface belonging to this exact USB device, not merely an arbitrary Ethernet interface.
- [ ] Host and phone exchange IP packets over the USB link.
- [ ] USB SSH succeeds using the existing pinned Nuxel host key and public-key authentication.
- [ ] USB transport can safely carry a hash-verified test file or deploy operation and can recover to WLAN/ACM.
- [ ] USB link detach/re-attach is detected correctly; no stale “connected” state or kernel debugfs hazard.
- [ ] Optional USB Internet tethering works end to end when a supported upstream is available, with explicit opt-in and strict firewall cleanup.
- [ ] Wi-Fi hotspot capability is probed from the actual Wi-Fi driver/regulatory configuration; if supported, AP mode and client internet access are physically tested. If unsupported, the UI reports UNSUPPORTED with a useful reason.
- [ ] Quick Settings and Settings controls call real providers and show read-back state; unsupported/error/transition states are not painted ON.
- [ ] Network routes, DNS, VPN/killswitch state and normal Wi-Fi connectivity are preserved when USB networking alone is enabled or disabled.
- [ ] Automated tests, static checks and hardware tests pass; logs and artifacts are saved.
- [ ] `REFLASH-PLAN.md` is updated with exact USBNET changes, required partitions and test status for the combined batch.

A source patch, successful kernel compile, configfs directory, USB descriptor, host interface, IP ping, SSH connection, Internet access and UI state are distinct milestones. Report each separately.

## 0.2 Required state vocabulary

Use these statuses consistently:

- `PASS`: verified with the relevant test and evidence.
- `PARTIAL`: some layer works but acceptance is incomplete.
- `FAIL`: attempted and failed.
- `BLOCKED_KNOWN_PANIC`: the exact old NCM failure remains present.
- `NEEDS_VALIDATION`: code/config exists but physical proof is missing.
- `UNSUPPORTED`: hardware/driver/host capability was probed and is not available.
- `NOT TESTED`: the test was not run.
- `ERROR`: operation failed at runtime; include cause.

Never report a mode as safe merely because it compiles or has no obvious source-level match to the NCM panic.

---

# 1. START WITH THE REAL REPOSITORY AND PRESERVE PARALLEL WORK

The supplied reference material is a snapshot from the uploaded Nuxel ZIP. The active repository and current working tree are authoritative at execution time. Re-run every relevant inspection; do not assume this pack exactly matches the current branch.

Before changing anything:

1. Run `git status --short --branch`, `git log -1 --oneline`, and identify the current branch/worktree.
2. Record all modified, staged, untracked and ignored generated files relevant to kernel/NFC/USBNET.
3. Read `REFLASH-PLAN.md`, `REPORT-USBNET.md`, kernel build docs and the reference files in this pack.
4. Locate and read the exact USBNET-related files in the live checkout.
5. Identify the NFC agent's current work and avoid its files/patches.
6. Do not run `git reset`, broad `git clean`, `git checkout -- .`, force checkout, stash, or any operation that can discard concurrent work.
7. Prefer a dedicated worktree/branch for USBNET if that is compatible with the build/deployment workflow. If working in the shared tree, limit edits to owned files and preserve all other diffs.
8. Never rewrite the existing NFC patch or its configuration simply to make the USB patch apply.

The kernel source checkout under `.build` may be absent in the uploaded archive. Fetch the exact pinned source using the repo's build script and inspect it; do not assume the reference report's line numbers still match without checking.

## 1.1 Existing repository facts to verify before implementation

The uploaded snapshot records:

- Device: Galaxy S10+ SM-G975F / `beyond2lte`, Exynos 9820.
- Live kernel in the report: `4.14.253-gf7194c1d15ed-dirty`.
- UDC: `10c00000.dwc3`.
- Current gadget composition: `acm.usb0` only.
- USB serial recovery: working.
- WLAN SSH: working with a pinned host key.
- No USB Ethernet data interface was physically exposed in the previous Mac test, because only ACM was present.
- Proposed USB subnet in existing helper: `10.15.19.0/24`, phone `10.15.19.82/24`, host `10.15.19.1/24`; retain only if route-collision checks prove it is safe.
- USB gadget VID:PID seen in the report: `18d1:4ee7`; verify the live descriptors before depending on it.

Do not turn these snapshot observations into hard-coded assumptions without fresh verification.

---

# 2. UNDERSTAND THE FAILURE HISTORY BEFORE TOUCHING CONFIGFS

Read all of these:

- `REPORT-USBNET.md`
- `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/README.md`
- `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/pstore-dmesg-ramoops-0.txt`
- `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/current-gadget.txt`
- `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/kernel-config-usb.txt`
- `docs/a73/USB-PHYSICAL-STATE-MATRIX.md`
- `docs/a74/USB-DETACH-SEQUENCE.md`
- `docs/a77-usb-detach/ROOT-CAUSE.md`

## 2.1 Known NCM crash

The previous real NCM test on the Samsung-derived 4.14.253 kernel triggered a panic during configfs function-instance destruction. The recorded pstore stack contains:

```text
misc_deregister
ncm_free_inst
usb_put_function_instance
ncm_attr_release
config_item_put
configfs_rmdir
```

The report points to the Samsung-specific `CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE` path in `drivers/usb/gadget/function/f_ncm.c`:

- `ncm_free_inst()` calls `ncm_function_cleanup()`.
- `ncm_function_cleanup()` calls `misc_deregister(&mirrorlink_device)`.

The recorded failure occurred while removing the NCM configfs function. The exact kernel source must be re-fetched/inspected and the call graph reconstructed; do not blindly trust prior line numbers or assume the first suspected lifecycle flaw is the full root cause.

The old experiment also attempted to write NCM `ifname`; that attribute was read-only and returned permission denied. **Never write `ifname`.** Let the kernel assign its network interface name unless the exact source and configfs ABI on the target prove another supported mechanism.

## 2.2 Required NCM source audit and fix

Inspect at least:

- `f_ncm.c`: allocation, function-instance free, function bind/unbind, cleanup, misc device registration and error paths.
- `f_rndis.c`: allocator, bind/unbind/free, vendor-specific wrappers.
- `u_ether.c` and related netdev lifetime paths.
- configfs function-instance registration and release ordering.
- Samsung composite/vendor hooks under `CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE`.
- workqueues, delayed work, timers, references, locks and all teardown callers.

Determine exactly why `misc_deregister()` is unsafe in this target lifecycle. Possible categories to investigate include duplicate/unbalanced deregistration, a static/global `miscdevice` shared by multiple function instances, failed or partial registration, lifetime ordering, racing work/close callbacks, or a vendor function cleanup called more than once. These are hypotheses only.

The fix must be based on the actual ownership/lifetime model. Depending on the proven cause, the solution may require a registered-state flag, serialized/refcounted singleton ownership, correct registration scope, exactly-once cleanup, proper cancellation/draining of asynchronous work, or a different minimal correction. Do not mechanically add a boolean without proving it handles multiple instances, partial initialization, bind failures and concurrent teardown.

Required source invariants:

- Every successful registration has exactly one matching deregistration.
- A failed registration is never deregistered as if it succeeded.
- A failed partial setup unwinds only resources actually acquired.
- No callback or work item can access freed function-instance state.
- Cleanup can be invoked by the real kernel paths without double-free/double-deregister.
- Concurrent create/remove is serialized or safely reference-counted.
- A second valid instance cannot accidentally deregister a shared resource still owned by the first.
- Error codes propagate and the configfs operation fails cleanly rather than leaving a half-bound gadget.
- Existing Android/Samsung composite functionality unrelated to Nuxel is not regressed.

Create a focused kernel patch with a unique name after inspecting the existing patch queue, for example `0011-nuxel-usbnet-ncm-lifecycle.patch`; this is only a suggested filename. Add a `.required` sidecar only after the patch is verified and is intended to be mandatory. Update `kernel/s10plus/patches/README.md` with purpose, evidence, scope and tests.

Add a regression test plan or small test harness where practical. The core regression is physical create → bind → enumerate → unbind → remove → recreate, repeated many times with ACM preserved and no panic/watchdog reset.

## 2.3 Do not use RNDIS as an unproven shortcut

The existing report notes that RNDIS `rndis_free_inst()` does not take the NCM `misc_deregister()` path and instead calls `gether_cleanup()` or `free_netdev()`. This does **not** prove RNDIS is safe. Audit its actual 4.14.253 path, netdev cleanup, DWC3 behavior and host-driver compatibility independently. It may be retained as a secondary mode for Linux/Windows after validation, but it is not the primary solution for the owner's Mac.

---

# 3. CHOOSE A MAC-COMPATIBLE USB ETHERNET FUNCTION

The primary acceptance host is macOS 15.7.9 on Apple Silicon. Use CDC-NCM as the preferred first option because modern macOS includes a CDC-NCM network driver. Verify this on the actual Mac with the exact host OS rather than relying only on documentation.

RNDIS is not a native equivalent on macOS. Do not quietly require a third-party RNDIS driver, an unsigned kernel extension, disabling SIP, reducing system security, or installing a networking driver. Such a route requires separate user approval, current compatibility/licence review, explicit install/uninstall steps and an alternative recovery path. It is not required for the main NCM target.

ECM can be evaluated if needed, but do not enable every gadget protocol merely because its Kconfig symbol exists. Select the smallest stable mode set for the required host matrix.

## 3.1 Mode selection matrix

Produce a table for each mode:

- ACM: mandatory recovery serial, always preserved.
- NCM: preferred Mac USB Ethernet; currently known panic until fixed and physically revalidated.
- RNDIS: optional Linux/Windows compatibility; source review plus actual physical test required.
- ECM: optional only if it materially improves compatibility; config and host proof required.
- EEM / ECM-subset: not required unless a measured host/platform requirement is demonstrated.

For every mode report:

- Kernel symbol state after `olddefconfig`.
- Configfs function directory availability.
- Function allocation/bind/unbind/remove result.
- Network interface name observed from kernel (not guessed).
- Host driver/interface result on Mac/Linux.
- IP connectivity.
- SSH result.
- Detach/reconnect result.
- ACM preservation.
- Final state and evidence.

Never claim “USB support” as a single binary feature.

---

# 4. KERNEL BUILD AND CONFIGURATION — MODIFY THE ACTUAL BUILD INPUT

The pinned kernel source and commit are defined by `kernel/s10plus/build-kernel.sh`. Use the script's pinned source/commit and normal patch flow. Do not switch to a random upstream kernel or newer Samsung tree mid-batch.

Important repo-specific build facts:

- The actual active capability fragment is `kernel/s10plus/configs/nuxel-drm-kbase.fragment` (or the fragment explicitly selected by `NUXEL_KERNEL_FRAGMENT`).
- `kernel/s10plus/defconfig` is informational, not the complete active configuration.
- `live-required.config` is a reference snapshot and is not the default build fragment.
- Do not make only an edit to the informational file and assume the build consumes it.
- The build wrapper applies `kernel/s10plus/patches/*.patch` in sorted order and records the result in `.build/out/patch-application.log`.
- Inspect the script and active `.config` to prove every option was accepted by the pinned Kconfig.

## 4.1 USB gadget config

Inspect the exact Kconfig symbols and dependencies for the target tree. The previous live config records:

- `CONFIG_USB_CONFIGFS=y`
- `CONFIG_USB_F_ACM=y`
- `CONFIG_USB_CONFIGFS_ACM=y`
- `CONFIG_USB_F_NCM=y`
- `CONFIG_USB_CONFIGFS_NCM=y`
- `CONFIG_USB_F_RNDIS=y`
- `CONFIG_USB_CONFIGFS_RNDIS=y`
- ECM / ECM-subset / EEM unset.
- DWC3 dual-role support enabled.

Do not blindly copy this into a fragment: verify current `.config`, dependencies and Kconfig semantics. Preserve ACM and DWC3 device/gadget support. Investigate the report's apparent mismatch between `CONFIG_USB_DWC3_DUAL_ROLE` and the snapshot's disabled `CONFIG_USB_DWC3_GADGET`; do not force a symbol merely because its name looks relevant.

After changing the active fragment:

1. Run the normal build script / `olddefconfig` path.
2. Inspect the resulting `.config`.
3. Save the requested config and final resolved config.
4. Verify the symbols are built in or available as modules as intended.
5. Verify module/firmware install paths if any.
6. Verify no unrelated display, fbdev, Mali, NFC or other current capabilities were dropped.

## 4.2 Other kernel networking features

For Internet tethering, inspect the target `.config` and source for the actual requirements and availability of:

- IPv4 forwarding.
- Netfilter/nftables.
- Connection tracking.
- NAT/masquerade.
- DHCP-related packet handling.
- IPv6 forwarding/NDP if IPv6 tethering is implemented.
- Bridge functionality only if genuinely needed.

Do not add a broad bridge or unrelated routing feature if a simple L3 interface plus NAT is sufficient. Do not add kernel options without tests demonstrating the need.

---

# 5. ONE USB GADGET OWNER — EXTEND THE EXISTING STATE MACHINE

Existing Nuxel files include:

- `services/nuxel-bridge/src/usb_mode.py`
- `services/nuxel-s10/bin/nuxel-usb-mode.sh`
- `services/nuxel-s10/systemd/nuxel-usb-mode-monitor.service`
- `services/nuxel-s10/systemd/nuxel-usb-mode-restore.service`
- `/api/v1/system/usb-mode`
- `/api/v1/usb-mode/set-mode`

The current helper owns Charging ↔ File Transfer transitions and keeps the ACM serial function. It uses configfs and UDC transitions. USB networking must be added to this existing ownership model, or via one explicit coordinator that owns the complete composite gadget.

**Do not create a second independent script/service that also mutates the same gadget configfs tree.** Two independent owners will race, remove each other's function links, or leave a stale UDC state.

## 5.1 Required exclusive mode model

Extend the existing state machine to cover clear mutually-exclusive compositions, for example:

- `charging` — ACM serial only, no network or MTP function.
- `file_transfer` — ACM + MTP; existing safe MTP export behaviour preserved.
- `usb_network` — ACM + NCM (or selected validated network function); local USB Ethernet data plane.
- `usb_tethering` — same validated USB network function plus explicit Internet sharing configuration.

If the product can safely support MTP + NCM simultaneously, treat it as a separately tested composition, not an assumption. Do not expose all functions at once without validation.

ACM must remain in every mode as the recovery serial channel. Verify actual descriptor/interface composition after every transition.

## 5.2 Transition transaction requirements

- One mutex/lock serializes every gadget state transition, including systemd restore, disconnect monitor, API actions, and rollback.
- Persist requested and actual states separately.
- Use atomic state-file writes.
- Record operation ID, requested mode, previous mode, start time, UDC, exact functions and links, active interface, result and error.
- Snapshot the exact previous configfs state, not only basenames.
- Preserve unrelated gadget descriptors/functions.
- Validate all preconditions before unbinding the UDC.
- Stop services tied to the departing mode before removing its function.
- Detach only functions owned by this manager.
- Remove symlinks before removing the function instance.
- Do not delete the configfs gadget or ACM function.
- Rebind the verified UDC and wait for real enumeration.
- Verify netdev creation, network config and host confirmation before marking active.
- Roll back to a known-good ACM-safe composition on any failure.
- Use a bounded rollback timer and a boot-time recovery check for interrupted transactions.
- On crash/reboot with a transaction marked in-progress, restore the safe `charging`/ACM-only composition. Never automatically recreate a previously unsafe NCM composition at boot.
- Ensure rollback is idempotent and cannot double-remove the same function.

## 5.3 Detach handling

Use the existing A77 semantics:

- UDC state alone can remain stale after cable removal.
- Type-C `data_role` can also remain stale after cable removal on this board.
- UDC `current_speed` returning `UNKNOWN` is a useful measured detach signal.
- Wired VBUS power-supply `online=0` is another measured detach signal.
- Missing sysfs signals should be neutral; do not invent a disconnect from absent attributes.
- Never use DWC3 `link_state` debugfs reads. A previous read after FSYS0 power gating synchronously faulted and caused a watchdog reboot.
- Do not treat wireless charging as wired VBUS.

Reuse the tested `system_indicators.py` / A77 model or factor a shared, tested helper. Do not fork a second, subtly different unplug-detection algorithm into USB networking.

On physical detach, tear down only transient host-side IP state/lease and update indicators; do not remove or mutate the gadget function from a signal path that can race a configfs transition. Let the single manager complete a serialized safe transition.

---

# 6. PHONE-SIDE USB NETWORK DATA PLANE

The existing phone helper `tools/beta/live/nuxel-usb-net.py` is a useful prototype but is currently intentionally restrictive. It recognizes NCM, RNDIS, ECM, ECM-subset and EEM, but only has an NCM apply path and refuses operation on the known-bad `4.14.253`. It currently uses a fixed subnet, a NCM-specific snapshot/rollback and a temporary confirmation timer.

Do not simply remove the block or change `KNOWN_BAD_NCM_KERNELS`. Replace or refactor the helper only after the kernel and physical tests prove a mode safe.

## 6.1 IP plan

The existing intended management link is:

- Phone: `10.15.19.82/24`
- Host: `10.15.19.1/24`
- Subnet: `10.15.19.0/24`

Retain only if collision detection succeeds on both phone and host. Inspect all existing routes, connected networks, VPN routes, ZeroTier routes, Docker/VM bridges and custom IPs. Do not rely on simple string-prefix matching.

Requirements:

- Detect overlaps with actual network masks and routes using a real IP library / OS route output.
- Refuse if subnet is already routed/assigned elsewhere.
- Do not modify wlan0 or its IP.
- Do not change the phone's default route for management-only USB networking.
- Do not change host default route, Wi-Fi, DNS or VPN in management-only mode.
- Do not add a competing default route merely to make `ssh` work.
- Use the actual kernel-created netdev name. `usb0`, `ncm0` and `rndis0` are candidate names only; inspect observed name.
- Set stable locally administered MAC addresses only where the function's writable attributes support it; validate MAC uniqueness and format.
- Never write read-only configfs attributes.

## 6.2 SSH and transfer proof

A host network interface existing is not enough. The phone must:

- assign the correct USB address to the observed gadget interface;
- bring that interface up;
- expose SSH only according to the existing host-key and firewall policy;
- report the link as `LINK_UP_UNVERIFIED` until authenticated SSH succeeds;
- not start arbitrary network services on all interfaces;
- preserve the pinned host key and public-key-only authentication.

The host must:

- positively associate the network interface with the exact Nuxel USB device;
- configure only that interface address;
- probe the phone's address (normally `.82`, not the host's own `.1` address);
- verify the SSH host key and public-key auth;
- run a harmless identity/status command;
- transfer a test artifact and compare SHA256;
- remove only the address/routes it added.

`auto` transport may select USB only after it proves: USB device identity, matching network interface, a usable IP route, SSH listener, expected host-key fingerprint and successful authenticated command. Otherwise it must continue to prefer the known-good WLAN path or report unavailable according to the existing Tri-Link contract. Never silently fall back from an explicitly requested USB transport to WLAN/serial.

## 6.3 Helper defects to address

Audit and repair the existing helper rather than cloning it:

1. `subnet_in_use()` currently uses prefix string heuristics; replace with real route/address overlap logic.
2. Existing `snapshot()` must store exact configfs paths, symlink targets, attributes, UDC binding, existing interface addresses/routes and service state needed for precise rollback.
3. The rollback path must be generalized for the selected mode while preserving ACM and functions not owned by the transaction.
4. Rollback timer alone is insufficient: persist an in-progress transaction and implement safe boot recovery.
5. Handle interrupted configfs setup after every individual operation; do not leave orphan directories/symlinks.
6. Validate return codes for `ip addr`, `ip link`, UDC bind/unbind, service start and interface wait. Do not ignore failed IP configuration.
7. Never write NCM `ifname`.
8. Correct any SSH diagnostic target that probes the host's own address instead of the phone address.
9. Recalculate and validate the network prefix if a configurable host address is supported.
10. Avoid stale helper code that advertises unsupported modes as available.

---

# 7. HOST-SIDE MAC / LINUX NETWORK DISCOVERY

Existing host helper:

`scripts/s10plus-debug-pack/nuxel-usb-net-host.sh`

It has a valuable safety boundary: it does not install drivers and does not change the default route, Wi-Fi, DNS or VPN. Preserve and strengthen that boundary.

## 7.1 Linux discovery

Current discovery assumes `idVendor` and `idProduct` are directly beneath `/sys/class/net/<iface>/device`. That is not universal. Resolve the interface's sysfs parent chain until the matching USB device is found; verify its VID/PID and, where possible, serial/interface number/configuration and driver. Never select an unrelated Ethernet interface because it has a similar name.

## 7.2 macOS discovery — critical bug

The existing helper first verifies VID/PID using `system_profiler SPUSBDataType`, then scans Ethernet-like hardware ports and selects the first interface that looks like USB/NCM/RNDIS/Ethernet. It does not prove that selected interface belongs to that exact USB device.

Fix this. Use a robust association using IORegistry/USB device ancestry, `system_profiler` hierarchy and network interface registry data, or another supported macOS mechanism. The chosen BSD interface must be linked to the exact USB device and the correct network function. If the mapping is ambiguous, refuse to apply and print diagnostics instead of guessing.

Verify on the actual Apple Silicon Mac:

- Nuxel USB device enumeration (VID/PID and configuration descriptors).
- CDC-NCM driver binding.
- The network interface's BSD name and IORegistry parent.
- Interface MAC address.
- Interface state and IPv4 address.
- Phone reachability.
- SSH host-key/authentication.
- Detach and reconnect behaviour.

Use `system_profiler`, `networksetup`, `ifconfig`, `ioreg`, `route` and suitable packet/connection diagnostics. Do not parse localized human prose if a structured output is available.

## 7.3 Host address configuration safety

The default intended host address is `10.15.19.1/24`, but confirm the selected interface has no unrelated address or route before applying.

- Store exactly what this tool changes.
- If address already present, treat it idempotently and do not claim ownership unless proven.
- On remove, delete only the address/routes this tool created.
- Never change the system default route in management-only mode.
- Never reset DNS, Wi-Fi, VPN, ZeroTier, other Ethernet adapters or macOS network services.
- Do not disable SIP, alter system security policy or install unsigned drivers.
- Provide `--status`, `--discover`, `--preflight`, `--apply`, `--remove` and `--diagnose` semantics with a machine-readable JSON contract.
- Distinguish `DEVICE_PRESENT`, `NETWORK_INTERFACE_FOUND`, `LINK_UP`, `IP_CONFIGURED`, `PHONE_REACHABLE`, `SSH_AUTHENTICATED` and `FILE_TRANSFER_VERIFIED`.

The existing `diagnose` logic must probe the phone-side address, not `10.15.19.1` (the host address). Add tests for that regression.

---

# 8. USB INTERNET TETHERING — DISTINCT FROM USB SSH

Do not conflate these separate capabilities:

1. **USB Ethernet / USB SSH:** local host↔phone connectivity only. It does not need Internet sharing.
2. **USB tethering:** the phone shares one of its own upstream networks (Wi-Fi station or a genuinely working cellular data interface) to the connected computer over USB.
3. **Wi-Fi hotspot:** the phone becomes a Wi-Fi access point and shares an upstream network to wireless clients.
4. **Reverse tethering:** the host shares its Internet connection back to the phone. This is a separate feature and is NOT implied by USB tethering; do not implement or label it as such unless explicitly scoped and tested.

## 8.1 USB tethering architecture

Implement an explicit, opt-in tether state machine on top of the validated USB network interface.

Before enabling tethering:

- Confirm USB network data plane is active and the host interface is reachable.
- Confirm the selected upstream interface exists, is connected and has a usable route.
- Verify the upstream can actually reach a probe endpoint before claiming Internet availability; distinguish link-only from Internet-ready.
- Present a clear warning that the attached computer receives routed Internet access.
- Require an explicit owner action, not merely plugging in USB.

Upstream choices may include:

- Wi-Fi client (`wlan0`) only if it is actually associated and routing works concurrently with the gadget.
- Cellular only if a real modem/data bearer exists and reports connected. The current reflash plan says `rmnet0` is disabled because the S10+ modem is not yet brought up. Do not offer “Mobile data” as an upstream merely because a Mobile tile exists.
- Other interfaces only when explicitly discovered and permitted by policy.

## 8.2 Implement forwarding/NAT safely

Choose one firewall/routing owner. Prefer an existing Nuxel NetworkManager sharing API if it is proven to configure the exact gadget interface and meet all firewall constraints; otherwise implement a narrow dedicated Nuxel tether provider with its own nftables table/chains and an explicit lifecycle.

Requirements:

- Enable IPv4 forwarding only while tether mode is active, after saving the prior sysctl value.
- Add narrowly scoped forwarding rules from USB gadget interface to the selected upstream.
- Add established/related return traffic only for the tether flow.
- Add NAT/masquerade only from the USB client subnet to the selected upstream interface.
- Keep the default forward policy/drop posture intact outside the narrowly scoped tether chains.
- Never flush the global nftables ruleset.
- Never remove `inet nuxel_console_guard` or bypass the existing SSH/console guard.
- Do not create a broad `iifname usb accept` or unrestricted LAN forward rule.
- Respect the VPN kill switch. Do not route tethered client traffic around a required VPN policy without an explicit policy design and user consent.
- Decide and document whether tethered hosts inherit the phone VPN or use the physical upstream; do not silently leak traffic outside the VPN.
- Handle DNS: either provide a real DHCP/DNS service on the USB side or use a documented host-side configuration. Do not advertise a resolver that is not running/reachable.
- If DHCP is added, lease only the tether subnet, bind only to the gadget netdev, and stop/remove state cleanly.
- If IPv6 tethering is not implemented, explicitly disable/withhold IPv6 router advertisements on the USB link or document the safe behaviour; do not leak unusable IPv6 defaults.
- Save exact previous sysctl, nft, route, DNS and DHCP service state. Restore only what this provider owns.
- Stop tethering on explicit OFF, USB detach, upstream disappearance, service crash or shutdown.
- Tether state is ON only after the forwarding path is configured and an attached host has end-to-end Internet access.

## 8.3 USB management mode must remain safe

Turning on USB Ethernet for SSH/deployment must NOT turn on Internet sharing automatically. USB tethering is a separate control, default OFF. Disabling tethering must not necessarily tear down local USB SSH unless the user also turns off USB networking.

---

# 9. WI-FI HOTSPOT

Add a real Wi-Fi hotspot option only if the S10+ Wi-Fi chipset, kernel driver, firmware and regulatory configuration expose a compatible AP mode.

Probe actual capabilities using NetworkManager/nmcli and `iw`/nl80211 where supported. Do not infer AP support from the existence of a hotspot icon asset or Android-era feature descriptions.

If AP mode is supported:

- Use NetworkManager's hotspot/shared mode if it owns the Wi-Fi device and can safely manage address, DHCP, DNS and NAT. Avoid simultaneously managing the same interface with hostapd and NetworkManager.
- Implement start/stop/status with read-back verification.
- Configure SSID and a strong WPA2/WPA3-capable passphrase according to actual driver support.
- Never return the passphrase in normal status polling or logs.
- Store credentials using the established secure settings/keyring mechanism where feasible; otherwise follow existing Nuxel secret-handling conventions and permissions.
- Handle channel/regulatory restrictions and unavailable hardware cleanly.
- Share an upstream only when explicitly configured and tested.
- Test that a second physical device can join, obtain an address, resolve DNS and reach the Internet (if upstream is enabled).
- Stop cleanly and restore the previous Wi-Fi client state. If simultaneous AP+STA is not supported, say so and explain the mode-switch behaviour before enabling.

If AP mode is not supported by the current Nuxel stack, return `UNSUPPORTED` with the actual nl80211/NetworkManager reason. Keep the tile visible but disabled or omit it according to the Settings UI conventions; never paint it ON.

Do not attempt to install undocumented vendor Wi-Fi firmware as part of this task. No proprietary USB Ethernet firmware is required; USB gadget data plane is kernel/software functionality.

---

# 10. NETWORKMANAGER / BRIDGE API

Existing `services/nuxel-bridge/src/network_manager.py` handles Wi-Fi connection information, DNS, VPN and ZeroTier, but the uploaded source has no hotspot/tether start/stop provider. Existing API paths include:

- `/api/v1/system/usb-mode`
- `/api/v1/usb-mode/set-mode`
- `/api/v1/system/tri-link`
- generic `/api/v1/rpc` with a controlled NetworkManager verb allowlist.

Extend existing architecture; do not create a second HTTP server or allow arbitrary shell commands from JavaScript.

## 10.1 Provider ownership

Define clear ownership:

- USB gadget composition: existing USB mode manager/coordinator.
- USB IP and USB SSH transport: dedicated USB network manager integrated with that coordinator.
- Internet-sharing/NAT/DHCP: one tether owner (NetworkManager shared mode or dedicated provider).
- Wi-Fi AP mode: NetworkManager if it controls the device; otherwise one explicitly chosen AP manager.
- Bridge: narrow typed RPC/status surface only.

Never have NetworkManager, a custom shell script and a second daemon all try to own the same interface/firewall/DHCP state.

## 10.2 Status schema

Expose a typed, versioned, read-only status response with fields equivalent to:

```json
{
  "success": true,
  "usb": {
    "supported": true,
    "state": "active",
    "mode": "ncm",
    "device_present": true,
    "host_interface": "enX",
    "phone_interface": "usb0",
    "phone_address": "10.15.19.82/24",
    "host_address": "10.15.19.1/24",
    "link": "up",
    "ssh": "authenticated",
    "acm_preserved": true,
    "last_error": null
  },
  "usb_tether": {
    "supported": true,
    "enabled": false,
    "state": "off",
    "upstream": null,
    "internet_verified": false,
    "last_error": null
  },
  "wifi_hotspot": {
    "supported": false,
    "enabled": false,
    "state": "unsupported",
    "reason": "actual driver capability reason"
  }
}
```

This is a schema example, not a claim that any state is currently true. Use `null`/`unknown` where data is missing. Do not hardcode the host interface name, phone interface name or supported booleans.

Status must be read-only and fast. Do not run disruptive configfs mutations on polling.

## 10.3 Actions and security

Implement narrow verbs such as:

- `usb-status`
- `usb-set-mode`
- `usb-preflight`
- `usb-tether-status`
- `usb-tether-start` with a validated upstream selection
- `usb-tether-stop`
- `hotspot-status`
- `hotspot-start` with strictly validated SSID/security/secret inputs
- `hotspot-stop`

Use existing API auth, protocol version checks, app identity and permission/capability policy. Add a permission such as `network:manage` or a better established capability if the project has one. Privileged actions must have a fixed allowlisted command/API and typed parameters. Never pass arbitrary command names, paths, interface names or shell fragments from JS into a root subprocess.

Require explicit action on start/stop. Return the actual provider read-back result and a stable error code. Do not return success merely because the subprocess exited zero.

---

# 11. QUICK SETTINGS AND SETTINGS UI

Existing Quick Settings is `pwa/nuxel-home/index.html` + `pwa/nuxel-home/js/qs.js`.

Current tiles include Wi-Fi, Bluetooth, Mobile, Location, DND, Flashlight, Rotate, Settings, Firewall; the expanded privacy row includes NFC, Fingerprint, Camera and Microphone. USB details currently show general USB, file transfer, console and transport status. There is no real USB-network tile and no hotspot toggle backend in the uploaded snapshot.

The JS `_toggle()` intentionally shows “control is unavailable” for unintegrated controls. Preserve that truth-first design.

## 11.1 Quick Settings controls

Add appropriate real controls, preferably within the expanded connection section or an appropriately designed additional row:

1. **USB Network** — enable/disable the local USB Ethernet function. This controls the USB data plane and local SSH link, not Internet sharing.
2. **USB Tether** — separate enable/disable for Internet sharing to the attached host; only enabled when USB network and a verified upstream exist.
3. **Hotspot** — Wi-Fi access point enable/disable only when actual hardware supports AP mode.

If the panel design cannot fit all three tiles cleanly, put the detailed actions in Network Settings and expose a simple USB Network + Hotspot/Sharing summary in QS. Do not overload the existing USB connected status indicator as a control.

Use the already-present hotspot/USB icon assets if still in the current repository; otherwise use the established icon pack. Do not fabricate an icon file path.

## 11.2 UI truth rules

For every tile render:

- `unsupported` → disabled, dim, explanation available.
- `unknown` / provider unavailable → neutral checking/unknown state; not OFF or ON.
- `transitioning` → busy state; prevent duplicate clicks.
- `active` → only after provider read-back confirms the function.
- `error` → show error/OSD and refresh true state.
- `off` → only after provider confirms off and cleanup completed.

A USB device plugged in does not mean USB networking is enabled. A USB Ethernet link does not mean SSH authentication passed. USB tether enabled does not mean the host has Internet. A Wi-Fi hotspot tile ON requires a real AP interface and read-back confirmation.

## 11.3 Settings page

Add a coherent Network/Tethering section to the existing Settings app if the existing architecture supports it. Audit current settings navigation and Wi-Fi page before creating new app structure.

Recommended UI options:

- USB Network: Off / Local USB Network / unavailable.
- USB Tethering: Off / Share Wi-Fi upstream / Share cellular only if cellular data actually works.
- Wi-Fi Hotspot: On/Off if AP mode supported.
- SSID and password fields for hotspot, with reveal control and secure storage.
- Upstream selector with live availability.
- Connected host/client information (only data actually exposed by the protocol).
- USB IP address, host link, SSH state, last error and diagnostic details.
- Warning that tethering grants the connected host Internet access.
- Separate buttons for Test USB Link and Stop Sharing.

Do not display fake client counts, signal strength, traffic rates or host names.

## 11.4 UI tests

Add tests covering:

- No provider / provider error.
- Unsupported Wi-Fi AP mode.
- USB device connected but network mode off.
- Network mode transitioning.
- USB link active but SSH unverified.
- SSH authenticated.
- USB tether enabled but upstream lost.
- Tether fully active and Internet verified.
- Hotspot active then stop.
- Rapid repeated click / double request.
- QS reopen/re-render preserves provider truth.
- Disabled tile cannot issue start action.
- Manual mode state and persisted selection after reboot.

---

# 12. FIREWALL, ROUTING, VPN AND PRIVACY SAFETY

Audit these exact files and all installed counterparts:

- `configs/nftables/nuxel-console-guard.nft`
- `configs/nftables/nuxel-firewall-config.json`
- `configs/nftables/nuxel-app-firewall.nft`
- `configs/nftables/nuxel-vpn-killswitch.nft`
- firewall service/provider scripts.

Current config lists USB interfaces such as `usb0`, `rndis0`, `ncm0`, `usb1` and `eth0` for console protection. The app firewall has a restrictive forward policy and the uploaded VPN/app firewall setup does not demonstrate complete Internet tethering. Do not interpret the console guard as a complete tethering policy.

Requirements:

- Preserve the console guard table and its priority.
- Preserve input/output defaults and per-app network class policy.
- Do not flush global nft rules.
- Use a separately owned tether table/chain or supported NetworkManager sharing backend.
- Add rules only for the exact USB subnet/interface and selected upstream.
- Scope established/related return traffic correctly.
- Scope NAT to the USB source subnet and chosen egress interface.
- Restore previous sysctl and nft state when stopped/failure/detach.
- Handle startup ordering and service restarts.
- Do not create a path that bypasses a VPN kill switch silently.
- Log exact installed rules and `nft list ruleset` evidence; a rule not present in read-back is not claimed.
- Ensure no client traffic leaks if tether service crashes or is killed.
- Ensure disabling tether does not remove rules or state owned by other providers.

Tests must prove that the firewall defaults remain intact before, during and after tethering; test negative paths as well as success.

---

# 13. SYSTEMD, STARTUP, DETACH AND RECOVERY

Provide appropriate systemd units/timers only where needed. Reuse current USB mode monitor/restore units if they can own the transition safely.

Requirements:

- Correct dependency ordering after configfs, NetworkManager, nftables and network-online state only where genuinely required.
- No automatic network function activation merely because a cable was plugged in unless the owner explicitly configured that behaviour.
- Default boot composition must be a safe ACM-preserving mode.
- Interrupted transition on boot returns to ACM-only `charging`, not a half-created NCM/hostspot mode.
- Tether service cannot start before the USB interface is active and upstream is verified.
- Upstream loss stops forwarding/marks tether degraded and offers safe recovery.
- Detach stops tether, cleans transient routes/DHCP and updates status.
- Reattach does not falsely assume host authentication or Internet connectivity.
- No polling of DWC3 debugfs registers.
- Service crash and stop operations are idempotent.
- Journald logs include correlation/transaction IDs but never Wi-Fi passwords, hotspot PSKs, private keys or sensitive config.

---

# 14. AUTOMATED TESTS AND QUALITY GATES

Build meaningful tests before physical validation. Add tests to the project's existing structure rather than a disconnected test harness.

## 14.1 Kernel tests/review

- Exact pinned source fetched and commit verified.
- Patch forward-apply/reverse-detection test.
- `olddefconfig` resolves requested symbols as expected.
- Kernel and DTB build pass.
- Patch applies in normal `build-kernel.sh` order.
- Static review confirms balanced misc-device and netdev lifetimes.
- No NCM cleanup use-after-free/double deregister/second-instance bug apparent.
- Existing ACM/NFC/display/fbdev/Mali changes preserved.

## 14.2 Gadget lifecycle tests

On a safe test target first, and then on the actual phone only after the source/rollback gates pass:

- create function instance;
- configure writable attributes only;
- link into the configuration;
- bind UDC;
- host enumerates;
- host detaches;
- unbind UDC;
- remove config link;
- remove function instance;
- recreate and repeat.

Test at least 10 consecutive cycles and, where feasible, 50+ soak cycles on a non-primary/lab target. On the owner phone only perform the physically approved bounded test after safety review. Capture kernel logs before/after; inspect pstore/ramoops after unexpected reboot. A phone reboot/watchdog/panic is a FAIL and must be diagnosed, not retried blindly.

Test error injection at each step: no UDC, no config directory, failed attribute write, interface timeout, failed IP, sshd unavailable, host never connects, host cable pulled mid-transition, timer rollback, process killed mid-transition, system reboot with in-progress marker.

## 14.3 Phone networking tests

- correct IP and mask applied;
- route collision detection on non-/24 networks;
- no default route change in local USB-only mode;
- WLAN address and SSH unaffected;
- phone reaches host over USB;
- host reaches phone over USB;
- correct SSH key enforced;
- deploy/test file checksum matches;
- disconnect/reconnect restores clean state;
- subnet conflict correctly refuses.

## 14.4 Mac host tests

- exact USB parent/interface mapping;
- NCM driver attach;
- correct interface identified;
- host IP assigned on that interface only;
- default route unchanged;
- DNS unchanged;
- Wi-Fi/VPN/ZeroTier unchanged;
- phone ping / TCP / SSH;
- authenticated command;
- hash-verified transfer;
- safe remove;
- physical detach/reconnect.

## 14.5 Linux host tests

Test on a real Linux host if available, with kernel `cdc_ncm`/`rndis_host` as applicable. Verify actual host driver, route, IP, SSH, file transfer, teardown and re-enumeration.

## 14.6 Tethering tests

With a real Internet upstream:

- USB network alone is local-only and does not share Internet.
- Explicit USB tether start configures DHCP/DNS (if used), forwarding and NAT.
- Host obtains the intended address and DNS configuration.
- Host can resolve names and reach public HTTPS endpoint.
- Phone's ordinary upstream still works.
- VPN policy behaves exactly as designed.
- Upstream disconnect removes/blocks Internet share.
- USB cable detach removes tether state.
- Stop restores exact prior forwarding/nft/routes/DNS/services.
- No global nftables flush or unrelated connectivity damage.

If no real upstream or second host is available, mark those physical tests `NOT TESTED`; do not substitute unit tests for them.

## 14.7 Wi-Fi hotspot tests

If AP mode exists:

- SSID starts.
- WPA security is applied.
- second device joins.
- client gets address.
- DNS works.
- Internet works only when configured.
- stop removes AP and restores client state.
- credentials never appear in logs/status.

If no AP capability exists, capture the `iw`/NetworkManager capability evidence and report `UNSUPPORTED`.

---

# 15. REFLASH BATCH INTEGRATION — ONE FLASH ONLY

`REFLASH-PLAN.md` explicitly groups USBNET with NFC, GPS/SSP, mobile networking and other kernel/vendor-gated components. The owner wants one coherent reflash rather than repeated experiments.

Therefore:

- Do not flash the phone in this mission.
- Do not run `dd`, `heimdall`, `fastboot flash`, TWRP flash commands or any partition-write command.
- Do not reboot the phone for USBNET testing without explicit operator approval and an established current test protocol.
- Do not independently build/flash an image that excludes the active NFC agent's new patch.
- Preserve all in-progress NFC and other batch work.
- Produce a clean, reproducible USBNET source patch, config fragment update, system payload, service units and test evidence ready to merge into the batch.

When the USBNET work is ready:

1. Re-read the latest `git status` and `REFLASH-PLAN.md`.
2. Record exact new kernel patches/config changes, system files, permissions, systemd units and API/PWA assets.
3. Confirm the NFC patch and USBNET patch coexist and apply in the intended sorted order.
4. Run the complete combined kernel build from the final combined source tree.
5. Verify the active config fragment still includes prior display, GPU, MFC and NFC capability settings.
6. Verify the final image includes both NFC and USBNET changes.
7. Add the USBNET row to the reflash acceptance matrix and identify which tests require physical operator actions.
8. Keep the previous A/B slot and serial recovery plan intact.
9. Mark the batch ready for operator review; do not trigger it.

If the NFC agent changes files while you work, resolve at source level with that agent/owner. Never overwrite or revert another agent's changes to make a build green.

---

# 16. DELIVERABLES

Create/update the following in the repository:

### `PWNAGE-USBNET-REPORT.md`

Executive verdict and feature matrix. Distinguish USB local networking, USB SSH, Internet tethering and Wi-Fi hotspot.

### `PWNAGE-USBNET-KERNEL-ANALYSIS.md`

Exact source commit, NCM failure root cause, full call/lifetime analysis, selected fix, patch rationale, config symbols and test results. Include why RNDIS/ECM were or were not selected.

### `PWNAGE-USBNET-TEST-RESULTS.md`

Automated and physical tests. Include host OS versions, USB descriptors, interface mapping, interface name, addresses, routes before/after, SSH key verification result, transfer hashes, detach/reconnect cycles, firewall/tether results and explicit NOT TESTED items.

### `PWNAGE-USBNET-REFLASH-MANIFEST.md`

Exact list of boot/kernel, DT, system-image, config, service, helper, API and PWA payload changes. Include patch order, hashes, build commit, image hashes and prerequisites for the one combined batch. Clearly state that no flash was performed during this mission.

### Kernel patch and config

- New uniquely named patch in `kernel/s10plus/patches/`.
- `.required` marker only if patch is verified and mandatory.
- Updated patch README.
- Updated actual active config fragment, only for validated symbols.

### Runtime source and packaging

- Unified USB gadget mode manager integration.
- Phone-side USB net manager/helper.
- Host-side macOS/Linux helper.
- Tether provider and nftables/DHCP integration, if supported.
- NetworkManager hotspot provider, if supported.
- systemd unit(s), default configuration and permissions.
- Bridge API/provider changes.
- Quick Settings + Settings UI changes and assets if needed.
- Automated tests and regression fixtures.
- Logs and screenshots/host diagnostics where available.

Do not add binary blobs or pretend firmware is needed. USB CDC-NCM/RNDIS/ECM gadget networking does not require a new proprietary Samsung sensor/ISP-style firmware blob. If investigation discovers an actual signed/vendor firmware dependency, document its source, licence/provenance, architecture and exact compatibility before adding it. Do not download arbitrary firmware.

---

# 17. FINAL RESPONSE FORMAT

At the end report:

1. **USB local data plane:** PASS / PARTIAL / FAIL, mode selected and exact evidence.
2. **NCM teardown regression:** PASS / FAIL / NOT TESTED, number of cycles and whether pstore stayed clean.
3. **Mac host:** exact OS, interface mapping and USB SSH authentication result.
4. **Linux host:** status if tested.
5. **USB tethering:** PASS / PARTIAL / UNSUPPORTED / NOT TESTED, upstream used and end-to-end proof.
6. **Wi-Fi hotspot:** PASS / UNSUPPORTED / NOT TESTED, capability and client test.
7. **Quick Settings/Settings:** real controls and backend status verification.
8. **Recovery/ACM:** verified in every mode tested.
9. **Reflash readiness:** exact combined patch/config manifest; explicitly state no flash performed.
10. **Artifacts:** paths to reports, patches, logs and hashes.

Do not end with “implemented” if only source code exists. Do not end with “working” if physical USB link or host proof is missing.

**Ultimate objective:** one controlled future reflash that contains the corrected kernel gadget lifecycle and all required userspace pieces, after which USB networking, optional tethering and the corresponding controls work reliably without sacrificing Nuxel's CDC-ACM recovery path or other existing networking.
