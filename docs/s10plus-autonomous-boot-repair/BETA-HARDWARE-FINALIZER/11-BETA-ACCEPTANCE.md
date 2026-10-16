# 11 — BETA ACCEPTANCE (what is proven, what is not)

Legend: **[I]** implemented · **[O]** offline-tested · **[D]** deployed · **[H]** tested on
the physical phone · **[U]** confirmed by the user · **[X]** not working / not claimed.

| Item | I | O | D | H | U | Note |
|---|---|---|---|---|---|---|
| Touchscreen driver present after a normal boot | ✓ | – | ✓ | ✓ | – | `input: sec_touchscreen`, `PROP=2`, IRQ 431 |
| Touchscreen accepted by libinput | ✓ | – | ✓ | ✓ | – | `accepted=1 direct_devices_seen=2` |
| Compositor holds the touchscreen device | ✓ | – | ✓ | ✓ | – | 2 `/dev/input/event*` fds in phoc |
| Real finger operates the launcher | ✓ | – | ✓ | – | – | instrumented; **needs the user’s taps** (see below) |
| Launcher is the authoritative PWA | ✓ | ✓ | ✓ | ✓ | – | HTTP 200 + hashes + registry test |
| App registry intact (ids/names/icons/dock) | ✓ | ✓ | ✓ | ✓ | – | `tests/launcher-registry-test.js` |
| Wallpaper is the original asset at the served path | ✓ | ✓ | ✓ | ✓ | – | sha256 + CSS reference + HTTP 200 |
| Colour conversion to the DECON order | ✓ | ✓ | ✓ | ✓ | – | unit test + `colour=R@0,G@8,B@16` live |
| Visual colour/wallpaper acceptance | – | – | – | – | – | **user** |
| Ten-zone cutout editor (Settings + console) | ✓ | ✓ | ✓ | ✓ | – | `SAFEZONES … blocked=[9,10]` |
| Status items avoid blocked zones | ✓ | ✓ | ✓ | ✓ | – | `moved=[{"cluster":"status-right","shift":112,"zone":9}]` |
| Settings persist across reboot | ✓ | – | ✓ | ✓ | – | files are `KEEP`d; `/etc/nuxel/**` |
| Power short press toggles the display | ✓ | – | ✓ | ✓ | – | `nuxelctl display off/on` verified; **physical press** is the user’s |
| Volume keys drive the real mixer | ✓ | – | ✓ | ✓ | – | element `Left AMP PCM Gain`, OSD 95 % |
| Volume OSD visible | ✓ | – | ✓ | – | – | publisher verified; on-screen check is the user’s |
| Audio output (sound from the speaker) | – | – | – | – | – | **[X] not verified** — no player in the image |
| Bixby key recognised (703) | ✓ | ✓ | ✓ | – | – | EVIOCGBIT on the device; **physical press** pending |
| Bixby → Nuxel Terminal (one instance) | ✓ | – | ✓ | – | – | PTY + focus rule implemented |
| Bixby remapping in Settings | ✓ | ✓ | ✓ | – | – | also `nuxelctl buttons set` |
| Animation plays its full cycle before hand-off | ✓ | – | ✓ | – | – | verify on the next boot (kmsg `ANIM_MIN_CYCLE_RESULT`) |
| Single framebuffer owner, clean hand-off | ✓ | – | ✓ | ✓ | – | `fb-owner` ends `LAUNCHER_DISPLAY_OWNER` |
| Fedora + live console survive UI updates | ✓ | – | ✓ | ✓ | – | every deploy/restrart done over the same console |

## The remaining physical tests (user, on the glass)

1. **Touchscreen**: tap top-left, tap centre, tap bottom-right, swipe vertically, then tap
   one launcher tile.  Expected evidence in `/run/nuxel-home.state`:
   `EVT pointerdown/click x=… y=… id=<tile>` followed by `EVT app:launch id=<app>`.
2. **Launcher**: confirm the interface is the intended Nuxel Home.
3. **Colours/wallpaper**: confirm the wallpaper and palette now look correct.
4. **Cutout**: Settings → Display → Status Bar → Camera & Cutout Areas; the battery
   indicator must stay clear of the camera area (default preset already blocks zones 9-10).
5. **Power**: one short press → screen off; another → screen on; Fedora and the console
   must survive.
6. **Volume**: presses change the level (the OSD appears); actual audio playback is
   reported separately as unverified.
7. **Bixby**: one short press opens the Nuxel Terminal; changing the mapping in Settings
   changes its behaviour.

Nothing in this document claims the physical results, and no “beta ready” statement is
made until the user confirms them.
