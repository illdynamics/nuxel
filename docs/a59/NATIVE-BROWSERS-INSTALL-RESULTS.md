# A59 — Native browser installation results (Firefox / Chromium / Ladybird)

All package checks and launches were performed ON THE S10+ (not the laptop).
The device has NO `dnf`/`dnf5`/`microdnf`/`pkcon` (only `/usr/sbin/rpm`), so
every package was downloaded as a signed Fedora aarch64 RPM from the official
Fedora 43 mirrors and installed with `rpm` after dependency review.

## Firefox — `INSTALLED`, `NETWORK_VERIFIED`, `BLOCKED_WAYLAND_WINDOW`
- Package: `firefox-157.0.1-1.fc43.aarch64` (signed Fedora updates repo).
- Dependencies resolved and installed:
  `mozilla-filesystem-1.9-36`, `fdk-aac-free-2.0.0-16`, `libvpx-1.15.0-4`,
  `pciutils-libs-3.15.0-1` (nspr/nss already present).
- Launch: `/usr/sbin/firefox --no-remote --profile … https://www.google.nl`
  under `MOZ_ENABLE_WAYLAND=1 GDK_BACKEND=wayland`.
- RESULT: Firefox's full process tree starts and runs (main + forkserver +
  `-isForBrowser … tab` + `rdd` content processes), and the tab content process
  loads the target page — real network/HTTPS was reached. The browser sandbox is
  active (sandboxReporter processes present; no `--no-sandbox`).
- BLOCKER: the main window does not map as a `zwlr_foreign_toplevel` toplevel
  under this `phoc --no-xwayland` headless+pixman compositor, so no Firefox
  window appears in the foreign-toplevel window list (only non-fatal warnings:
  `org.a11y.Bus` autolaunch without `$DISPLAY`, and `Sandbox: Couldn't open
  video device /dev/video251`). Status: `BLOCKED_WAYLAND`/`BLOCKED_GPU` for the
  visible window; `NETWORK_VERIFIED` for page load.

## Chromium — `PACKAGE_AVAILABLE`, `NOT_INSTALLED` (time-boxed)
- Package: `chromium-155.0.8059.84-1.fc43.aarch64` is available in the Fedora
  43 updates repo.
- NOT installed this session: like Firefox it has a non-trivial dependency tree
  to resolve manually without `dnf`, plus the vendor 4.14 kernel's user-namespace
  / seccomp / shared-memory sandbox primitives need an independent audit before
  a secure Chromium launch could be claimed. It was not forced with `--no-sandbox`.
- Status: `PACKAGE_AVAILABLE`, `NOT_TESTED` (safe next step: bootstrap `dnf5`
  first, then `dnf5 install chromium` with transaction preview).

## Ladybird — `UPSTREAM_PREALPHA`, `NOT_INSTALLED` (owner's preference)
- Not present in Fedora 43 repos (no signed `ladybird` aarch64 RPM).
- Ladybird is pre-alpha; a genuine AArch64 build requires a separate off-device
  build tree (clang + ~10s of minutes to hours of compilation) and no official
  Fedora binary exists. This was NOT faked as a browser; the working Nuxel
  Browser remains the stable browser milestone.
- Status: `UPSTREAM_PREALPHA` / `BLOCKED_PACKAGE_ARCH`.

## Per-browser summary
| Browser | Status |
|---|---|
| Nuxel Browser (custom) | `INSTALLED` + `LAUNCHES` + `NETWORK_VERIFIED` (PASS) |
| Firefox | `INSTALLED` + `NETWORK_VERIFIED`, window `BLOCKED_WAYLAND` |
| Chromium | `PACKAGE_AVAILABLE`, `NOT_INSTALLED` (dnf absent) |
| Ladybird | `UPSTREAM_PREALPHA`, `NOT_INSTALLED` |
| GNOME Web/Epiphany | `PACKAGE_AVAILABLE` (not installed this session) |

## Honesty
No `curl`-only PASS was recorded for any browser. Nuxel Browser's milestone is
backed by a committed/finished real HTTPS navigation in a genuine top-level
WebKitGTK view; Firefox's is backed by a real content-process page load but its
window-mapping blocker is reported explicitly rather than hidden.
