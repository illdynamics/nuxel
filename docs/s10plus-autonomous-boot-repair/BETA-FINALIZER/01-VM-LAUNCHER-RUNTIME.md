# 01 — THE WORKING UTM VM LAUNCHER RUNTIME (measured live, cycle A31)

Access path used: `utmctl ip-address nuxel-aarch64-phosh` → `192.168.64.3`,
then `ssh nuxel@192.168.64.3`. The podman/gvproxy cross-build path was **not**
used anywhere in this cycle (measured unstable on this host, A29) — the VM is the
build channel, because it is Fedora 43 aarch64 with the same ABI as the handset.

```
utmctl list                      -> 711988C4-…  started  nuxel-aarch64-phosh
utmctl status nuxel-aarch64-phosh -> started
utmctl ip-address                 -> 192.168.64.3
ssh nuxel@192.168.64.3 uname -r   -> 6.17.1-300.fc43.aarch64

systemctl list-units '*nuxel*'
  nuxel-bridge.service          active running  Nuxel Bridge D-Bus Permission Broker
  nuxel-http-bridge.service     active running  Nuxel HTTP Bridge API
  nuxel-notifications.service   active running  Nuxel Notification Hub
  nuxel-portal.service          active running  Nuxel Portal Daemon
  nuxel-web.service             active running  Nuxel PWA Static Web Server (nuxel-home launcher on :8000)
  nuxel-home-kiosk.service      disabled        (launcher is opened in-session)
  nuxel-home-native.service     disabled        (GTK4 twin, starts with an ImportError)

ss -lntp
  127.0.0.1:8000  python3 (nuxel-web: the PWA static server / docroot)
  127.0.0.1:8080  nuxel-http-bridge

/var/lib/nuxel/.api-token         ABSENT  (dev mode: per-session tokens via POST /api/v1/auth/token)
```

The launcher is the **Nuxel Home PWA** at `pwa/nuxel-home/`, served on
`127.0.0.1:8000` and rendered by **WebKitGTK 2.52.5** — the same engine family,
registry and CSS the S10+ port uses. The VM's `nuxel-web.service` docroot is the
repository root, which is why the launcher URL is `/pwa/nuxel-home/index.html`
and why `../nuxel-common/bridge.js` resolves.

Application registry (authority): `pwa/nuxel-home/js/apps.js` — 9 apps, 3 docked:

| id | name | type | url |
|---|---|---|---|
| nuxel-dialer | Phone | native | `nuxel-dialer://` |
| nuxel-messages | Messages | native | `nuxel-messages://` |
| nuxel-contacts | Contacts | native | `nuxel-contacts://` |
| org.nuxel.Mail | Mail | pwa | `/pwa/nuxel-apps/mail/index.html` |
| org.nuxel.Calendar | Calendar | pwa | `/pwa/nuxel-apps/calendar/index.html` |
| org.nuxel.Notes | Notes | pwa | `/pwa/nuxel-apps/notes/index.html` |
| org.nuxel.Files | Files | pwa | `/pwa/nuxel-apps/files/index.html` |
| nuxel-camera | Camera | native | `nuxel-camera://` |
| nuxel-settings | Settings | native | `nuxel-settings://` |

`js/apps.js launchApp()` → `_launchPwa()` (fullscreen iframe of the registry url)
or `_launchNative()` (`native:launch` event → custom `nuxel-…://` scheme).

**Conclusion carried into this cycle:** the S10+ must run *this* PWA, not a
re-implementation. It already does (see doc 02); what was broken were the asset
paths, the input path, the framebuffer handoff and the launch mode.
