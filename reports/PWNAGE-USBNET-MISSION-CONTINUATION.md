# PWNAGE-USBNET — continuation note (2026-11-14 02:25 UTC)

The mission is **not** complete in the sense the owner asked for (real USB
networking + tethering working from the Mac). The blocking condition has held
for every probe during this run:

* `ping 192.168.178.167` fails (ARP incomplete), SSH times out;
* no USB child device enumerates on the Mac (no `18d1`, no Samsung, no
  `cu.usbmodem*`), `adb devices` is empty.

Therefore no deploy to the live phone, no live test, no tether proof, no reboot
and no reflash could be performed. Nothing was flashed; no partition was
written.

## What is ready and verified (all offline)

| Item | Evidence |
|---|---|
| Real NCM lifecycle patch (applies to pristine pinned tree, compiles, marker in `.rodata`) | `PWNAGE-USBNET-KERNEL-ANALYSIS.md`, `evidence/pwnage-usbnet-114000/` |
| Single gadget owner (charging/file_transfer/usb_network/usb_tethering), flock + journal + rollback + boot recovery | `services/nuxel-s10/bin/nuxel-usb-mode.sh`, 31-check simulation |
| Tether provider (own nft table, exact source, VPN-aware, host-evidence verified) | `services/nuxel-bridge/src/usb_tether.py` + tests |
| Bridge/API typed actions, QS/Settings/lockscreen honesty | `api.py`, `qs.js`, `lockscreen-indicators.js`, `usb-network-settings.js` |
| Mac exact-device discovery (real IORegistry shape verified) + acceptance script | `nuxel-usb-net-host.sh`, `nuxel-usb-net-accept.sh` |
| Tests | 116 passed (`evidence/.../pytest-114000.txt`), simulation 31/31 |

## To finish the moment the phone is reachable

1. Deploy userspace: `NUXEL_HOST=root@192.168.178.167
   NUXEL_SSH_KEY=~/.ssh/wicked_wqn_id_rsa
   tools/pwnage_usbnet/deploy-pwnage-usbnet.sh`
2. Kernel half: resolve the NFC agent's `0007` conflict, run one combined
   `kernel/s10plus/build-kernel.sh`, re-gate with `verify-boot-image.py`
   (must find `nuxel-ncm-lifecycle-fix-v2`), then flash once from TWRP.
3. On the Mac: `scripts/s10plus-debug-pack/nuxel-usb-net-accept.sh` — it runs
   discovery → apply → ping → SSH → hash transfer → tether proof → remove and
   records everything under `$TMPDIR/nuxel-usb-accept-*`.
4. Reboot the phone; booting into Nuxel is success, TWRP means a failed boot
   (recover the previous A/B slot + ACM console).

## Reflash decision

**Not needed for the userspace half.** The boot image **must** be rebuilt for
the NCM fix (the only recorded p112000 image predates it); that belongs in the
single combined batch with NFC, as `PWNAGE-USBNET-REFLASH-MANIFEST.md` and
`REFLASH-PLAN.md` §7 state.
