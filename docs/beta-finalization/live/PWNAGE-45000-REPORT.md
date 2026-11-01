# PWNAGE-45000 — implementation and live verification report

Date: 2026-10-31
Device: Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
Live kernel: `4.14.253-gf7194c1d15ed-dirty`
OS: Nuxel / Fedora 43 aarch64
SSH: `root@192.168.178.167` over Wi-Fi, key `~/.ssh/wicked_wqn_id_rsa`

## Result summary

- Source implementation: complete for all userspace features requested.
- Offline regression: **291 PASS / 0 FAIL** (`tests/pwnage45000/run-all.sh`).
- Live device: updated and rebooted; providers, registry, dock art, Firefox,
  Nuxel Software, DND, torch and display edge-light verified on the handset.
- Honest blockers: USB host copy needs a physical cable/host; NFC kernel off;
  fingerprint has no secure provider; Flatpak user namespaces off; graphical
  polkit has no logind session; VLC's Qt GUI module is broken in this Fedora build.

## Confirmed causes

1. **Lockscreen order/transport sizing** — primary DOM order was correct but the
   transport row was still derived from the old 40px/252px geometry. Updated to a
   56px row at 286px (76px wide File Transfer cell); landscape remains 44px.
2. **USB File Transfer** — kernel/configfs support existed
   (`CONFIG_USB_CONFIGFS_F_MTP=y`, `CONFIG_USB_F_MTP=y`), and a responder existed
   but exported `/home/nuxel` wholesale. This was a security bug as well as the
   immediate activation gap. The responder now serves only `/home/nuxel/Shared`.
   Composition was proven live with both `acm.usb0` and `mtp.gs0`; `/dev/mtp_usb`
   appeared and the responder opened it. With no host cable, `active` stays false.
3. **Software center** — recheck showed DNF/PackageKit/AppStream are available and
   network repositories work. GNOME Software 49.4 installs but SIGSEGVs on this
   image before a surface. Added a real GTK3 PackageKit front-end
   (`/usr/lib/nuxel/nuxel-software`) using fixed argv `pkcon`; it launches visibly.
   `pkcon resolve/search` returns real Fedora rows. Flatpak is blocked by
   `CONFIG_USER_NS=n` (`unshare -U: Invalid argument`).
4. **Native app launch** — the bridge launched session-user apps with
   `XDG_RUNTIME_DIR=/run/user/1000`; the Phoc socket lives at
   `/run/nuxel-wayland` and was not group-writable. Firefox therefore exited with
   “no display” or “Permission denied”. Fixed the session runtime (user-owned
   `/run/user/1000` with the Phoc socket symlinked), a post-socket permission
   watcher, socket ACLs and dconf directory ownership. Launch responses now include `process_alive` and
   `surface_seen`; Firefox and Nuxel Software return `outcome=visible`.
5. **NuXTore** — catalog ID `org.nuxel.NuxTore` did not match canonical
   `org.nuxel.Nuxtore`, and install/remove were localStorage-only. Added a
   Bridge-owned atomic registry mutation API, case alias migration, runtime
   reconciliation and Home registry refresh. Install only commits after
   registration; remove unregisters and preserves payload/user data.
6. **Dock art** — source PNGs have huge transparent margins; the old generator
   scaled the whole canvas. New generator alpha-crops at threshold 8, preserves a
   glow pad, normalizes to a 44px content box, premultiplies exactly once, writes
   `navdock-art.h`, and regenerates the 96px DOM fallbacks. Native dock rebuilt and
   running on the phone.
7. **NFC** — live kernel reports `# CONFIG_NFC is not set`; only an I2C 0x27 hint
   exists. Provider reports `BLOCKED_KERNEL`; toggle/tag test are disabled.
8. **Fingerprint** — qbt2000 driver and `/dev/qbt2000_fd`, `/dev/qbt2000_ipc` are
   present, but no secure TEE enrollment provider exists. Provider reports
   `BLOCKED_SECURE_PROVIDER`; no templates are read/imported/exported.
9. **Security lock** — credential verification moved to a root Bridge provider
   using scrypt + salt + constant-time compare + persistent failure lockout.
   Native launch refuses while locked. Live PIN cycle proven (PIN redacted from evidence); plaintext PIN not stored;
   credential file is 0600 root:root.
10. **DND** — QS previously fell through to “unavailable”. Added persistent DND
    state; the notification daemon records suppressed notifications without
    deleting history. Live DND notification has
    `suppressed=true, suppression_reason=dnd`.
11. **Flashlight** — existing owner used; live `torch-sec1` 15→0 brightness cycle
    verified under the 60s policy.
12. **Colored LED** — no notification LED class. The provider reports
    `hardware_led=false` and requests a bounded edge-light from the single
    `nuxel-wl-fb` framebuffer owner. Direct `/dev/fb0` sampling proved red, green
    and blue borders and clean OFF.

## Live evidence (paths under `docs/beta-finalization/live/evidence/pwnage-45000/`)

