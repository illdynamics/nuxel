# Service Hardening

This document describes the hardening applied to the local HTTP services that
back the PWA runtime on the device:

- `nuxel-web.service` — the static PWA web server (serves the PWA bundle).
- `nuxel-http-bridge.service` — the HTTP→D-Bus bridge REST API the PWA calls
  for capabilities and system services.

Both services are **localhost-only** and strictly confined. The token-auth and
CORS policies below define how the HTTP bridge API authenticates PWAs and which
origins may call it.

## Localhost-only bindings

Neither service is exposed on the network.

- `nuxel-web.service` binds exclusively to `127.0.0.1:8000`:
  ```ini
  ExecStart=/usr/bin/python3 -m http.server 8000 --bind 127.0.0.1
  RestrictAddressFamilies=AF_INET AF_INET6
  ```
- `nuxel-http-bridge.service` binds exclusively to `127.0.0.1:8080` via the
  `NUXEL_HTTP_BIND=127.0.0.1` environment variable and `NUXEL_HTTP_PORT=8080`.
  Its `RestrictAddressFamilies=AF_INET AF_UNIX` allows only IPv4/IPv6 and the
  local Unix socket needed for D-Bus.

The bridge API source defaults to `127.0.0.1` (`NUXEL_HTTP_BIND`) so even a
misconfigured unit cannot listen on all interfaces by default.

## `nuxel-web.service` directives

`services/nuxel-web.service` applies the following hardening:

| Directive | Value | Purpose |
|-----------|-------|---------|
| `ProtectSystem` | `strict` | The entire filesystem hierarchy is read-only except explicitly allowed paths. |
| `ProtectHome` | `yes` | `/home`, `/root`, and `/run/user` are inaccessible. |
| `PrivateTmp` | `yes` | Private `/tmp` and `/var/tmp`. |
| `PrivateDevices` | `yes` | No access to physical devices. |
| `NoNewPrivileges` | `yes` | Blocks privilege escalation via `execve` and setuid/setgid. |
| `RestrictAddressFamilies` | `AF_INET AF_INET6` | No raw packet / other address families. |
| `ReadOnlyPaths` | `/` | Whole root mounted read-only. |
| `ReadWritePaths` | `%h/nuxel` | The PWA bundle directory is kept writable (e.g. for service-managed updates); the static server itself only reads it. |

The unit serves the PWA on `127.0.0.1:8000` and does not need write access to
the home directory, so `ProtectHome=yes` is applied even though
`%h/nuxel` is granted as a read-write path.

## `nuxel-http-bridge.service` directives

`services/nuxel-bridge/systemd/nuxel-http-bridge.service` applies the following
hardening:

| Directive | Value | Purpose |
|-----------|-------|---------|
| `ProtectSystem` | `strict` | Read-only root. |
| `ProtectHome` | `yes` | Home directories inaccessible. |
| `PrivateTmp` | `yes` | Private `/tmp`. |
| `PrivateDevices` | `yes` | No physical device access. |
| `NoNewPrivileges` | `yes` | Blocks privilege escalation. |
| `RestrictAddressFamilies` | `AF_INET AF_UNIX` | Only TCP listener + D-Bus socket. |
| `ReadOnlyPaths` | `/` | Whole root read-only. |
| `ReadWritePaths` | `/var/lib/nuxel /var/log/nuxel` | Token read/write and logging only. |

The bridge unit runs as the unprivileged `nuxel-bridge` user and group, runs
with `PrivateTmp=yes`, and can only write under `/var/lib/nuxel` (token
storage, e.g. `/var/lib/nuxel/http-bridge/token`) and `/var/log/nuxel`.

## Token auth model

The HTTP bridge API (`services/nuxel-bridge/src/api.py`) authenticates every
endpoint except the bootstrap endpoint:

1. **Bootstrap (not auth-gated):** a PWA with no token calls
   `POST /api/v1/auth/token` with `{"app_id": "<app-id>"}`. The API mints a
   random per-session token, records it in the in-process `SESSION_TOKENS`
   registry with an expiry (default TTL 1 hour), and returns it in the JSON
   body.
