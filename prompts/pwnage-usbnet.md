# PWNAGE USBNET — Nuxel USB Networking + Tethering + Quick Settings

You are working on Nuxel for the Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820), Fedora Linux ARM64, Samsung-derived Linux 4.14.253.

**Read and follow `full-pwnage-usbnet.md` completely.** It is the binding technical specification, test plan, integration plan and safety contract.

## Mission

Finish the actual USB Ethernet data plane so the phone exposes a usable USB network interface to the owner's Apple Silicon Mac (macOS 15.7.9), provide authenticated USB SSH/deploy, and implement honest controls for optional USB Internet tethering and Wi-Fi hotspot in Quick Settings and Settings.

This is not just adding icons or enabling Kconfig symbols. Implement the kernel/runtime fix, phone and host networking, provider/API, transition handling, tether/firewall behaviour, UI and physical test plan.

## The repo already contains important groundwork

Start by inspecting the current checkout and `git status`. Relevant existing files include:

- `REFLASH-PLAN.md`
- `REPORT-USBNET.md`
- `tools/beta/live/nuxel-usb-net.py`
- `scripts/s10plus-debug-pack/nuxel-usb-net-host.sh`
- `services/nuxel-bridge/src/usb_mode.py`
- `services/nuxel-s10/bin/nuxel-usb-mode.sh`
- `services/nuxel-bridge/src/network_manager.py`
- `services/nuxel-bridge/src/api.py`
- `pwa/nuxel-home/index.html`
- `pwa/nuxel-home/js/qs.js`
- `configs/nftables/`
- `kernel/s10plus/build-kernel.sh`
- `kernel/s10plus/configs/nuxel-drm-kbase.fragment`
- `kernel/s10plus/patches/`
- `docs/a73/`, `docs/a74/`, `docs/a77-usb-detach/`
- `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`

Verify the live source; the pack's reference files are a snapshot, not a replacement for inspecting current code.

## Critical known blocker

The previous real CDC-NCM attempt on the 4.14.253 Samsung kernel caused a panic during configfs function teardown. The pstore stack went through:

`misc_deregister → ncm_free_inst → usb_put_function_instance → ncm_attr_release → configfs_rmdir`

The Samsung-specific `f_ncm.c` cleanup calls `misc_deregister(&mirrorlink_device)`. **Do not retry NCM on the old kernel, do not remove its safety gate, and do not write the read-only `ifname` attribute.** Fetch the exact pinned kernel source, prove the lifecycle root cause, fix registration/cleanup ownership and error paths, then build regression tests.

RNDIS compiles but is not physically validated. Its different cleanup path does not prove it safe. macOS should use the native CDC-NCM path as the primary target; do not make a third-party RNDIS driver, disabling SIP or lowering system security a requirement.

## Single gadget owner

Extend the existing USB mode state machine. Do not create a second service that independently edits the same configfs gadget. Every mode must preserve CDC-ACM serial recovery. Add safe transactional modes for charging, MTP/file transfer, USB network and (separately) USB tethering. Snapshot exact state, serialize transitions, use rollback and restore ACM-only on interrupted/failed transitions.

Reuse A77 physical detach detection. Do **not** read DWC3 `link_state` debugfs; A74 documents a hard lockup/watchdog reboot after that register read on this kernel.

## Networking and UI scope

Keep these distinct:

1. USB Ethernet/local SSH (no Internet sharing).
2. USB tethering (phone's Wi-Fi or real cellular upstream shared to the connected computer; explicit opt-in).
3. Wi-Fi hotspot (phone AP mode; only when actual Wi-Fi driver capability supports it).
4. Reverse tethering (host Internet to phone) is not implied and must not be silently conflated.

Repair host interface discovery: current macOS helper checks VID/PID but can select an unrelated Ethernet port. Prove the selected BSD interface belongs to the exact USB device using IORegistry/device ancestry. Correct diagnostics to probe the phone address, not the host's `.1` address. Preserve default route, DNS, Wi-Fi, VPN and ZeroTier for local USB networking.

Implement end-to-end tethering only with narrow forwarding/NAT/DHCP/DNS rules, explicit upstream selection, VPN kill-switch awareness and exact cleanup. Never flush nftables or weaken the console guard. A USB link by itself is not proof of tethered Internet.

Add real Bridge provider actions and read-back status, permission checks, Quick Settings controls for USB Network / USB Tether / Hotspot as appropriate, and coherent Network Settings. Unsupported and unknown states must never look ON. No arbitrary shell commands from JS.

## Kernel + one-reflash constraint

Use the exact pinned kernel commit and the actual build fragment `kernel/s10plus/configs/nuxel-drm-kbase.fragment`. Do not edit only informational `defconfig`/legacy `live-required.config`. Add a new unique USBNET kernel patch; do not overwrite the NFC agent's `0007` patch or concurrent work.

**Do not flash or reboot the phone in this mission.** The owner wants one controlled reflash batch containing NFC, USBNET and other kernel-gated work. Prepare the patch, source, services, API, UI, tests and `PWNAGE-USBNET-REFLASH-MANIFEST.md` for that combined batch. Preserve all current changes; do not reset, stash or broadly clean the shared tree.

## Required physical validation

When the operator explicitly makes a current test build available and authorizes testing:

- verify ACM serial remains available;
- create/bind/enumerate NCM and repeat create/unbind/remove/recreate cycles without panic;
- verify exact Nuxel USB interface appears on the Mac;
- configure only that interface and preserve default route/DNS/Wi-Fi/VPN;
- ping and SSH to the phone using pinned host-key/public-key authentication;
- hash-verify a test transfer;
- physically unplug/reconnect and verify state clears/restores;
- test USB tether end-to-end with a real upstream;
- test Wi-Fi hotspot with a second device if AP mode exists.

Synthetic tests are useful but do not replace physical proof. If no physical test can be run, mark it `NOT TESTED`.

## Deliverables

Create/update:

- `PWNAGE-USBNET-REPORT.md`
- `PWNAGE-USBNET-KERNEL-ANALYSIS.md`
- `PWNAGE-USBNET-TEST-RESULTS.md`
- `PWNAGE-USBNET-REFLASH-MANIFEST.md`
- uniquely named kernel patch + `.required` only after verified, patch README, active config fragment as needed;
- phone-side USB network manager;
- host-side Mac/Linux helper;
- unified USB gadget state-machine integration;
- tether/hotspot provider and safe firewall/network integration where supported;
- Bridge API/RPC and Quick Settings/Settings UI;
- automated tests, logs and SHA256 evidence.

No new proprietary USB firmware is expected or included. Do not invent or download blobs.

**Completion means real USB SSH/data transfer works on the Mac, the NCM teardown regression is fixed and tested, tether/hotspot controls are honest and physically verified where hardware supports them, ACM recovery survives, and the complete result is ready to join the single controlled reflash batch.**
