# nuxel-bridge first-party seed grants

Read-only seed records installed to `/usr/share/nuxel/permissions/`.  A seed
only fills an app that has no record in the owner-writable store; an explicit
grant, deny or revoke always wins.  Only `system_inspect` (the canonical id for
read-only diagnostics) is seeded here.  No write capability, microphone,
location or broker authority is seeded.
