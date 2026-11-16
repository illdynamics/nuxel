# PWNAGE-USBNET — Reflash Manifest (join the single combined batch)

**No partition was written and no device was rebooted or flashed by this run.**
The phone was unreachable on Wi-Fi, USB and ADB (see
`PWNAGE-USBNET-TEST-RESULTS.md` §1). This entry is prepared to join the ONE
controlled A/B batch in `REFLASH-PLAN.md` together with NFC and the
SSP/GPS/sensorhub work.

---

## 1. Kernel patch

| Item | Value |
|---|---|
| Source | `Linux4/android_kernel_samsung_exynos9820` @ `f7194c1d15eded1c2a1a4dc63825b26103435cc0` |
| New patch | `kernel/s10plus/patches/0011-nuxel-usb-ncm-lifecycle.patch` + `.required` |
| Patch sha256 | `95d8a3e7fde4e6145bc87ae6c284fa094d6d55c4e9aebd6f7d3c041e03e84b78` |
| Applies to pristine pinned `f_ncm.c` | YES (`git apply --check`) |
| Retired | `0011-nuxel-usb-ncm-idempotent-misc-deregister.patch` → `.retired` (prefix-only, insufficient) |
| Fragment | `kernel/s10plus/configs/nuxel-drm-kbase.fragment` (no new symbol required — NCM/NFC/SAMSUNG_COMPOSITE/NFT_MASQ_IPV4 already present) |
| Marker for CI/apps | `const char nuxel_ncm_lifecycle_marker[]` (exported) and `/sys/class/misc/usb_ncm/nuxel_fix` = `nuxel-ncm-lifecycle-fix-v2` |
| Build check this run | `drivers/usb/gadget/function/f_ncm.o` — PASS, marker `R` in `.rodata` (`evidence/pwnage-usbnet-114000/`) |

## 2. Userspace payload (SSH deploy; no reflash needed)

`tools/pwnage_usbnet/deploy-pwnage-usbnet.sh` (`--rollback`). sha256 of the
deploy script itself: `3d8c4e9f7d1c94798d51813ab582d96cb5635f9e553990650df537e7bda55c96`.

| Source | Target | Mode |
|---|---|---|
| `services/nuxel-s10/bin/nuxel-usb-mode.sh` | `/usr/lib/nuxel/nuxel-usb-mode.sh` | 0755 |
| `services/nuxel-s10/bin/nuxel-usb-net-monitor.sh` | `/usr/lib/nuxel/nuxel-usb-net-monitor.sh` | 0755 |
| `services/nuxel-s10/systemd/nuxel-usb-net-monitor.service` | `/etc/systemd/system/` | 0644 |
| `services/nuxel-s10/systemd/nuxel-usb-net-restore.service` | `/etc/systemd/system/` | 0644 |
| `services/nuxel-bridge/src/{api,usb_tethering,usb_tether,usb_mode,tri_link_status,network_manager}.py` | `/usr/lib/nuxel/nuxel-bridge/` | 0644 |
| `pwa/nuxel-home/{index.html,js/qs.js,js/lockscreen-indicators.js,css/status-bar.css}` | `/usr/share/nuxel/pwa/nuxel-home/` | 0644 |
| `pwa/nuxel-apps/settings/{index.html,usb-network-settings.js}` | `/usr/share/nuxel/pwa/nuxel-apps/settings/` | 0644 |

Deploy also **removes** the retired `/usr/lib/nuxel/nuxel-usb-net-helper.sh`
and disables the old `nuxel-usb-mode-restore.service` (it restored only MTP;
the single owner now handles restore + recovery).

Image build: `images/s10plus/build-phone-rootfs-inside-fedora.sh` no longer
installs the second helper and enables `nuxel-usb-net-restore.service`.

## 3. Security / firewall

* Tether: `table inet nuxel_usb_tether` only — forward hook priority -50 with
  `policy drop`, exact phone source address, established return only, NAT
  scoped to one upstream. Deleted on stop/detach/failure.
* No global `flush`, no modification of `inet nuxel_console_guard` or
  `inet nuxel_app_firewall`; `ip_forward` saved/restored exactly.
* VPN kill switch armed + physical upstream → refuse (`VPN_CONFLICT`).
* DHCP: not provided by the phone; the host is statically configured
  10.15.19.2/24 with gateway 10.15.19.1 (reported as `dhcp:
  static-host-config`). No resolver or RA is advertised.
* Rebooting/unplugging a share: monitor detects A77 detach (UDC speed/VBUS)
  and stops the share before returning to ACM-only.

## 4. Owner acceptance sequence after the batch

1. `/dev/ttyACM*` / `/dev/cu.usbmodem*` still enumerates (ACM in every mode).
2. `nuxel-usb-mode.sh status` → `charging`, `acm_present: true`.
3. Enable USB Network (QS or Settings). The tile reads `USB Net on` only after
   the owner recorded a live netdev; `link` until SSH is verified.
4. On the Mac:
   `nuxel-usb-net-host.sh --discover --json` (must be the exact device),
   `sudo --apply`, `ping 10.15.19.1`, `--ssh` (pinned key),
   hash-verified transfer, then `--remove`.
5. Soak: toggle USB network off/on ≥10 times; `dmesg`/pstore clean.
6. Tether: Settings → “Share Internet with attached computer” (or QS Tether),
   then on the Mac `--tether-test` — status becomes `on` only after the host
   reports evidence; stop and confirm `ip_forward`/nft restored.
7. Hotspot: must show `n/a` unless `hotspot-status` reports supported.
8. Reboot; the phone must boot **Nuxel** (TWRP would mean a bootloop; recover
   via the previous A/B slot + ACM console).

## 5. Open items blocking "final" (must be done in the batch window)

1. **The shared kernel tree is mid-series for the NFC agent**: required
   `0007-nuxel-sec-nfc-nci-transport.patch` conflicts with the current
   `.build/src`, so `build-kernel.sh` aborts before USBNET. This is
   concurrent-work state, not a USBNET defect. Resolve it with the NFC owner,
   then run one combined build from the final tree.
2. The previously recorded boot image
   `build/out/s10plus/debug-candidates/p112000-usbnet/boot-usbnet-ncm-lifecycle.img`
   was built from a tree **without** the lifecycle fix and must not be flashed.
   The newest candidate present is
   `p113000-nfc-r1/boot-k94-fixed.img` (sha256
   `98610b52efa4122990beab498f47db9dbb63d2a62d2c414dd600f764be071220`) —
   owned by the NFC work; it must be rebuilt from the final combined tree and
   re-gated with `tools/s10plus/verify-boot-image.py` (including the
   `nuxel-ncm-lifecycle-fix-v2` marker) before flashing.
3. Physical NCM teardown soak, ACM preservation, Mac interface/SSH/transfer
   and tether end-to-end are **NOT TESTED** and are acceptance gates.

4. **Deploy-manifest coverage test** (`tools/beta/live/tests/test_live_deploy_plan.py`)
   currently fails on ~200 *unrelated*, untracked files in the shared tree
   (`pwa/nuxel-apps/*`, `configs/nuxel/*`, other agents' `services/*`). It is
   the repository-wide extension manifest, concurrently owned; USBNET ships
   through `tools/pwnage_usbnet/deploy-pwnage-usbnet.sh` regardless. The
   manifest must be reconciled in the batch window, not by this mission.