- `baseline/live-baseline.txt` — kernel, UDC, configfs, packages, devices.
- `baseline/mtp-probe.txt` — initial MTP capability probe.
- `live/providers.txt` — live DND/NFC/fingerprint/security/LED/software status.
- `live/native-launch-evidence.txt` — Firefox/Nuxel Software visible; VLC/Signal
  truthfulness.
- `live/software-evidence.txt` — PackageKit/pkcon and Flatpak gate.
- `live/security-evidence.txt` — PIN/lock/unlock cycle.
- `live/led-framebuffer-evidence.txt` — physical framebuffer colour samples.
- `live/mtp-composition-evidence.txt` — acm+mtp composition and safe restore.
- `tests/pwnage45000-run-all.txt` — 291 PASS / 0 FAIL.
- `live/journal-tail.txt` — service/launch journal.
- `live/post-reboot.txt`, `live/post-reboot-launch.txt`, `live/final-state.txt` — final reboot/session verification.
- `live/pwa-url-check.txt` — all 26 registered PWA entry URLs return HTTP 200.

## Physical acceptance

Verified live over SSH and on the real handset:

- native dock running at 360x62 logical, scale 2, with regenerated art;
- Firefox visible (`app_id=org.mozilla.firefox`);
- Nuxel Software visible (`app_id=nuxel-software`);
- DND suppression/history;
- torch ON/OFF on `torch-sec1`;
- red/green/blue edge-light and OFF from `/dev/fb0`;
- USB CDC-ACM remains present and MTP composition/responder becomes ready when
  File Transfer is selected.

Not physically provable in this run:

- MTP host enumeration and bidirectional SHA-256 copy (no USB data host/cable);
- NFC tag UID (kernel `CONFIG_NFC` off);
- fingerprint enrollment (no secure provider);
- polkit graphical prompt (no logind session in the root-owned Phoc session);
- VLC window (Fedora VLC Qt GUI module fails to register in the module bank).

## Security notes

- No mass-storage export, no raw block writes, no bootloader operations.
- MTP root restricted to `/home/nuxel/Shared`; dotfiles/symlinks escaping it are
  never exposed.
- No Flatpak sandbox weakening, no `--no-sandbox`, no host filesystem grant.
- No raw biometric template handling.
- Credentials never logged; PIN/pattern verifier uses scrypt and 0600 storage.
- NuxTore remains local/offline and continues to verify signed bundles.
- PWA launch arguments remain registry-resolved; no client-supplied Exec/path.

## Follow-up pass: lockscreen top bar + full Podman rebuild

The active top bar on this image is the native A45 layer-shell `nuxel-statusbar`,
not only the DOM bar. The follow-up changed the native binary to read the
authoritative `/run/nuxel/security/lock-state.json` every second. While locked it
destroys its overlay layer surface (so no 36 px exclusive zone or pixels cover
the lockscreen); on unlock it recreates it. Missing/unreadable state is treated
as locked (fail closed). The DOM fallback is also hidden with
`body.lockscreen-active .status-bar { display:none !important; }`. PWA cache was
bumped to `v71-p45001`.

Live proof (SSH): `STATUSBAR_SHOWN locked=0 → STATUSBAR_HIDDEN locked=1 →
STATUSBAR_SHOWN locked=0`; a compositor screenshot with the lock overlay present
is saved at `evidence/pwnage-45000/screenshots/lockscreen-no-topbar-p45001.png`.

A clean ARM64 Fedora 43 rootfs was rebuilt with Podman from
`images/s10plus/build-phone-rootfs-fedora.sh` in container `nuxel-build-45001`.
The resulting 4 GiB ext4 image passed `e2fsck -fn` and the offline rootfs
verifier. Three real build-integration bugs were fixed along the way:

1. `gen-navdock-art.py` resolved its repository root as `/` when copied into the
   build staging tree, so the build aborted on missing artwork. It now discovers
   the root (including `/nuxel`) and the build skips writes to source fallbacks.
2. `openssl` was missing from the builder host tool set, so RDP credential
   generation aborted after a successful package transaction.
3. gid 3003 (`inet`) was created after `usermod -aG inet nuxel-remote`; it is now
   created before any supplementary-group lookup.

The image is `build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-p45001.img`
(sha256 `4f91d673e2e46528acb1ddc029c819140832d1e4bfb0c8f8588ebb89af89e1e1`).
Only the affected userspace files were deployed over the existing SSH path; the
rootfs image was not raw-flashed.


Follow-up regression: **300 PASS / 0 FAIL** (`tests/pwnage45000/run-all.sh`, captured at
`evidence/pwnage-45000/tests/pwnage45001-run-all.txt`).

The handset was rebooted after deployment. Post-reboot: SSH returned, kernel
`4.14.253-gf7194c1d15ed-dirty`, all five core units active, the deployed hashes
match, the PWA serves `v71-p45001`, and the native status bar starts hidden
(`STATUSBAR_START_HIDDEN locked=1`).
