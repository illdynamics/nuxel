# PWNAGE-USBNET — Report (2026-11-14)

**Mission:** USB Ethernet data plane (CDC-NCM) + USB SSH/deploy + optional USB
Internet tethering + honest Wi-Fi hotspot controls, for S10+ `SM-G975F` /
Exynos 9820 / pinned Linux 4.14.253, host macOS 15.7.9 Apple Silicon.

## Verdict

| # | Layer | Verdict |
|---|---|---|
| 1 | USB local data plane | **NEEDS_VALIDATION** — implemented; no phone reachable to test |
| 2 | NCM teardown regression | **PASS (source + object)**, **NOT TESTED** physically |
| 3 | Mac host helper | **PASS** (real-Mac IORegistry verification + fixtures); end-to-end NOT TESTED |
| 4 | Linux host | **NOT TESTED** (no Linux host) |
| 5 | USB tethering | **NEEDS_VALIDATION** — provider + scoped nft ready; no end-to-end run |
| 6 | Wi-Fi hotspot | **UNSUPPORTED until probed**; UI never paints it ON |
| 7 | Quick Settings / Settings / lockscreen | Real controls wired to providers; not run on device |
| 8 | ACM recovery | Preserved in every composition (simulated) |
| 9 | Reflash readiness | Kernel patch + userspace payload ready; **no flash performed** |

## What changed in this run (and what was actually broken)

1. **The NCM "fix" did not exist in the artifact.** The previous run's build
   tree held only a 10-line stub, and the patch named in its manifest was
   missing from `kernel/s10plus/patches/`. A real patch was written from the
   pinned source: refcounted singleton ownership, work drained before free,
   exactly one `misc_deregister()`, failure propagation, module-exit cleanup,
   and a build marker. It now applies to the **pristine** file and compiles.
2. **Two owners of the same gadget.** `nuxel-usb-mode.sh` (charging/MTP) and
   `nuxel-usb-net-helper.sh` (NCM) both edited the same configfs tree — the
   spec's explicit "never" case. The network helper is **retired**; the mode
   manager now owns **all four** compositions (charging, file_transfer,
   usb_network, usb_tethering) with one flock, one journal, rollback to
   ACM-only and boot recovery.
3. **macOS discovery could never work.** `ioreg -a` (no `-l`) carries no
   `idVendor`/`BSD Name`, and the helper looked for the interface as an
   *ancestor* of the driver while macOS puts it as a **child**. Verified on the
   real Mac and fixed (uses `-a -l`, walks ancestors, exact VID:PID).
4. **Wrong probe target.** Diagnostics and the device default were `.82`
   (the old plan where the host was `.1`). The phone is `.1`, host `.2`;
   all defaults, tests, tri-link and the live helper now agree.
5. **Tether was one button with an unscoped NAT.** Now: USB Network, USB Tether
   composition and Internet sharing are separate. The share has its own
   `inet nuxel_usb_tether` table (forward at priority -50, policy drop; exact
   source address; established return only; NAT scoped to one upstream), saves
   and restores `ip_forward`, refuses a physical upstream while the VPN kill
   switch is armed, and only reports `internet_verified` after the attached
   computer's own end-to-end evidence (`usb-tether host-report`).
6. **Tri-link lied about 4.14.253.** It hardcoded "blocked" regardless of the
   running build. It now judges the marker and the owner's activation record.
7. **UI truth.** QS USB tile shows `link` until SSH is verified; the tether
   tile brings the USB composition up only on an explicit tap; hotspot shows
   `n/a` when unsupported; the lockscreen sheet gained a USB Network option.
8. **Typed owner actions only.** `usb-net enable-for-host`, `usb-tether
   start/stop/verify/host-report/upstreams`, `network hotspot-*`; no JS shell.

## Deliverables

* `PWNAGE-USBNET-REPORT.md` (this file)
* `PWNAGE-USBNET-KERNEL-ANALYSIS.md`
* `PWNAGE-USBNET-TEST-RESULTS.md`
* `PWNAGE-USBNET-REFLASH-MANIFEST.md`
* `kernel/s10plus/patches/0011-nuxel-usb-ncm-lifecycle.patch` (+ `.required`),
  `kernel/s10plus/patches/README.md`
* `services/nuxel-s10/bin/nuxel-usb-mode.sh` (single owner, 4 modes)
* `services/nuxel-s10/bin/nuxel-usb-net-monitor.sh` (shim to the owner's monitor)
* `services/nuxel-s10/systemd/nuxel-usb-net-{monitor,restore}.service`
* `services/nuxel-bridge/src/{usb_tethering,usb_tether,usb_mode,tri_link_status,api}.py`
* `scripts/s10plus-debug-pack/nuxel-usb-net-host.sh` (Mac/Linux helper,
  `--tether-test`) and `nuxel-usb-net-accept.sh` (one-command physical acceptance)
* `pwa/nuxel-home/{index.html,js/qs.js,js/lockscreen-indicators.js}`,
  `pwa/nuxel-apps/settings/{index.html,usb-network-settings.js}`
* `tools/pwnage_usbnet/deploy-pwnage-usbnet.sh` (deploy/rollback)
* `tests/pwnage_usbnet/` (39 tests incl. a real-transition simulator),
  `tests/a80/test_usb_net_provider.py`
* `docs/beta-finalization/live/evidence/pwnage-usbnet-114000/`

## Blocker

The phone did not answer on `192.168.178.167`, was absent from every USB bus
and from `adb` for the whole run. Therefore nothing could be deployed, tested
on hardware, rebooted or flashed. This report does **not** claim working USB
networking or tethering — only that the source, kernel patch, providers, UI and
tests are ready for the device and the single controlled reflash batch.
