# Baseline — PWNAGE-85000

## Identity

- Host: `192.168.178.167` (helper-pinned `10.20.30.16` unreachable; not trusted)
- Root: `id -u` = 0, `id -un` = root
- Device: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820
- OS: Fedora 43 ARM64
- Kernel: `4.14.253-gf7194c1d15ed-dirty` aarch64
- Repo: `/Users/wicked/x/nuxel`, HEAD `ac310d06`, branch `pwnage-80000`; working tree already dirty from prior sessions
- Session: Phoc/Wayland, `nuxel-wl-fb` sole `/dev/fb0` writer; resolution 720×1520 (source) → panel 1440×3040, scale 2

## Supplied/PWNAGE-84000 baseline

| Metric | Value |
|---|---:|
| Native GTK spawn | ≈0.48 s |
| Flatpak sandbox init | **30.7 s** (3 runs) |
| Flatpak failure mode | fixed post-context / D-Bus-proxy wait |
| Prewarm | enabled, did not resolve stall |

## Live reproduction before fixes

```text
systemd-run --wait --pipe --uid=nuxel ... flatpak run --command=true org.gnome.TextEditor
→ 15.94–15.99 s
→ F: Can't get document portal: GDBus.Error:org.freedesktop.DBus.Error.NoReply
  Message recipient disconnected from message bus without replying
```

```text
runuser -u nuxel -- xdg-document-portal
→ fuse: failed to open /dev/fuse: Permission denied
→ error: fuse init failed: Can't mount path /run/user/1000/doc
```

```text
busctl user org.a11y.Bus → NoReply (at-spi-bus-launcher disconnected)
/run/nuxel-wayland/at-spi was root:root 0700
```

```text
systemctl status <transient unit>
→ deactivating (stop-sigterm), TimeoutStopUSec=15s, cgroup empty
```

`flatpak --user list --app` through the same transient path: **≈16 s**. The provider's `is_installed()` runs that inventory on every launch. The reported 30.7 s is consistent with two 15 s waits.

## Baseline whole-device observations

| Metric | Value |
|---|---:|
| bridge API CPU | 13.1% |
| bridge helper CPU | 0.7% |
| repeated user-scope flatpak list jobs | 5 / ~20 s |
| `nuxel-pwa-host` `repaint` writes | 32 / 6 s |
| WebKit `ThreadedCompositor` thread (screen off) | 74.67% |
| WebKit main thread | ~18–20% |
| wl-fb state while off | `REPAINT_REQUEST` (display marker lost) |
| screen-off panel | `bl_power=4`, brightness 0 |
| thermal zones | 26.6–43.0 °C during session |
| battery | 11%, discharging |

## Preserved facts

- Phoc/Wayland, `nuxel-wl-fb`, `/dev/fb0`, touch, display sleep/wake, audio, clockd, soundd, microphone, Wi-Fi SSH and app state were not replaced.
- No kernel/bootloader/DTB/initramfs/partition change.
- No governor, thermal, zram or scheduler change.
- No Flatpak override, `--no-sandbox`, host filesystem grant or broad device grant was added.
