# APP-INFRASTRUCTURE — canonical registry, bridge, portal, notifications, web server

**Component:** Priority 4 — Full Fedora userspace, services & application infrastructure
**BriQ:** `briq-04c-app-infrastructure`
**Verifier:** `python3 tools/s10plus/a33/verify-app-registry.py`
**Verdict:** `OFFLINE_TESTED_WITH_DEFERRALS` (0 problems; the deferral is a
cross-group app tree that has not landed yet — see §5)
**Evidence:** `build/pkgmeta/app-registry.json`, the two test files in §6

---

## 1. One registry, three consumers, no drift

```
pwa/nuxel-common/app-registry.json          ← CANONICAL (registry_version 4)
   ├── pwa/nuxel-home/js/apps.js             PWA launcher grid   (read-only check)
   ├── shell/nuxel-home-native/nuxel_home/app_registry.json   native shell (rendered)
   ├── services/nuxel-bridge/src/api.py      GET /api/v1/apps/registry
   └── /etc/nuxel/app-registry/app_registry.json   installed copy (rootfs builder)
```

`verify-app-registry.py` fails on any of: a missing/extra app in the launcher, a
URL or type that differs between the registry and `apps.js`, a native-shell copy
that is out of sync, a `registry_version` mismatch, a PWA entry that does not
resolve to a real `index.html` + `manifest.json`, a manifest whose
`nuxel.bridge_version` differs from the pin, a capability the bridge cannot
arbitrate, or a `pwa/nuxel-apps/<dir>` that ships an `index.html` and is
documented nowhere.

## 2. bridge_version pinning (no silent version skew)

`pwa/nuxel-common/bridge-version.json` is the pin:

| Field | Value | Meaning |
|---|---|---|
| `bridge_version` | `1` | PWA↔host **protocol** contract. Every app manifest declares it as `nuxel.bridge_version`. |
| `host_version` | `0.4.0-alpha` | implementation version of `nuxel-bridge` / `nuxel-http-bridge`; free to move without touching manifests. |
| `policy` | `reject-on-mismatch` | enforced on both sides. |
| `http_header` | `X-Nuxel-Bridge-Version` | what the PWA client sends. |

Enforcement, measured offline:

* `pwa/nuxel-common/bridge.js` exports `NUXEL_BRIDGE_VERSION = '1'`, sends the
  header on every request, cross-checks the pin file, and on a mismatching (or
  *undeclared*) host `bridge_version` sets `versionMismatch`, logs a hard error,
  emits `bridge:version-mismatch`, and **throws `NuxelBridgeVersionError` from
  `call()`**. It does **not** fall back to mock data: a version skew is not an
  availability problem, and mock data would make a skewed app look healthy.
* `services/nuxel-bridge/src/api.py` publishes `bridge_version` on
  `/api/v1/health` and `/api/v1/ping`, and answers **409 `version_mismatch`**
  (with `expected`/`got`) to any request whose `X-Nuxel-Bridge-Version` differs.
  A client that sends no header is a documented legacy client and is served.
* `services/nuxel-bridge/src/bridge.py` publishes `BridgeVersion` / `HostVersion`
  D-Bus properties and includes `bridge_version` in `Ping()` JSON.
* The systemd units pin `NUXEL_BRIDGE_PROTOCOL_VERSION=1` and
  `NUXEL_BRIDGE_VERSION=0.4.0-alpha`, so `systemctl show -p Environment` shows
  exactly what is enforced. The verifier asserts all four places agree.

## 3. The bridge and the static server

* `nuxel-bridge` (`org.nuxel.Bridge`) is the capability mediator. Its
  `SendNotification` path calls the notification hub, which is why
  `nuxel-notifications.service` now starts **before** `nuxel-bridge.service`
  (the previous revision had both orders declared — an ordering cycle; see
  `SERVICE-GRAPH.md` §3).
* `nuxel-http-bridge` serves `/api/v1/*` on `127.0.0.1:8080` for PWAs that cannot
  use D-Bus. It serves the canonical registry at `/api/v1/apps/registry` from
  `NUXEL_APP_REGISTRY` (installed as `/etc/nuxel/app-registry/app_registry.json`).
  An absent or malformed registry is reported as `available:false` with the
  resolved path and the reason — never replaced by an invented app list.
