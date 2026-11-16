# NUXEL A53 — Flatpak Sandbox & Portals

## Gate status: `BLOCKED_KERNEL` (user namespaces) — no sandbox can start

Fresh live evidence on today's boot:

```
# zcat /proc/config.gz | grep -E 'CONFIG_USER_NS|CONFIG_SECCOMP|CONFIG_PID_NS|CONFIG_NET_NS'
# CONFIG_USER_NS is not set
CONFIG_PID_NS=y
CONFIG_NET_NS=y
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y

# unshare -U true
unshare: unshare failed: Invalid argument            (rc=1)

# bwrap --unshare-user --ro-bind / / --proc /proc --dev /dev -- /bin/sh -c 'echo OK'
bwrap: Creating new namespace failed, likely because the kernel does not support user namespaces. (rc=1)
```

(`/proc/sys/user/max_user_namespaces` exists with value `27231`, but the kernel was built without
`CONFIG_USER_NS`, so that knob is non-functional.)

Flatpak requires user/mount namespaces for its sandbox. Without `CONFIG_USER_NS` the sandbox
cannot be created. The mission explicitly forbids a kernel replacement and forbids
`--no-sandbox`/`--filesystem=host`/`--device=all` workarounds. **This is a hard, honest blocker.**

## Package state (observed)

- `flatpak`: **not installed**. `xdg-desktop-portal` / `xdg-desktop-portal-gtk`: **not installed**.
- `bubblewrap-0.12.0-1.fc43.aarch64` installed (the primitive exists; the kernel feature does not).
- `flatpak --default-arch`, remotes, installations: not runnable (binary absent).

## Portals / PipeWire / polkit (observed)

- `xdg-desktop-portal` and `xdg-desktop-portal-gtk`: absent → no FileChooser/OpenURI/screencast portal.
- `pipewire`/`wireplumber`: absent → no camera/screencast/audio portal backends.
- `polkit-126`: present, but no graphical auth agent is wired into the Phoc session.
- A52's `org.nuxel.Camera` remains a **private** broker; it does **not** claim
  `org.freedesktop.portal.Camera`.

## Minimal safe future remediation (separate mission)

A kernel built with `CONFIG_USER_NS=y` (owner-authorised) would unblock the sandbox; then
`dnf install flatpak xdg-desktop-portal xdg-desktop-portal-gtk` after a transaction preview. The
repo's `pwa/flatpak/` manifests remain staged for that day. Native RPM apps remain usable without
Flatpak.
