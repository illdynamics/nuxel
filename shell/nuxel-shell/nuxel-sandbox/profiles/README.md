# Nuxel sandbox profiles (`/opt/nuxel/sandbox/<app-id>.json`)

One JSON profile per app. The launcher (`shell/nuxel-shell/nuxel-sandbox/sandbox.c`)
loads `<NUXEL_SANDBOX_DIR>/<app-id>.json`, falling back to the app registry
(`configs/nuxel/app-registry/app_registry.json`) when no profile is staged.

## Rules

* `default.json` is the fail-closed baseline: no network, no D-Bus, no devices,
  read-only `/usr`. A new app is measured against it, not against a copy of an
  existing app's profile.
* `pwa-template.json` (`template: true`) is the catalogue a PWA **may** request.
  Copying it does not grant anything; the launcher passes the granted subset.
* `capabilities` in a profile is what the app is **launched with**; the app
  registry's `capabilities` is what it may **request** and
  `default_capabilities` is what ships enabled. Granting less than declared is
  the expected direction. A profile that lists a capability the registry does
  not declare for that app is a drift bug and `verify-permissions.py` fails it.

## The honest part (measured on the S10+, not aspirational)

The device kernel is **Linux 4.14.253**. That decides what each field can do:

| Field | Reality on 4.14.253 |
|---|---|
| `landlock_rules` | **Not applied.** Landlock is mainline >= 5.13. `nuxel-sandbox` prints `LANDLOCK_UNAVAILABLE` and continues instead of refusing to launch. Path-level confinement for unprivileged apps does not exist here. |
| `network_policy` / `network_class` | Applied, but through the **cgroup v1 net_cls classid** match (`nft 'meta cgroup 0x...'`). The cgroupv2 `socket cgroupv2` matcher needs >= 5.13. |
| `seccomp_profile` | Applied (seccomp BPF + `no_new_privs` exist in 4.14). |
| `devices` | Advisory. DAC on the device node is the real boundary; seccomp can block `ioctl` but the kernel cannot deny `open()` for one app only without Landlock/AppArmor. |
| `dbus_access` | Enforced by the D-Bus policy + AppArmor **if** AppArmor is enabled in this kernel. Verify with `nuxel-security-audit.sh`; if the LSM is absent the profiles are inert and must be labelled that way. |
| `capabilities` (sms/call/camera/mic/location/...) | Userspace gates (portal) + DAC. Not a kernel boundary on 4.14. |

Every one of those statements is also machine-readable in
`../nuxel-permissions/capabilities.json` (fields `enforceable`,
`enforces_against`, `limitation`), which the GTK permission manager, the HTTP
API and `tools/s10plus/a33/verify-permissions.py` all read. Do not add a switch
anywhere that claims more than that file states.
