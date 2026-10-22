# NUXEL A53 — GNOME Software (RPM + Flatpak store)

## Gate status: `BLOCKED_NETWORK` + `BLOCKED_SESSION` (no dnf) — cannot install the store

The requested outcome — search/install/update/remove native RPM **and** Flatpak apps from the phone
UI — is blocked before it starts, for concrete, verified reasons:

1. **No package manager.** `dnf`, `dnf5`, `microdnf`, `PackageKit`/`pkcon` are all absent; only
   `rpm` exists. GNOME Software's PackageKit backend needs PackageKit (absent) and the Flatpak
   plugin needs Flatpak (absent).
2. **No network.** No UP interface, no route, no `usb0`; Wi-Fi PSK is owner-only. Nothing can be
   downloaded.
3. **Flatpak sandbox is kernel-blocked** regardless of network (`# CONFIG_USER_NS is not set`).

## On-device discovery (read-only)

```
# dnf info gnome-software PackageKit   -> dnf: MISSING
# rpm -q gnome-software PackageKit flatpak xdg-desktop-portal xdg-desktop-portal-gtk
  package gnome-software is not installed · package PackageKit is not installed
  package flatpak is not installed · xdg-desktop-portal(-gtk) not installed
```

## What was NOT done (per contract)

- No kernel flash to enable `CONFIG_USER_NS`.
- No raw `rpm --nodeps` database hacks to fake a store.
- No fake catalogue UI, no "store" screenshots with nonfunctional buttons.
- No sandbox weakening, no global SELinux/polkit disable.

## What would be required, in order, once the owner provides Wi-Fi

1. Bootstrap a package manager: download `dnf5`/`libdnf5` + deps RPMs over Wi-Fi and `rpm -ivh`
   them (chicken-and-egg — requires the network the owner holds).
2. `dnf install gnome-software` after `--assumeno` transaction preview (PackageKit, AppStream,
   flatpak-libs, libadwaita come with it).
3. Add Flathub only after transport + GPG trust are verified (`flatpak remote-add --if-not-exists
   flathub …`), keeping `aarch64` as the default arch.
4. A working graphical polkit auth agent for the Phoc session (none exists today).

## Verdict

- GNOME Software installed and displayed → **BLOCKED**.
- Real RPM install/launch/remove from store → **BLOCKED** (no store).
- Flatpak sandbox supported → **BLOCKED_KERNEL** (exact blocker recorded above).
- Real Flatpak install/launch/remove from store → **BLOCKED** (no sandbox, no store, no network).

These are reported honestly and are not converted into "PASS because the backend exists on some
other machine".
