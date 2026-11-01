# PWNAGE-45000 — feature ledger

Target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), kernel
`4.14.253-gf7194c1d15ed-dirty`, Nuxel/Fedora 43 aarch64.

Status vocabulary: **DONE** (source + tests + live proof), **DONE-NEEDS-OWNER**
(source/tests + device proof incomplete), **BLOCKED_*** (real hardware/kernel
dependency), **NOT_SUPPORTED_ON_DEVICE**.

| # | Feature | Status | Evidence / blocker |
|---|---------|--------|--------------------|
| 1 | Lockscreen order Charging→Live→USB + larger/lower transports | DONE | DOM order verified; CSS row 286px/56px; `tests/pwnage45000`; responsive landscape 44px |
| 2 | USB MTP + CDC-ACM | DONE-NEEDS-OWNER | Kernel `CONFIG_USB_F_MTP=y`; responder at `/usr/lib/nuxel/nuxel-mtp-server`; configfs staged `acm.usb0`+`mtp.gs0`; `/dev/mtp_usb` created; responder opened `/home/nuxel/Shared`; host cable/enumeration/copy not available in this run |
| 3 | Native Software center | DONE with polkit blocker | `/usr/lib/nuxel/nuxel-software` GTK3 + `pkcon`/PackageKit DNF backend; visible surface verified. GNOME Software 49 SIGSEGV → not used. Flatpak blocked (`CONFIG_USER_NS=n`). Graphical polkit agent cannot obtain a logind subject in the current root-owned Phoc session → privileged prompts need a future logind/session change |
| 4 | Native app launch | DONE (Firefox), truthful failure (VLC/Signal) | Firefox `/usr/bin/firefox` visible, `surface_seen=true`, toplevel `org.mozilla.firefox`; XDG_RUNTIME_DIR corrected to `/run/nuxel-wayland`; socket group-writable. VLC Qt interface module fails to load → bridge returns `exited_before_surface` + journal. Signal `unsupported_on_device` (no aarch64 RPM; Flatpak blocked) |
| 5 | NuXTore registry/lifecycle | DONE | Canonical registry 40 apps; alias `org.nuxel.NuxTore→org.nuxel.Nuxtore`; Bridge `apps/{inventory,reconcile,register,unregister}`; install commits only after registration; remove preserves payload/user data; live unregister/register round-trip proven |
| 6 | NFC | BLOCKED_KERNEL | `# CONFIG_NFC is not set`; I2C 0x27 hint present, no kernel NFC class/dev node; provider + Settings/topbar report blocker, no fake ON; tag test disabled |
| 7 | Fingerprint | BLOCKED_SECURE_PROVIDER | qbt2000 driver and `/dev/qbt2000_{fd,ipc}` detected; no verified TEE/fprintd provider; no templates imported/exported; enrollment/test disabled |
| 8 | Security lock | DONE | scrypt verifier (2^14/8/1), salt, 0600 root credential, constant-time compare, persistent lockout; Bridge blocks native launches while locked (`423 session_locked`); PIN→wrong→correct→swipe cycle proven; Home PIN/pattern prompt implemented |
| 9 | DND | DONE | Persistent `/var/lib/nuxel/notifications/dnd.json`; live toggle; notification stored with `suppressed=true, suppression_reason=dnd`; QS/Settings wired; critical/alarm exceptions |
| 10 | Flashlight | DONE | `torch-sec1`, real brightness 15→0; 60s policy owner; camera/thermal guards; QS wired |
| 11 | Colored notification LED | DONE (truthful fallback) | No notification LED class → `hardware_led=false`; display edge-light via the single `nuxel-wl-fb` owner; framebuffer sampled red/green/blue and clean OFF |
| 12 | Native navdock art | DONE | Alpha-aware generator crops transparent padding, normalizes 44px content, regenerates `navdock-art.h`, writes 96px DOM fallbacks; native dock rebuilt and running |
| 13 | Build/rootfs integration | SOURCE DONE, IMAGE BUILD BLOCKED | Builder includes new modules/configs/packages and syntax-checks; clean image build not run here because the Docker daemon is unavailable |
| 14 | Physical reboot/deploy | DONE | Files deployed with backup at `/var/lib/nuxel/pwnage45000-backup-20261031T182512Z`; device reboot performed; see deployment record |

## Known blockers

- **USB host enumeration**: no USB data cable/host attached during this run. Kernel
  function, configfs composition, `/dev/mtp_usb`, responder and restricted root
  are proven; physical host copy remains `NEEDS_OWNER_TEST`.
- **VLC visible UI**: Fedora 43 `vlc-gui-qt` loads (plugin listed) but the VLC
  3.0.24 module bank reports "no suitable interface module"; VLC falls back to
  its CLI and exits. The bridge now reports this instead of a fake success.
- **Graphical polkit**: PackageKit/pkcon work; the root-owned Phoc session has no
  logind session, so xfce-polkit cannot register a valid polkit subject. A native
  RPM transaction that requires auth will fail until Nuxel runs a logind/PAM
  session. No authorization bypass was added.
- **Flatpak**: `CONFIG_USER_NS` unset, `unshare -U` fails.
- **NFC**: kernel built without `CONFIG_NFC`.
- **Fingerprint**: no usable secure/TEE userspace provider.

## Follow-up (2026-10-31, PWNAGE-45001 UI/build pass)

| Item | Status | Evidence |
|---|---|---|
| Lockscreen top bar removed | DONE | Native `nuxel-statusbar` tears down its layer surface while `lock-state.json` is locked and recreates it on unlock; DOM fallback has `body.lockscreen-active .status-bar { display:none }`. Live state transitions SHOWN→HIDDEN→SHOWN and screenshot in `evidence/pwnage-45000/live/topbar-lockscreen-followup.txt`. |
| Full ARM64 rootfs rebuild on Podman | DONE | `fedora:43` linux/arm64 container `nuxel-build-45001`; image `build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-p45001.img`, sha256 `4f91d673…e1e1`; e2fsck and offline verification PASS. |
| Build reproducibility repairs | DONE | navdock generator resolves `/nuxel` when copied into the build tree; source fallbacks are not mutated during image builds; builder deps include `openssl`; gid 3003 exists before `usermod`. |
| Live deploy + reboot | DONE | Userspace delta deployed with backup `/var/lib/nuxel/pwnage45000-followup-20261031T191613Z`; device rebooted, SSH returned, all five core units active, post-reboot lockscreen has no top bar. Evidence: `evidence/pwnage-45000/live/post-reboot-topbar-followup.txt`. |
