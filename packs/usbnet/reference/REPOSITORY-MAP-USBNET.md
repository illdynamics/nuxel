# Repository map — USB networking work

This map records the implementation boundaries found in the uploaded repository snapshot. It is a navigation aid, not a substitute for re-inspection.

| Area | File(s) | Existing role / gap |
|---|---|---|
| Mission status | `REPORT-USBNET.md` | Previous physical audit; NCM teardown panic, RNDIS unverified, only ACM live |
| Reflash coordination | `REFLASH-PLAN.md` | Calls for one A/B batch; USBNET is boot/kernel + system helper work |
| Phone USB net prototype | `tools/beta/live/nuxel-usb-net.py` | Read-only status, capability checks, NCM-only guarded apply, fixed subnet, NCM-specific rollback |
| Host USB net | `scripts/s10plus-debug-pack/nuxel-usb-net-host.sh` | Linux/macOS discover/apply/remove/diagnose; macOS device-to-interface association unsafe; diagnostic SSH target wrong |
| Existing USB mode state | `services/nuxel-bridge/src/usb_mode.py` | Charging/file-transfer only; calls one helper; real state read-back |
| Existing gadget owner | `services/nuxel-s10/bin/nuxel-usb-mode.sh` | Configfs owner for ACM + MTP/File Transfer, UDC transitions and recovery to Charging |
| Bridge API | `services/nuxel-bridge/src/api.py` | Existing USB mode status/set routes; NetworkManager RPC allowlist; no tether/hotspot provider in snapshot |
| NetworkManager provider | `services/nuxel-bridge/src/network_manager.py` | Wi-Fi/DNS/VPN/ZeroTier, but no hotspot/tether operations in snapshot |
| Quick Settings markup | `pwa/nuxel-home/index.html` | Existing Wi-Fi/Bluetooth/mobile/location/etc tiles; USB status detail rows; no real USB network/hotspot toggle |
| Quick Settings controller | `pwa/nuxel-home/js/qs.js` | Existing controls and honest unavailable behavior; add typed provider-backed controls |
| Firewall | `configs/nftables/nuxel-console-guard.nft`, `nuxel-firewall-config.json`, app/VPN chains | USB console allowances exist; this is not a complete tethering NAT/DHCP/forward policy |
| Kernel source pin/build | `kernel/s10plus/build-kernel.sh` | Pinned 4.14.253 source; patch application and active config fragment |
| Active config fragment | `kernel/s10plus/configs/nuxel-drm-kbase.fragment` | Actual default capability fragment; do not edit informational `defconfig` only |
| Kernel patch queue | `kernel/s10plus/patches/` | Add a unique USB patch without overwriting NFC `0007` or concurrent work |
| Detach logic | `services/nuxel-bridge/src/system_indicators.py`; `docs/a77-usb-detach/ROOT-CAUSE.md` | A77 combines configured UDC proof with speed/VBUS/Type-C detach vetoes |
| Dangerous old signal | `docs/a74/USB-DETACH-SEQUENCE.md` | DWC3 debugfs `link_state` read after detach can fault/lock up; do not reintroduce |
| Old physical state history | `docs/a73/USB-PHYSICAL-STATE-MATRIX.md` | Original stale UDC/type-C detach behaviour |
| NCM panic evidence | `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/` | pstore records `misc_deregister → ncm_free_inst → configfs_rmdir` panic |

## Critical distinctions

- ACM serial works; that does not mean USB Ethernet works.
- A network interface exists; that does not mean IP works.
- IP ping works; that does not mean SSH authentication works.
- SSH works; that does not mean Internet tethering works.
- USB tethering (phone upstream shared to host) is not reverse tethering (host upstream shared to phone).
- Wi-Fi hotspot requires AP-mode support from the actual S10+ Wi-Fi driver/firmware and correct NetworkManager ownership.
- Kernel config symbols being `y` do not prove runtime lifecycle safety.