* `nuxel-web` serves the **repository root** on `127.0.0.1:8000`, so
  `/pwa/nuxel-home/index.html` finds `../nuxel-common/bridge.js` (enforced by
  `pwa/nuxel-common/verify-wiring.js`) and every app is addressed as
  `/pwa/nuxel-apps/<app>/index.html`. The launcher is never staged flat.

## 4. Portal and notifications

* `nuxel-portal` (`org.nuxel.Portal`) mediates every hardware permission through
  a user-consent dialog on the **session** bus (`org.nuxel.PhoshAgent`), running
  as user `nuxel`. Grants are persisted per app and per portal type with
  durations `once` / `session` / `always`; a `once` grant is consumed on first
  check; a request with no answer inside `NUXEL_PORTAL_TIMEOUT_SECONDS` (30) is
  **denied**, and that window is deliberately shorter than the bridge's D-Bus
  timeout (90) so a real verdict is produced instead of a timeout masked as a
  failure. Every portal type carries a declared risk level
  (low/medium/high) — there is no unlabelled capability. No AppArmor profile is
  declared, because Nuxel cannot provably enforce one on this kernel.
* `nuxel-notifications` (`org.nuxel.Notifications`) persists history to the
  canonical `/var/lib/nuxel/notifications.json` with a bounded cap
  (`NUXEL_NOTIFICATIONS_HISTORY_CAP=200`) and monotonic ids across restarts.

## 5. Deferrals and cross-group gaps (visible, never silent)

Reported by the verifier as `DEFER` / `WARN`, and fatal under `--strict`:

| Item | Owner | Status |
|---|---|---|
| `org.nuxel.LiveConsole` (launcher grid revision 4 → `/pwa/nuxel-apps/console/index.html`) | bg-02 (grid) / bg-07 (app tree) | **deferred**: the app tree has no `index.html`/`manifest.json` yet in this cycle. The launcher entry is real; the surface is not. |
| `pwa/nuxel-apps/settings/manifest.json` has no `nuxel{}` block | bg-02 / bg-06 | **warn**: capabilities + `bridge_version` are recorded in the canonical registry instead; the manifest must gain the block. |
| `pwa/nuxel-apps/{mail,calendar}.manifest.json` declare `storage:read` / `storage:write`; `terminal` declares `shell:local-pty` | bg-06 | **warn**: these ids are not in `services/nuxel-bridge/src/capabilities.py` (`storage:persistent` is the enum entry). An app must not advertise a capability the host cannot arbitrate — documented in the registry's `capability_gaps`, not hidden. |
| `pwa/nuxel-home/manifest.json` declares `nuxel.bridge_version: 0.4.0-alpha` | bg-02 | **warn**: that is `host_version`, not the protocol pin. The launcher is a system surface and is not part of `apps[]`, so nothing is rejected — but the two fields must not be conflated. |
| 20 app directories in `pwa/nuxel-apps/` | bg-06 / bg-07 / bg-05 | inventoried in `tree_apps` with owner + state; an `index.html` that appears without a registry entry or an inventory note fails the verifier. |

Run `--strict` once every group has merged: a deferral or gap is then a hard
failure, which is the release gate.

## 6. Tests (all offline, no bus, no hardware)

```sh
python3 tools/s10plus/a33/verify-app-registry.py            # registry/launcher/manifest/pin
python3 tools/s10plus/a33/verify-app-registry.py --strict    # release gate
python3 services/nuxel-portal/test-portal-policy.py          # grant store + timeout invariants
python3 services/nuxel-notifications/test-notifications-persistence.py
python3 tools/s10plus/a33/tests/test-app-infrastructure.py   # real HTTP handler: pin, 409, registry
node pwa/nuxel-common/test-bridge.js                         # client pin + refusal semantics
node pwa/nuxel-common/verify-wiring.js                       # shared bridge module wiring
```

## 7. Honest limits

* A green registry is bookkeeping evidence: it proves the app set is consistent
  and every entry resolves to real files. It is **not** evidence that an app's
  hardware path works (`NEEDS_OWNER_TEST` for anything requiring a SIM, a finger,
  a camera or a speaker).
* `bridge_version` mismatch handling is proven against a real HTTP server with a
  stub D-Bus. On the handset the same handler runs with the real bus; the
  semantics are identical, but the on-device run is bg-10's measurement.
* Nothing here is deployed to the phone by this component. No flashing of any
  kind is performed or required.
