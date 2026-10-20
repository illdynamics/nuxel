# Owner physical confirmation — Nuxel v0.6.3-beta (S10+)

**Status: PENDING — no physical PASS is claimed.**  
**Deployed:** 2026-10-20, userspace only, no flash/partition/kernel/modem/firmware write.  
**Live webroot:** `/usr/share/nuxel`  
**Rollback if a change fails:** `sh /var/backups/nuxel/v0.6.3-beta-pre-20261020T123441Z/rollback.sh`

Please run this as a **90-second PASS/FAIL test** on the phone. Reply with the
item number and PASS or FAIL; add one short note for any FAIL. Do not mark audio
PASS unless you actually hear it.

## 90-second checklist

| # | Test | Expected | Owner result |
|---|---|---|---|
| 1 | Look at Home’s bottom Back/Home/Recents dock and the app shortcut dock | BG2 pixel-art background is visible on both; icons remain visible | PENDING |
| 2 | Open Home Settings → dock background; tap **BG1**, then **BG2** | Both docks visibly change to the selected artwork; no blank dock | PENDING |
| 3 | Tap Phone, Contacts, Settings, Browser icons | Each responds and opens (or visibly starts opening) | PENDING |
| 4 | Pinch outward/inward on an empty part of Home | Home does **not** zoom or scale | PENDING |
| 5 | Swipe upward starting in the **bottom half** of Home (not on the dock) | All Apps opens; swipe up again | PENDING |
| 6 | Swipe up again after All Apps | Settings opens (or the next drawer stage) | PENDING |
| 7 | Swipe from the **upper half** of Home | Quick Settings expands; gesture again collapses/closes it | PENDING |
| 8 | Settings → Wi-Fi: tap **Scan** | Real AP list appears (e.g. Snoerbreuk, WPA2); the software test already returned 11 APs | PENDING |
| 9 | Select an AP and enter its password **on the phone** | Association completes; do not send the password here | PENDING |
| 10 | After join, check DHCP/DNS and open a real HTTPS page in Browser | Phone gets an address, DNS resolves, HTTPS page loads | PENDING |
| 11 | All Apps → Browser | Browser opens locally; report whether an external HTTPS page loads | PENDING |
| 12 | Audio: play the Nuxel cue / speaker test | Any audible speaker sound? | PENDING (expected silent: ABOX `calliope_sram.bin` missing) |

## Reply format

```text
1 PASS  2 PASS  3 PASS  4 PASS  5 PASS  6 PASS  7 PASS
8 PASS  9 PASS/FAIL  10 PASS/FAIL  11 PASS/FAIL  12 PASS/FAIL
Notes: <only for FAIL or surprising behavior>
```

## What is already machine-verified (not a physical claim)

- Payload SHA256 and all 19 files verified locally and on the phone.
- 21 installed paths re-hashed after deploy; all match.
- `/pwa/nuxel-home/index.html`, `launcher.css`, both dock images, Settings,
  `wifi-settings.js`, Browser route and app registry all return HTTP 200.
- WebKit reloaded and requested the dock assets with `?v=0.6.3-beta` (200).
- `nuxel-bridge` and `nuxel-http-bridge` are active; `/api/v1/ping`,
  `/api/v1/health`, `/api/v1/apps/registry` return 200.
- Wi-Fi radio is enabled and a real scan returned 12 APs.
- Audio: ABOX/Calliope firmware load fails (`calliope_sram.bin`,
  `calliope_sram_2.bin`, `vts.bin`, error -2); `SPEAKER` and `bias_level` are Off;
  no UCM2 profile or ALSA/PipeWire playback tool exists. This is a blocker, not a
  PASS.
