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

These files also preserve the existing first-party `network:manage` and
`bluetooth:manage` session grants for Home/Settings.  They are read by
`nuxel-bridge` from `/var/lib/nuxel/permissions/*.json` at startup.  A grant is
**not** a fix: the global policy still has to be enabled, the provider still has
to answer, and the provider must return real coordinates.

Rollback: restore the pre-deployment copies under
`/var/lib/nuxel/a72/rollback-fast-*/` and restart `nuxel-bridge`.
