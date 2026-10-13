# Nuxel Flatpak PWA Runtime

This directory contains Flatpak manifests that build and package the Nuxel
production PWA runtime based on WebKitGTK.

## Runtime: `org.nuxel.Platform`

`org.nuxel.Platform.json` builds the hardened WebKitGTK (WebKitGTK-2.46.5)
shared platform runtime that every Nuxel PWA runs on top of. It also:

- Installs the shared bridge client to `/app/share/nuxel/bridge.js`
  (from `pwa/nuxel-common/bridge.js`).
- Builds and installs the `nuxel-pwa-launcher` binary.
- Installs hardened default PWA preferences under `/app/etc/nuxel-pwa.conf`.

### Building the runtime

WebKitGTK takes a long time to build. Run from this directory:

```sh
# Create the build dir once
mkdir -p ../flatpak-build-runtime

# Build the platform runtime extension
flatpak-builder \
    --repo=../flatpak-repo \
    --install-deps-from=flathub \
    --ccache \
    --force-clean \
    ../flatpak-build-runtime \
    org.nuxel.Platform.json
```

Then export the built runtime to a local repository:

```sh
flatpak build-update-repo ../flatpak-repo
```

## Application manifests

The app manifests (`org.nuxel.Calendar.json`, `org.nuxel.Mail.json`,
`org.nuxel.Home.json`) declare `runtime: org.nuxel.Platform` and package each
PWA's static assets plus a launcher shell script into a Flatpak app.

### Building and installing an app

```sh
flatpak-builder \
    --repo=../flatpak-repo \
    --install-deps-from=flathub \
    ../flatpak-build-app-calendar \
    org.nuxel.Calendar.json

flatpak install ../flatpak-repo org.nuxel.Calendar
```

Launch a PWA with:

```sh
flatpak run org.nuxel.Calendar
```

## Prerequisites

- `flatpak-builder` and `flatpak` installed
- Flathub remote configured: `flatpak remote-add --user flathub https://flathub.org/repo/flathub.flatpakrepo`
- Network access to download the WebKit sources and GNOME SDK

## Notes

- WebKit is pinned to a real release tag (`WebKitGTK-2.46.5`) rather than
  `HEAD` for reproducible builds.
- Each PWA gets an isolated WebKitGTK web context (separate storage, cookies,
  and ServiceWorker registrations); no shared browser state.
