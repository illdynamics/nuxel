# A51 — Ladybird AArch64 Build (pre-alpha) — BLOCKED, exact reasons

## Status: BLOCKED (not attempted to fake; no binary shipped)

Ladybird (https://github.com/LadybirdBrowser/ladybird) remains a **pre-alpha
developer browser**. Its current build requires (per upstream at the pinned era)
Qt **6.10+**, CMake **3.30+**, a C++23 toolchain, Rust, and nasm, with a
Qt-based frontend. None of these prerequisites exist on the live handset, and a
build host is unavailable over the live console.

## Live feasibility check (evidence)
| Requirement | Handset state | Verdict |
|---|---|---|
| Network to fetch source/deps | Wi-Fi not joined (owner PSK pending) | BLOCKED |
| Qt6 (`qt6-qtbase`, `qt6-qtwayland`) | **not installed** | BLOCKED |
| Compiler (`gcc`/`clang`) | **not installed** (only `pkgconf-pkg-config`) | BLOCKED |
| Rust/nasm/CMake 3.30+ | not installed | BLOCKED |
| Graphics backend (EGL/DRM) | no DRM device; software GL only | RISK |
| RAM | 7.2 GiB (marginal for a full C++ engine build) | RISK |

## Correct build path (continuation, once internet is up)
1. Build on a **Fedora AArch64 host or a proper AArch64 sysroot cross-build** —
   never copy an x86_64 Ladybird binary to the phone.
2. Pin a source revision; audit the exact commit's `Documentation/BuildInstructionsLadybird.md`
   for its current Qt/CMake/Rust/nasm/LLVM versions and any documented AArch64
   support or open issues.
3. Install Qt6 on the handset **only** if the build's runtime needs it and it is
   safe to add to the fragile image; keep dependencies isolated.
4. `file`/`readelf -h` + ABI + shared-library audit must confirm `AArch64`,
   compatible glibc, the Qt Wayland plugin, TLS CA bundle, fonts, and that
   **every Ladybird subprocess is also AArch64**.
5. Install as an isolated, reversible Nuxel package with its own `.desktop`
   entry and icon; do **not** overwrite the current Browser shortcut until live
   acceptance passes.

## Honest acceptance bar (must ALL pass before "preferred browser")
Own window through Phoc (not a WebKitGTK wrapper), HTTPS to `example.org` +
a second site with valid TLS, native OSK types into the address bar, Enter
navigates, Back/Home/close work, 2+ tabs if stable, no thermal runaway, profile
under a user-owned path, survives restart/reboot. Label it pre-alpha and keep a
reliable fallback.

## Immediate conclusion
Ladybird is **not installable or runnable on the handset today**; the blocker is
concrete and reproducible (no network, no Qt6, no toolchain). Deliver G5
(WebKitGTK fallback) so real browsing works first, then pursue this build on a
proper AArch64 host.
