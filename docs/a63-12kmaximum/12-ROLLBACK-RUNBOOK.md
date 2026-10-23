# A63 rollback runbook

Private host backup: `/home/wicked/nuxel-rescue/a63/20261023T120045+0200`.

Verified archives include pre-change Home code, SnekByte, `/etc/nuxel`, WebKit state and NetworkManager profiles. SHA-256 manifests remain in the private directory; saved-network material must stay private.

Live per-file backups use `.nuxel-a63-rollback` for the three Home scripts and web unit. The guarded deploy also retained `.nuxel-rollback` for metadata files. Restore only the affected explicit path, verify its hash, run `systemctl daemon-reload` for unit changes, then restart only `nuxel-web`. Do not recursively overwrite `/usr/share/nuxel`.

The original `/etc/group` is `/etc/group.nuxel-a63-rollback`. Restore it only as part of an immediate full A63 service rollback, after stopping `nuxel-web`, because later account changes would otherwise be lost. No reboot is required for userspace rollback. Never use these steps on partitions or boot media.
