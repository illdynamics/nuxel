# APP-INFRASTRUCTURE — canonical registry, bridge, portal, notifications, web server

**Component:** Priority 4 — Full Fedora userspace, services & application infrastructure
**BriQ:** `briq-04c-app-infrastructure`
**Verifier:** `python3 tools/s10plus/a33/verify-app-registry.py`
**Verdict:** `OFFLINE_TESTED_WITH_DEFERRALS` (0 problems; the deferrals are app
trees owned by other groups that have not landed yet — see §5)
**Evidence:** `build/pkgmeta/app-registry.json`, the test files in §6
**Revision 2 (cycle 6)** closed the four gaps this document used to describe as
work in progress: the registry's dangling `tree_apps` entry (a hard `FAILED`
verdict) is now a declared `planned` state, the missing activation path is
implemented and mediated (§3.2), the static web server is a real PWA server with
service-worker and cache policy (§3.3), and the client exposes the same contract
(`bridge.js` `activateApp`/`recentActivations`, §2).

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
arbitrate, a `pwa/nuxel-apps/<dir>` that ships an `index.html` and is documented
nowhere, or a `tree_apps` entry WITH a present-state (`complete`,
`in_progress`, `shared-assets-not-an-app`) whose directory is not on disk.

### 1.1 `tree_apps` states: a present claim must be true, a promise is labelled

Revision 2 replaced an ambiguous boolean ("documented") with four explicit
states, because the registry used to claim a directory that did not exist:

| State | Meaning | Verifier behaviour |
|---|---|---|
| `complete` | installed, `index.html` + `manifest.json` present | the directory **must** exist or the verdict is `FAILED` |
| `in_progress` | the owning group is landing it in this cycle | the directory must exist; a missing `index.html` is reported, not a failure |
| `shared-assets-not-an-app` | `pwa/nuxel-apps/_shared` | must exist; never a launcher entry |
| `planned` | declared and owned, **not landed yet** | the directory must **not** exist yet; while absent the entry is a printed `DEFER` naming the owning group and its ledger briq, and it is promoted automatically (reported as LANDED) when the tree appears |

That is what keeps the inventory from going stale in either direction: a
present-state entry that points at nothing fails closed, and a promise is never
counted as an app.

### 1.2 `required_apps_not_yet_in_tree`: the mission inventory, cross-checked

The mission names apps that have no tree directory at all yet (Permissions &
Privacy, Firewall, VPN/Tor/remote access, Security auditor, System monitor).
Guessing directory names for them would make the verifier report paths that will
never exist, so they are recorded **concept-level** with no path claim - and the
entry is not a free-text promise: each names its owning build group and its
`ledger_briq`, and the verifier fails if
`docs/beta-finalization/workqueue/<briq>.json` does not exist or if that briq's
`component` is not the `owner_group` the registry claims. A mission requirement
therefore cannot point at work nobody owns.

### 1.3 Why `registry_version` stays 4 in this revision

`tree_apps`, `required_apps_not_yet_in_tree` and `notes` are INVENTORY sections:
they do not change `apps[]` or a single app URL, so bumping
`NUXEL_REGISTRY_VERSION` in `pwa/nuxel-home/js/apps.js` (owned by the Priority 2
group) would be a false signal - and the verifier treats registry-version drift
as a failure. The version moves when the app grid moves.

## 2. bridge_version pinning (no silent version skew)

`pwa/nuxel-common/bridge-version.json` is the pin:

| Field | Value | Meaning |
|---|---|---|
| `bridge_version` | `1` | PWA↔host **protocol** contract. Every app manifest declares it as `nuxel.bridge_version`. |
| `host_version` | `0.5.2-beta` | implementation version of `nuxel-bridge` / `nuxel-http-bridge`; free to move without touching manifests. |
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
  `NUXEL_BRIDGE_VERSION=0.5.2-beta`, so `systemctl show -p Environment` shows
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
  Two defects in this path were fixed and are now regression-tested
  (`tools/s10plus/a33/tests/test-web-server.py`, which starts the real shim and
  speaks HTTP to it):

  1. **A resolved-but-wrong docroot was served anyway.** An explicit
     `NUXEL_WEBROOT` that contained no launcher index started a server that
     answered `/` with a listing and 404'd the launcher — the measured A29b blank
     WebKit view, with a unit that reported success. The shim now verifies that
     the resolved docroot actually contains `pwa/nuxel-home/index.html` (or the
     flat `nuxel-home/index.html`) and exits non-zero with the path in the
     message otherwise, so the failure lands in `systemctl status` instead of in
     a blank screen.
  2. **`/etc/nuxel/web.conf` was inert.** The builder writes
     `NUXEL_WEBROOT` / `NUXEL_WEB_PORT` / `NUXEL_WEB_BIND` there, but the unit
     never loaded it, so the documented override did nothing and the shim always
     fell back to probing. `nuxel-web.service` now carries
     `EnvironmentFile=-/etc/nuxel/web.conf` (optional, so VM/dev hosts still
     work) and the test asserts the builder consumes what it writes.

  The interpreter is natively `/usr/bin/python3` (from the `python3` RPM); the
  shim accepts `NUXEL_WEB_PYTHON` only so this offline test can run the identical
  code path on a host whose python3 lives elsewhere. The unit does **not** set
  it.

