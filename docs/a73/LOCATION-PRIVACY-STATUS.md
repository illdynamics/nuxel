# NUXEL A73 — Location Privacy Status (honest)

> **Update (PWNAGE 27000):** the state model, provider failure reporting,
> first-party grants, D-Bus policy and Maps tile pipeline were repaired in
> `docs/pwnage-27000/GPS-MAPS-REPORT.md`. This document remains as the A73
> design record; where it says “no fix” for an unavailable provider, the newer
> state is `unavailable`.

## Design
The Location Quick Setting is a **global permission/provider policy** switch,
deliberately decoupled from whether a GNSS satellite fix exists.

- `enabled`/`permission_enabled` — the global policy (persistent, survives
  reboot). OFF denies new position requests and marks any stale fix invalid;
  ON re-allows consented reads.
- `provider_ready` — GeoClue/authorised provider is connected and usable.
- `location_fix_available` / `fix_source` / `fix_timestamp` / `accuracy` — the
  actual last fix, reported **only** when a real provider yields coordinates.
- GNSS hardware presence is reported separately and is never a fix claim.

Policy file: `/var/lib/nuxel/permissions/location-policy.json` (atomic write,
bridge-writable). Capability `location:manage` is portal-gated.

## Live readback (deployed bridge)
```
enabled: false            (privacy-safe default)
provider: geoclue2
provider_ready: false     (geoclue.service auto-stops when idle)
location_fix_available: false
fix_source: null
gnss: present (ssp_sensorhub/ssp_data_injection/bbd_sensor), fix_supported: false
```

Set-enabled round trip verified **both ways** on-device:
- `set-enabled true` → `{success:true, enabled:true, permission_enabled:true}`
- `set-enabled false` → `{success:true, enabled:false, …}`
- persisted across a bridge restart (fresh process read the stored policy).

## Enforcement
- `GetLocation` (the old `location.status` path used by Maps) now returns
  `LOCATION_DISABLED` before any coordinate read when the policy is OFF, and
  still requires the `location:read` capability when ON.
- GeoClue (`geoclue.service`) is the only provider and auto-stops when idle;
  no IP→GNSS substitution, no fabricated lat/lon anywhere.

## Limits (stated, not hidden)
- With no GNSS userspace provider wired, `location_fix_available` stays false;
  the tile shows "Location · no fix" while ON — the policy is still ON, which is
  the correct semantic.
- The bridge runs as `nuxel-bridge` (`PrivateDevices=true`); `/dev/ssp_*` and
  `/dev/ttyBCM` are root-only. PWNAGE 27000 therefore also reports the bound
  BCM GPS SPI device from sysfs (`present:true`, `node_visible_to_bridge:false`)
  instead of under-reporting the hardware as absent. See
  `docs/pwnage-27000/GPS-MAPS-REPORT.md`.
- Complete system-wide privacy is bounded by the provider surface: any client
  that can reach GeoClue outside the bridge would need its own D-Bus policy
  review; the bridge-side denial is the enforced path for Nuxel PWAs.

## Maps integration
Maps' boot probe calls `location.status` (now policy-gated) and its locate
button currently focuses manual coordinate entry — it never manufactures a
position. With the policy ON and a future real fix it would report it; with OFF
or no fix it degrades to the manual path gracefully.