2. **Authenticated calls:** every other `/api/v1/*` route requires an
   `Authorization: Bearer <token>` header. `_verify_auth()` accepts a token
   only if it is a live entry in `SESSION_TOKENS` (not expired) **or** it
   exactly matches the static `server_token` provisioned for the daemon. There
   is no "accept any non-empty token" bypass; every non-bootstrap endpoint
   strictly requires a valid token in all modes (`dev` and `prod`).
3. **Unauthorized requests** return HTTP `401` with the JSON body
   `{"error": "unauthorized"}` (lowercase per the API contract).

The shared bridge client (`pwa/nuxel-common/bridge.js`) resolves a token in
this order: `window.__NUXEL_TOKEN__` (native launcher injection), the local
token file `/var/lib/nuxel/.api-token`, `localStorage`, and finally the
`POST /api/v1/auth/token` bootstrap. It then uses the token for `/api/v1/ping`,
`/api/v1/capabilities`, and `POST /api/v1/rpc` calls.

## CORS policy

The bridge API reflects only explicitly allowed origins — it **never** returns a
wildcard `Access-Control-Allow-Origin: *`.

`NUXEL_API_ALLOW_ORIGIN` is the **source of truth** for the allowlist and is
honored in **both** `dev` and `prod` modes. It is a comma-separated list, for
example:

```ini
NUXEL_API_ALLOW_ORIGIN=http://127.0.0.1:8000,http://localhost:8000
```

Behavior:

- If the request `Origin` header exactly matches an entry in
  `NUXEL_API_ALLOW_ORIGIN`, that exact origin is echoed in
  `Access-Control-Allow-Origin`.
- If the `Origin` is not on the allowlist, **no** `Access-Control-Allow-Origin`
  header is emitted, so the browser blocks the cross-origin response.
- This applies to all HTTP methods, including `OPTIONS` preflight and
  non-`GET`/`POST` requests; there is no permissive fallback.

The systemd unit sets this environment variable (dev and prod deploy alike):

```ini
Environment=NUXEL_API_ALLOW_ORIGIN=http://127.0.0.1:8000,http://localhost:8000
```

### Dev vs production

- **Dev mode** (`NUXEL_HTTP_MODE=dev`): per-session tokens are issued on demand
  via `/api/v1/auth/token`; an existing static token file is still honored. CORS
  is still restricted to the `NUXEL_API_ALLOW_ORIGIN` allowlist — there is no
  `*` allowance.
- **Production mode** (`NUXEL_HTTP_MODE=prod`): a static token file
  (`/var/lib/nuxel/http-bridge/token`) is required at startup and used as the
  `server_token`; per-session tokens remain accepted. CORS is likewise
  restricted to `NUXEL_API_ALLOW_ORIGIN`.

## Verification

On the target device (systemd), validate both units:

```sh
systemd-analyze verify \
  services/nuxel-web.service \
  services/nuxel-bridge/systemd/nuxel-http-bridge.service
```

Exercise the auth + CORS contract:

```sh
# Bootstrap token
TOKEN=$(curl -s -X POST http://127.0.0.1:8080/api/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"org.nuxel.Platform"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')

# Authenticated ping
curl -s http://127.0.0.1:8080/api/v1/ping \
  -H "Authorization: Bearer $TOKEN"

# Unauthenticated request must be 401 with {"error":"unauthorized"}
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/api/v1/ping

# Allowed origin is reflected exactly (no *)
curl -s -D - -o /dev/null http://127.0.0.1:8080/api/v1/ping \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Origin: http://127.0.0.1:8000' | grep -i access-control

# Disallowed origin gets no Access-Control-Allow-Origin header
curl -s -D - -o /dev/null http://127.0.0.1:8080/api/v1/ping \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Origin: http://evil.example' | grep -i access-control || echo 'no ACAO header'
```