### 3.2 Launcher → app activation (the mediated launch path)

The launcher resolves an app id to an activation **descriptor** through the
privileged service, so app identity is decided in exactly one place:

```
Nuxel Home (WebKit/WebKitGTK)                     native PWA host (non-Web process)
  appRegistry.launchApp(id)                         parses app:launch / pwa:open / native:launch
    └─> POST /api/v1/apps/activate  ────────────────> WebKit navigation to the registry url,
        {app_id: caller, target: id}                   or exec of the registry's native_binary
        <── {action: navigate|exec|pending_app_tree|documented_placeholder,
             url|native_binary, launchable, executed:false, source:"registry"}
```

| Property | Implementation | Why it matters |
|---|---|---|
| the registry is the only source of the descriptor | `_activate_app()` builds `url` / `native_binary` from `app-registry.json`, never from the request | a client-supplied `binary`, `command`, `url` or `path` is ignored by construction, so "activate an app" cannot become "run an arbitrary program" (asserted by the test) |
| no execution primitive exists | the handler contains no `subprocess`, `os.system`, `popen`, `os.exec*`, `exec(`, `eval(` or `shell=True`; the test greps the handler body | the bridge resolves; the launch happens in the native host |
| an id is an identifier, never a path | `^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$` checked *before* any lookup → `400 invalid_app_id` | traversal, absolute paths and shell metacharacters are refused before they can be resolved |
| an unknown id is refused | `404 unknown_app` (+ `registry_version`) | nothing is guessed; the launcher shows an honest "unknown app" |
| an unavailable registry is reported | `503 registry_unavailable` with the source path and reason | an absent registry never becomes a fabricated app list |
| a declared-but-unlanded app is not "launchable" | `resolution: "pending"` → `launchable:false`, `action:"pending_app_tree"`, owners + reason | navigating to a 404 is not a launch (LiveConsole is the live example) |
| a native placeholder is honest | no `native_binary` → `launchable:false`, `action:"documented_placeholder"` + the registry's own note | `nuxel-camera` is not reported as a working camera |
| activity is observable, bounded | `ACTIVATION_HISTORY` (cap 20) + refusal counter, read through `GET /api/v1/apps/recent`; refusals are counted, not recorded as launches | the Live Console app's activity view needs the data the bridge already has |

The client half lives in `pwa/nuxel-common/bridge.js` (`activateApp(target,
source)`, `recentActivations()`), and `_request()` now attaches the refusal
reason (`err.code` = `unknown_app` / `invalid_app_id` / `registry_unavailable`)
to the thrown error instead of losing it in `"bridge HTTP 404"`, so a UI can
distinguish the states. Covered by
`services/nuxel-bridge/test-launcher-activation.py` (real handler + real
registry, every app id, refusal cases, no-execution assertions, launcher wiring)
and `pwa/nuxel-common/test-bridge.js`.

### 3.3 The static server is a real PWA server (revision 2)

`python3 -m http.server` was replaced by
`services/nuxel-web/bin/nuxel-web-server.py` (installed to
`/usr/lib/nuxel/nuxel-web-server.py`), because a development file server cannot
provide the four things this tree needs. The shim still owns docroot resolution
and verification and hands the verified root to the server, so there is one
root-resolution rule; if the server file is missing the shim falls back to
`-m http.server` **with a warning** rather than failing to start.

