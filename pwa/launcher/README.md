# Nuxel PWA Launcher

`nuxel-pwa-launcher` runs each PWA in an isolated, hardened WebKitGTK webview
and implements the PWA install/uninstall lifecycle.

## Build

```sh
meson setup build && meson compile -C build
# Requires: webkitgtk-6.0>=2.44, gtk4>=4.14, json-glib-1.0>=1.8
```

## Usage (normal boot)

```sh
NUXXEL_APP_ID=org.nuxel.Calendar \
NUXXEL_DATA_DIR=/var/app/org.nuxel.Calendar/data \
NUXXEL_MANIFEST_PATH=/app/share/nuxel-pwa/manifest.json \
NUXXEL_BRIDGE_SOCKET=/run/nuxel/bridge/org.nuxel.Calendar.sock \
nuxel-pwa-launcher
```

Each PWA gets an isolated `WebKitWebsiteDataManager`, so storage, cookies and
ServiceWorker registrations are never shared between apps.

## Lifecycle CLI

The launcher accepts three lifecycle subcommands:

```sh
# Install a PWA from its manifest.json
nuxel-pwa-launcher --install /path/to/manifest.json

# Uninstall a PWA (removes the Flatpak app and wipes its data)
nuxel-pwa-launcher --uninstall org.nuxel.Calendar

# Wipe a PWA's data without uninstalling it
nuxel-pwa-launcher --wipe-data org.nuxel.Calendar
```

`--install` parses the web manifest, generates a Flatpak app manifest that uses
`org.nuxel.Platform` as its runtime, shows a real modal consent dialog for each
declared capability (aborting the install if any capability is denied), invokes
`flatpak-builder` then `flatpak install` to build/install the app, and writes the
app into the dynamic app registry. `--uninstall` invokes `flatpak uninstall`,
removes the app from the registry, and deletes its per-app data directory
(`~/.local/share/nuxel/apps/<app-id>`).


The registry path is not hardcoded: the launcher reads the `NUXXEL_REGISTRY_JSON`
environment variable if set, otherwise derives it from `NUXEL_APP_DIR` in
`/etc/nuxel/paths.conf`, and finally falls back to
`~/.local/share/nuxel/app_registry.json`. Flatpak build output and the repository
default to `~/.cache/nuxel/flatpak-build` and `~/.cache/nuxel/flatpak-repo`
(override the repo with `NUXXEL_FLATPAK_REPO`). The registry uses the same
`{ "version": ..., "apps": [...] }` shape consumed by
`shell/nuxel-home-native/nuxel_home/app_model.py` (`AppRegistry.add_app()` /
`AppRegistry.remove_app()`).


## Lifecycle states

| State        | Meaning                                                                 | Trigger                     |
| ------------ | ----------------------------------------------------------------------- | --------------------------- |
| uninstalled  | Not present in the Flatpak system or the app registry.                  | `flatpak uninstall` / launcher `--uninstall` |
| disabled     | Installed/data present but not launched (e.g. revoked capabilities).    | capability revocation / manual disable |
| enabled      | Installed and launchable in the default console UI.                     | `flatpak install` / launcher `--install` |
| installed    | Flatpak app + registry entry present, data directory may exist.         | launcher `--install`        |

Transition `enabled -> disabled` and back is driven by the capability
consent/revocation flow; `disabled -> uninstalled` requires removal of the app
and its data (`--uninstall`), and `--wipe-data` clears an app's data directory
while keeping the app installed.
