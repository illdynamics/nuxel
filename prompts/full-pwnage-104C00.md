# FULL-PWNAGE-104C00 — Permission manager and firewall: make them real and visible

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104C00.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

The permission manager (`nuxel-permd`, PWA apps under
`pwa/nuxel-apps/settings/apps-permissions-settings.js`) and the app firewall
(`configs/nftables/nuxel-app-firewall*.nft`, `nuxel-console-guard.nft`) must be
**enforcing and observable**: toggling a permission in the UI changes real
behaviour, denied network access is actually blocked, and the UI never shows a
permission as granted when the kernel says otherwise.

## 1. Baseline

```sh
$SSH $PHONE 'systemctl status nuxel-permd --no-pager; pgrep -af nuxel-permd'
$SSH $PHONE 'nft list ruleset 2>&1 | head -120'
$SSH $PHONE 'ls -la /var/lib/nuxel/permissions/ /etc/nuxel/permissions/ 2>&1'
```
`nuxel-permd` is running on `127.0.0.1:8765`. Note the nftables files in the repo
are currently modified/uncommitted — re-read them before trusting the live ruleset.

## 2. Work order

1. **Permission round-trip**: for each permission type (mic, camera, location,
   notifications, network), deny → verify the app fails to use the feature →
   grant → verify it works. Record API + UI + kernel-level evidence.
2. **Firewall**: create a test cgroup/app with no network permission; confirm
   nftables drops egress (and DNS), then grant and confirm it flows. Verify
   `nuxel-console-guard` is loaded and the app-firewall table is applied at boot
   (not only at runtime).
3. **UI truth**: the settings app must reflect `/var/lib/nuxel/permissions`
   state; fix any drift where toggles show stale state.
4. Persist across reboot and re-verify in §4.

## 3. Acceptance

- Deny actually denies (captured `nft` counters/logs + app error).
- Grant actually grants.
- Permission state persists across reboot; UI shows the truth.
- No default-allow regressions for existing working apps.
