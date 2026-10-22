# A51 — Flatpak ARM64 Readiness

## Verdict: `FLATPAK_SANDBOX_BLOCKED_BY_KERNEL`

Flatpak cannot run a sandbox on this handset because the Samsung vendor kernel
(4.14.253) was built **without user namespaces**.

## Evidence (live, non-destructive)
```
# zcat /proc/config.gz | grep -E 'CONFIG_USER_NS|CONFIG_SECCOMP'
# CONFIG_USER_NS is not set
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y

# unshare -U true
unshare: unshare failed: Invalid argument

# unshare -U -m -p -f --mount-proc true
unshare: unshare failed: Invalid argument

# bwrap --unshare-user --unshare-ipc --unshare-pid --unshare-net --ro-bind / / --dev /dev --proc /proc -- /bin/sh -c 'echo OK'
bwrap: Creating new namespace failed, likely because the kernel does not support user namespaces.
```

`bubblewrap 0.12.0` is installed, but without `CONFIG_USER_NS` it cannot create
the user/mount namespaces Flatpak relies on. The mission forbids a kernel
replacement, so this is a hard blocker, not something to work around with
`--no-sandbox`/`--filesystem=host` (explicitly out of scope and unsafe).

## Package state
- `flatpak`: **not installed** (as the historical `nuxtore-and-flatpak.md` finding predicted).
- `xdg-desktop-portal`, `xdg-desktop-portal-gtk`: **not installed**.
- `bubblewrap`: installed (sandbox primitive present, but blocked by kernel).

## What would still be required even with a kernel fix
1. `dnf install flatpak xdg-desktop-portal xdg-desktop-portal-gtk` after viewing
   the exact planned transaction (excludes kernel/firmware/display-stack).
2. `flatpak --default-arch` must report `aarch64`; add the canonical Flathub
   remote only after transport + GPG trust are checked.
3. A real published AArch64 GUI Flatpak (not every app has an arm64 build)
   installed and run as the unprivileged GUI user, with portal features
   verified under Phoc (Phoc itself may lack the desktop portal backend the
   portals need — another gap to document then).

## Remediation
A future image/kernel with `CONFIG_USER_NS=y` (owner-authorised, out of scope
for this mission) would unblock the sandbox; the repo's Flatpak manifests
(`pwa/flatpak/`) remain staged for that day. Native RPM apps and the WebKitGTK
browser path remain usable **without** Flatpak.