| Property | Policy | Why |
|---|---|---|
| MIME | explicit table (`.webmanifest`/`manifest.json` → `application/manifest+json`, `.js`/`.mjs` → `text/javascript`, `.wasm`, fonts, media) + `X-Content-Type-Options: nosniff` | an installable manifest and an ES module must not depend on a changing stdlib guess |
| service worker | `Cache-Control: no-cache` + `Service-Worker-Allowed: /` + `X-Nuxel-Service-Worker: 1` for `sw.js` | a stale service worker is the classic "the launcher runs old JavaScript" defect: the browser must revalidate, and the worker may claim the root scope it registers for |
| HTML/manifests | `no-cache` | an update check must not be masked by a cached shell |
| content-addressed assets | `Cache-Control: public, max-age=31536000, immutable` when the URL carries `?v=`/`?h=`/`?hash=`/`?ver=` | the URL changes with the content, so a long cache is safe and the launcher loads fast |
| everything else | `public, max-age=3600` | bounded staleness rather than browser-invented policy |
| revalidation | `ETag` (sha256[:16]) + `Last-Modified` on every 200, `304` for `If-None-Match`/`If-Modified-Since`, `HEAD` supported | the CI smoke test's "sw.js cacheable (validator)" check passes with a real validator |
| troubleshooting | `NUXEL_WEB_NO_CACHE=1` → `no-store` everywhere | the owner's stale-asset switch, no code change |
| listings | `/` and any directory → `403`, never a listing | a directory listing of the staged tree is an information leak, not a convenience |
| traversal | every path is `realpath`-resolved and must stay under the docroot; `..`, encoded `..` and symlink escapes are refused | `python3 -m http.server` already refuses these; the replacement must not regress it |
| throughput | `ThreadingHTTPServer` | WebKit opens several connections per page; a single-threaded server serialises them behind one slow request |
| journal | successful requests are not logged; refusals are | the journal is a diagnostic channel, not a request log |

Every row above is asserted by `tools/s10plus/a33/tests/test-web-server.py`
against the real shim over HTTP - including the `304`s, the traversal attempts
and the "successful requests are silent" property - so the policy is verified
rather than described.

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
| `pwa/nuxel-home/manifest.json` declares `nuxel.bridge_version: 0.5.2-beta` | bg-02 | **warn**: that is `host_version`, not the protocol pin. The launcher is a system surface and is not part of `apps[]`, so nothing is rejected — but the two fields must not be conflated. |
| 20 app directories in `pwa/nuxel-apps/` | bg-06 / bg-07 / bg-05 | inventoried in `tree_apps` with owner + state; an `index.html` that appears without a registry entry or an inventory note fails the verifier. |
| `pwa/nuxel-apps/privacy` | bg-05 (`briq-05a-permission-manager`) | **deferred** (`planned`, not landed — the previous revision wrongly claimed it existed and the verifier failed on it; that FAILED verdict is what this revision fixes). |
| Permissions & Privacy, Firewall, VPN/Tor/remote, Security auditor, System monitor | bg-05 / bg-06 | **pending** in `required_apps_not_yet_in_tree`: concept-level, with owner + ledger briq cross-checked against `docs/beta-finalization/workqueue/`. No tree path is claimed. |

Run `--strict` once every group has merged: a deferral or gap is then a hard
failure, which is the release gate.

## 6. Tests (all offline, no bus, no hardware)

```sh
python3 tools/s10plus/a33/verify-app-registry.py            # registry/launcher/manifest/pin
python3 tools/s10plus/a33/verify-app-registry.py --strict    # release gate
python3 services/nuxel-portal/test-portal-policy.py          # grant store + timeout invariants
python3 services/nuxel-notifications/test-notifications-persistence.py
python3 tools/s10plus/a33/tests/test-app-infrastructure.py   # real HTTP handler: pin, 409, registry
python3 services/nuxel-bridge/test-launcher-activation.py     # registry -> activation descriptor, refusals, no execution
python3 tools/s10plus/a33/tests/test-web-server.py           # static PWA server: docroot, MIME, SW headers, cache policy, 304, traversal
node pwa/nuxel-common/test-bridge.js                         # client pin + refusal semantics
node pwa/nuxel-common/verify-wiring.js                       # shared bridge module wiring
bash tools/s10plus/a33/tests/run-userspace-tests.sh          # all of Priority 4 (04a/04b/04c)
```

## 7. Honest limits

* A green registry is bookkeeping evidence: it proves the app set is consistent
  and every entry resolves to real files. It is **not** evidence that an app's
  hardware path works (`NEEDS_OWNER_TEST` for anything requiring a SIM, a finger,
  a camera or a speaker).
* `bridge_version` mismatch handling is proven against a real HTTP server with a
  stub D-Bus. On the handset the same handler runs with the real bus; the
  semantics are identical, but the on-device run is bg-10's measurement.
* The static server and the activation endpoint are `OFFLINE_TESTED` here and
  `IMPLEMENTED_NOT_DEPLOYED` on the handset: the builder installs them and the
  tests run the real code, but nothing in this component deploys to the phone
  (that is bg-10's live step) and no flashing of any kind is performed or
  required.
* The activation descriptor is a *resolution*, not a launch: the bridge proves
  which program or URL an id means, and the native PWA host performs it. Whether
  a launched app then works is the app's own evidence (and, for anything needing
  a finger, a SIM or a speaker, `NEEDS_OWNER_TEST`).
