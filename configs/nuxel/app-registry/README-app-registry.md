# Nuxel App Registry

> **Single source of truth for application registration.** The app registry is
> the one place a Nuxel app is introduced to the system. From it, the D-Bus
> bridge (`org.nuxel.Bridge`), the permission portal (`org.nuxel.Portal`), the
> sandbox launcher (`nuxel-sandbox`), and the per-app nftables firewall all
> derive app identity, capabilities and the **deterministic cgroup name**.

This is a *data + schema* deliverable (briq-se1). It does not replace the
per-app sandbox JSON profiles — those remain the sandbox's runtime tuning —
it is the **authoritative list** of which apps exist and their network class,
so that cgroup naming, nftables rules, portal grants and bridge registrations
cannot drift apart.

## Files

| File | Purpose |
|------|---------|
| `app_registry.json`       | The registry data (schema_version 1). |
| `app-registry.schema.json`| JSON-Schema (draft-07) documenting & validating `app_registry.json`. |
| `tools/app-registry-check.sh` | Validation + single-source enforcement script (also installed on device). |

## On-device location

The registry is shipped under `/etc/nuxel/app-registry/app_registry.json`
(root, read-only). At first boot the firstboot/`init` stage copies it to
`/var/lib/nuxel/app-registry/app_registry.json` (writable runtime copy) so
installed apps can register additional entries. All consumers read the runtime
copy after first boot, falling back to the read-only system copy when absent.

- System copy: `/etc/nuxel/app-registry/app_registry.json`
- Runtime copy: `/var/lib/nuxel/app-registry/app_registry.json`
- Override: `NUXEL_APP_REGISTRY` environment variable.

## Schema (version 1)

```jsonc
{
  "schema_version": 1,
  "generated": "2026-08-12T00:00:00Z",
  "path": "/etc/nuxel/app-registry/app_registry.json",
  "cgroup_rule": "socket cgroupv2 level 2 app-*",
  "apps": [ { "app_id": "...", "name": "...", "type": "native|pwa|system|template",
              "cgroup_name": "app-...", "network_class": "public|isolated|unspec",
              "capabilities": [...], "default_capabilities": [...], ... } ]
}
```

### Required fields (per app)

* **`app_id`** — primary key, unique. Used by bridge/portal permission grants
  (`/var/lib/nuxel/permissions/<app_id>.json`).
* **`name`** — human-readable launcher label.
* **`type`** — `native` (GTK4 C binary), `pwa` (WebKitGTK web app), `system`
  (system service, not sandboxed), `template` (reusable profile, not launchable).
* **`cgroup_name`** — deterministic cgroup under `/sys/fs/cgroup/nuxel/`. **Rule:
  it MUST equal the deterministic mapping of `app_id`** (lowercased, characters
  outside `[a-z0-9-]` → `-`, repeated `-` collapsed, leading/trailing `-`
  trimmed, prefixed `app-`). This is what guarantees the nftables
  `socket cgroupv2 level 2 "app-*"` match applies. `app-registry-check.sh`
  verifies this for every entry.
* **`network_class`** — `public` (nftables ACCEPT + socket() syscalls),
  `isolated` (default firewall drop), `unspec` (runtime flags).
* **`capabilities`** — requestable capabilities a user may grant via the portal.

### Optional fields

* `executable` (native), `launch_args`, `cgroup_classid` (legacy v1),
  `default_capabilities` (no-prompt), `data_dir`, `allowed_ro_paths`,
  `allowed_rw_paths`, `dbus_access`, `devices`, `memory_max_bytes`,
  `memory_high_bytes`, `network_policy` (field-level outbound policy),
  `enabled` (soft deregistration).

## Relationship to other components

| Consumer | Reads registry for | Field |
|----------|--------------------|-------|
| `nuxel-sandbox` (`sandbox.c`) | profile fallback when no JSON profile is staged; canonical cgroup name | `app_id`, `cgroup_name`, `network_class`, `capabilities`, `data_dir`, `dbus_access`, `devices`, `memory_*` |
| `nftables.sh` / `configs/nftables` | which cgroups exist and their network class → ACCEPT vs default-drop | `app_id`, `cgroup_name`, `network_class` |
| `org.nuxel.Bridge` (`bridge.py`) | the set of known apps and their capabilities | `app_id`, `capabilities`, `default_capabilities` |
| `org.nuxel.Portal` (`portal.py`) | which apps may be granted which capability | `app_id`, `capabilities` |

## Deterministic cgroup mapping

The mapping is implemented identically in three places and verified against the
registry by `app-registry-check.sh`:

* **C**: `nuxel_sandbox_app_id_to_cgroup()` in `sandbox.c`
* **Shell**: `sanitize_app_id()` in `nuxel-sandbox/nftables.sh`
* **Registry**: each entry's `cgroup_name` (must equal the mapping of `app_id`)

`Org.Nuxel.Mail` → `org-nuxel-mail` → `app-org-nuxel-mail`.
