# A51 — Final Status (G1–G5)

| Gate | Verdict | Evidence |
|---|---|---|
| **G1 Wi-Fi** | **PASS (fix) / physical join pending owner** | Root cause traced to live `bridge.py` `/new`; replaced with verified-AP activation + profile reuse/autoconnect + stale-scan guard; deployed & hash-verified; scan returns full AP identity; bogus-AP test returns clean `stale_scan`. Owner PSK entry + reboot autoconnect remain owner-only. |
| **G2 GUI** | **PARTIAL (native GTK4 launches)** | `adwaita-1-demo` (GTK4) ran on the physical Phoc/Wayland display until a bounded timeout (rc 143 = SIGTERM). GTK3+GTK4 present. Qt6 absent. Touch/OSK lifecycle needs physical confirmation. |
| **G3 Flatpak** | **BLOCKED (kernel)** | `FLATPAK_SANDBOX_BLOCKED_BY_KERNEL`: `CONFIG_USER_NS is not set`; `unshare -U` → `Invalid argument`; `bwrap` → "kernel does not support user namespaces". flatpak/portals not installed. |
| **G4 Ladybird** | **BLOCKED** | No network, no Qt6, no gcc/clang/rust/nasm on-device. Exact blockers + AArch64 build continuation in LADYBIRD-AARCH64-BUILD.md. |
| **G5 Browser fallback** | **PARTIAL** | WebKitGTK runtime present and already rendering (Home). Epiphany not installed; install requires the network the Wi-Fi fix provides. |

## Non-negotiable result
The Wi-Fi root cause is **fixed and deployed**; the final "press Connect →
internet → browser → reboot autoconnect" sequence requires the owner to enter
the PSK once and approve a reboot. Every downstream gate (browser install,
Flatpak, Ladybird) is gated on that first real connection, and Flatpak is
additionally gated on a kernel `CONFIG_USER_NS` change that this mission
forbids.

## Honest remaining blockers (not assumed success)
1. **Owner PSK entry** → completes G1 physical join + HTTPS + browser + reboot.
2. **No network until (1)** → blocks `dnf install epiphany` (G5) and any
   Qt6/Ladybird fetch (G4).
3. **Kernel lacks `CONFIG_USER_NS`** → Flatpak sandbox impossible without a
   forbidden kernel change (G3).

No PSK was requested, guessed, leaked, or stored. No flashing, kernel
replacement, sandbox bypass, or password leak occurred. Existing Home, native
OSK, Wi-Fi scanning, lockscreen, USB console, and A50 tuning remain unchanged.
