# Owner confirmation — A44 icon delivery

**Status: PENDING — no physical PASS is claimed.**  
**Device:** S10+ SM-G975F, Fedora 43 aarch64, kernel 4.14.253  
**Deployed:** 2026-10-20, userspace only, no flash/partition/kernel/reboot.  
**Rollback:** `sh /var/backups/nuxel/a44-icon-delivery-20261020T145655Z/rollback.sh`

Please run this on the phone and reply with PASS or FAIL per line.

| # | Test | Expected |
|---|---|---|
| 1 | Look at Home: app grid, four-shortcut dock, Back/Home/Recents bar | Supplied custom PNG icons are visible, sharp, not clipped, and each appears once |
| 2 | Swipe from the top to open Quick Settings; close; open again | Eight custom toggle icons are visible both times; no doubled, broken or stale images |
| 3 | Open Settings; return Home; open Browser; return Home | Each app opens; its launcher icon remains single and correct after switching |
| 4 | Press Home (or reload Home) | Icons remain single/correct; layout, wallpaper and dock preference are unchanged |
| 5 | Check Home layout/preferences/credentials before vs after | No user data loss |

Reply format:

```text
1 PASS/FAIL  2 PASS/FAIL  3 PASS/FAIL  4 PASS/FAIL  5 PASS/FAIL
Notes: <only for FAIL or surprising behavior>
```

Machine evidence already verified: all 23 registered URLs are 200 `image/png`
with source-equal SHA-256; WebKit decoded all 23; Quick Settings reopened twice
without duplicates; app switching kept one visible frame; v28 caches replaced
old namespaces; localStorage keys survived. Those are not a substitute for your
visual confirmation.
