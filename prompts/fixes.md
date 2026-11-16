## What I fixed (code, unverified on hardware)
1. **Firewall can no longer break boot** — bounded with `timeout`, `TimeoutStartSec=75`, soft steps, no start-limit give-up; the firewall still loads before the network units.
2. **Console guard hardened** — new `prerouting_guard` chain at priority −300 (before `nuxel_raw`), so a conntrack/"invalid" classification can never black-hole SSH/ping; `console-verify` now proves the prerouting chain exists and loads the accept-only guard if the ruleset is empty.
3. **Wi-Fi SSH self-heals** — `nuxel-ssh-lan-allow` helper + `sshd.service.d/20-nuxel-lan-allow.conf` guarantee `AllowUsers … root@192.168.178.0/24` before every sshd start (idempotent, only extends the allowlist; key-only auth untouched).
4. **USB console self-repairs** — initramfs unbinds any foreign serial-less gadget from the UDC before starting `nuxel-console`; `Charging Mode` now ensures/verifies `acm.usb0` and recreates it once if `/dev/ttyGS*` doesn't appear.
5. **Pattern lock setup** — Settings now has just a **“Set up pattern lock”** button; nothing (no matrix, no PIN field) is shown until pressed, then a **Step 1 / Step 2** two-draw wizard stores the pattern only when both draws match, and sets **Pattern + PIN** if you enter a fallback PIN. Layout adapts to landscape. The old preset can no longer activate an unconfirmed pattern. Status now reports the real credential kind (`secret_kind`/`pattern_set`).

Static checks: new `tests/pwnage105200/` → **27/27 PASS**; A80/A86 lockscreen contracts PASS (the `jsdom` check fails only because `/tmp/jsdomtest/node_modules` doesn't exist here). Not staged yet (the tree already had many unrelated uncommitted changes, including a large in-progress `bridge.py` rewrite I left untouched).

## Still blocked
Reflash → boot → ADB/serial console → Wi-Fi SSH → USB SSH/NCM + tethering → performance/smoothness → GPU acceleration → GTK/flatpak double icons → autorotation sensor → reboot verify — all need the device.

**To continue:** please confirm the USB-C data cable is firmly in the Mac (or plug it straight into the Mac, not a hub), then say "phone plugged in". I'll immediately check for TWRP ADB, push these fixes into the live rootfs, reboot into Nuxel, and verify the consoles before moving to the rest.
tokens used
9,376,410

