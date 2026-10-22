# A55 Browser Packages — Firefox / Chromium / Chrome / Ladybird

## Hard blocker (external resource): no package manager on the phone
Live verification: `dnf`, `dnf5`, `microdnf`, and `flatpak` are all **absent**.
Only `rpm` 6.0.2 is present. On-device dependency resolution for a signed Fedora
aarch64 RPM set is therefore not possible this cycle without first installing a
package manager (itself blocked on the same dependency-resolution bootstrap).

## Per-browser status (honest)
| Browser | Status | Evidence |
|---|---|---|
| Firefox (Fedora ARM64 RPM) | **BLOCKED_EXTERNAL_RESOURCE** | `firefox` absent; no dnf/flatpak to resolve + install aarch64 RPM set |
| Chromium (Fedora ARM64 RPM) | **BLOCKED_EXTERNAL_RESOURCE** | `chromium` absent; same package-manager blocker |
| Google Chrome (official ARM64 RPM) | **BLOCKED_EXTERNAL_RESOURCE** | no vendor RPM present; cannot retrieve+verify official RPM without package tooling; no x86_64 mislabel |
| Ladybird (pre-alpha engine) | **BLOCKED_EXTERNAL_RESOURCE / TOOLCHAIN** | no upstream AArch64 build; device has no compiler (no gcc/make); cross-build + Qt6 sysroot exceeds this session's safe scope |
| Epiphany (WebKitGTK fallback) | **BLOCKED_EXTERNAL_RESOURCE** | `epiphany` absent; same package-manager blocker |

## What IS working now (not a substitute, but the honest default)
- `nuxel-browser-native` (this cycle): genuine top-level WebKitGTK browser,
  loads `https://www.google.nl` + `https://example.org` (see NUXEL-BROWSER.md).
- The WebKitGTK runtime (webkit2gtk4.1 + webkitgtk6.0, GTK3/GTK4) is present and
  the WebProcess/NetworkProcess sandbox spawns correctly for webkit2gtk-4.1.

## Follow-on (exact, once network+package tooling are available)
1. Install `dnf5` (or `dnf`) from Fedora 43 aarch64 repo with its RPM set.
2. `dnf5 --assumeno install firefox chromium epiphany` to preview, then apply.
3. Chrome: fetch the official Google-hosted ARM64 RPM, verify its signature/arch
   (`rpm -qp --qf '%{ARCH}'` must be `aarch64`), then install. No third-party repack.
4. Ladybird: build with an AArch64 cross-toolchain + Qt6 sysroot on a host; verify
   every binary with `file`/`readelf`; install under a separate prefix + desktop entry.
5. No `--no-sandbox`/`--disable-web-security`/`--ignore-certificate-errors` under
   any circumstances.
