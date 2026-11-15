# First-party location capabilities

The handset image has **no `systemd --user` / PhoshAgent**, so the portal's
interactive consent dialog cannot run there.  The system surfaces that the owner
operates directly therefore receive explicit, auditable grants:

| App id | Capability | Why |
|---|---|---|
| `org.nuxel.Home` | `location:manage` | the Location Quick Setting controls the global privacy/provider policy |
| `org.nuxel.Home` | `location:read` | Home may display the provider state |
| `nuxel-settings` | `location:manage` / `location:read` | Settings → Location & Maps diagnostics and the explicit "Request a real fix" action |
| `org.nuxel.Maps` | `location:read` | draw the live-location marker after the owner taps the locate button |
| `org.nuxel.Maps` | `location:manage` | enable the global location policy before requesting its own position; revocable per app in Settings → Permissions → Location control |

These files also preserve the existing first-party `network:manage` and
`bluetooth:manage` session grants for Home/Settings.  They are read by
`nuxel-bridge` from `/var/lib/nuxel/permissions/*.json` at startup.  A grant is
**not** a fix: the global policy still has to be enabled, the provider still has
to answer, and the provider must return real coordinates.

### Store ownership (reboot-safe)

The live grant store is shared by root-owned `permD` (writer / reviewer) and the
unprivileged `nuxel-bridge` (enforcer).  Grant records must therefore be
`root:nuxel-bridge 0640` (or readable by the same group).  `nuxel-bridge.service`
checks this on every start with an `ExecStartPre` one-way repair (adds group read
only; it never widens access to other users), and `permD` writes new records in
that form.  A root-only `0600` file is a real boot bug: it makes `permD` say
"allowed" while the bridge enforces a capability denial.

Read and control are separate delegates of the one `location` resource.  The
store keeps a `delegate_of` allow record for `location:read`/`location:manage`,
plus an exact-token `decision: deny` record when the owner revokes one toggle.
This prevents granting Maps control from silently erasing Maps location-read
(or the reverse).  The Settings → Permissions view offers **Location** and
**Location control** as separate per-app switches.

Rollback: restore the pre-deployment copies under
`/var/lib/nuxel/a72/rollback-fast-*/` and restart `nuxel-bridge`.
