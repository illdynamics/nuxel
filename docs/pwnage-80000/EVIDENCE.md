# PWNAGE-80000 — Live Evidence

All commands were run on the physical S10+ over Wi-Fi SSH. Host key verification remained enabled.

## Connection

```text
Host: 192.168.178.167
SSH key: ~/.ssh/wicked_wqn_id_rsa (readable, 0600)
Pinned host key: SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs
Remote identity: uid=0 user=root
Kernel: 4.14.253-gf7194c1d15ed-dirty
OS: Fedora 43 aarch64
```

## Final deployed hashes

```text
53d5e13e376214c08f6ba24d38c3879f83b1f9b647af73b7d33cf65ce334fb5d  /usr/lib/nuxel/nuxel-pwa-host
f476f30f75c0bac8ef7ce161d6045504ed2bc9d4c7e35f63bc68aa816043c42e  /usr/lib/nuxel/nuxel-osd
b47d1f16fb585c7491e1aa9c6e8463c155c62b224ae2762655f663274b2067ae  /usr/lib/nuxel/nuxel-button-manager
c9453df0400214d84fe37e2d0787420d36f0f60862235696ad523b5206d41349  /usr/share/nuxel/pwa/nuxel-home/js/app.js
64269dd3b6ffa97bda798e391e6f429bbf54f12b72d95ff2050a323748cd428e  /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js
ff9568535d2d06ac346f4dbc246c42d7b6b84d4c1dc7cc9ac823f544376d1229  /usr/share/nuxel/pwa/nuxel-apps/doom/js/doom.js
```

## Focused Back / keyboard / overlay run

```text
Calendar before Back:
  bound=True grid=42 editor=flex keypad=block kb=1
  frame.canGoBack=True

After Back with keyboard open:
  EVT back:keyboard-dismiss
  NUXEL_KEYBOARD_VISIBLE 0

After editor Back:
  editorDisplay=none
  frame.canGoBack=False

After root Back:
  app=None state=CLOSED session=CLOSED
  overlays={'frames': 0, 'iframes': 0, 'powerMenus': 0, 'folderSheets': 0}
  dock=True

Desktop input after close:
  action all-apps -> drawerOpen=True, drawerChildren=45
```

Doom root Back:

```text
DOOM_ACTIVE app=org.nuxel.Doom state=ACTIVE
DOOM_BACK   app=None state=CLOSED overlays={frames:0,iframes:0,powerMenus:0,folderSheets:0}
```

Force-kill with keyboard open:

```text
BEFORE_KB=1
AFTER_FORCE app=None state=CLOSED overlays={frames:0,iframes:0,powerMenus:0,folderSheets:0} kb=0
```

## Recents swipe run

```text
HOST_UI_SWIPE id=recents-card-org.nuxel.Calendar dir=left
app:graceful-start id=org.nuxel.Calendar native=0 reason=recents-swipe-left

HOST_UI_SWIPE id=recents-card-org.nuxel.Doom dir=right
app:closed id=org.nuxel.Doom reason=force:recents-swipe-right
app:force-killed id=org.nuxel.Doom reason=recents-swipe-right

FINAL overlays={frames:0,iframes:0,powerMenus:0,folderSheets:0}
```

## Calendar numeric time

```text
START 09:30
KEYPAD True time-keypad
EDITOR flex
BOUND True
GRID 42
FRAME canGoBack=True explicitBack=True navigationCanGoBack=False
KB=0
```

## Four-orientation drawer matrix

```text
ORIENT portrait          eff=0   transform=normal verified=True viewport=360x760  drawerCols=3 right=347.98 overflowX=False
ORIENT landscape         eff=90  transform=270    verified=True viewport=1520x760 drawerCols=3 right=1504  overflowX=False
ORIENT reverse-portrait  eff=180 transform=180    verified=True viewport=360x760  drawerCols=3 right=347.98 overflowX=False
ORIENT reverse-landscape eff=270 transform=90     verified=True viewport=1520x760 drawerCols=3 right=1504  overflowX=False
```

## Power menu

```text
OSD_INPUT interactive=1 rows=16 row_h=46.0 cols=2 rows_per_col=8
```

Screenshot selection:

```text
gallery_before=26 gallery_after=27
/home/nuxel/Gallery/nuxel-screenshot-20261105T145445792Z.png
```

Lock selection:

```text
locked=1
/run/nuxel-wl-fb.state: DISPLAY_SLEEP ... display=off
security/lock-state.json: {"locked": true, "owner": "security_provider"}
```

Refusal and Back:

```text
CTRL_MENU_SELECT index=14 id=recovery
MENU_REFUSED id=recovery reason=NO_FLASH_INVARIANT
CTRL_MENU_SELECT index=10 id=back
MENU_SELECT id=back action=back
```

Duplicate-open check: `pgrep -c nuxel-osd` returned **1**.

## Reboot timing (final controlled test)

```text
Selection:                         2026-11-05T15:06:13.753Z
CTRL_MENU_SELECT index=3           restart
MENU_SELECT id=restart
REBOOT_ALLOWED                     at_ms=194400
REBOOT_SPAWNED                     at_ms=194401
REBOOT_ACCEPTED                    at_ms=194534   (+133 ms)
Finished systemd-reboot.service     2026-11-05T16:06:17+01:00
Reached target reboot.target        2026-11-05T16:06:17+01:00
SSH ready again                     2026-11-05T15:06:47Z
```

This separates a ~4 second userspace/systemd shutdown from the ~30 second bootloader/kernel boot. There is no 30-second delay before the reboot request is issued.

## NuXtore / Doom

```text
nuxtore-verify.py --root .
  OK org.nuxel.Doom 2.0.0 SIGNED_VERIFIED 22 files, 3237359 bytes; signed by nuxel-beta-dev-2026
  -- org.example.UnsignedDemo 0.0.1 UNSIGNED_REFUSED
  => all packages verified

Fresh UI install (unregistered first):
  HOST_UI_FOCUS id=install-org.nuxel.Doom result=ok
  HOST_UI_FOCUS id=do-install result=ok
  inventory: org.nuxel.Doom = installed_and_launchable

WAD catalogue:
  4 entries:
    freedm.wad    IWAD  Freedoom
    freedoom1.wad IWAD  Doom 1 / Freedoom
    freedoom2.wad IWAD  Doom 2 / Freedoom
    prboom.wad    PWAD
```

No commercial IWAD is bundled. Freedoom/FreeDM remain the free defaults; user imports require an ownership acknowledgement.

## Post-reboot persistence

```text
Final boot ID: 06216bf6-9cbf-4b48-b46d-5ad008cf8db6
nuxel-wayland, nuxel-wl-fb, nuxel-button-manager,
nuxel-web, nuxel-http-bridge, nuxel-orientationd: active
systemctl --failed: 0 loaded units listed
Orientation: portrait, effective 0, display_verified True
Doom inventory: installed_and_launchable
```

---

# Continuation evidence (post-reboot hardening)

## Boot cue stop regression

Before:

```text
nuxel-boot-sound.service: State 'stop-sigterm' timed out. Aborting.
nuxel-boot-sound.service: Failed with result 'timeout'.
systemctl --failed: 1 loaded unit (nuxel-boot-sound.service)
KillMode=control-group
```

After deploying the process-scoped drop-in and exercising the real cue path:

```text
start_rc=0
ActiveState=inactive
SubState=dead
Result=success
KillMode=process
TimeoutStopUSec=5s
systemctl --failed: 0 loaded units listed
Unit process 13483 (timeout) remains running after unit stopped.
Unit process 13486 (pw-play) remains running after unit stopped.
Finished nuxel-boot-sound.service
```

The helper processes are the intentional bounded 8 s silent warm-up; the service now finishes successfully without waiting on them.

## Framebuffer bridge rebind

Before the deploy-script fix:

```text
1793892049 WL_DISPATCH_FAIL errno=32
display=off
```

After `systemctl restart nuxel-wl-fb.service`:

```text
1793892066 FRAMES_OK total=24 fps_1s=8 failures=0 ... display=on
1793892071 FRAMES_OK total=60 fps_1s=7 failures=0 ... display=on
```

`deploy-pwnage80000.sh` now restarts the bridge after Wayland and waits for `FRAMES_OK`.

## App-close native focus

Calendar was opened, the editor/time field focused, then Back was pressed through the root close:

```text
HOST_AFTER_APP_CLOSE why=after-app-close zoom=1 repaint=1 focus=home
HOST_HOME_REFOCUS active=1 view_focus=1
back:keyboard-dismiss
back:pwa-app-control
back:pwa-app-control
back:pwa-at-root-graceful-close
overlays={"frames":0,"iframes":0,"powerMenus":0,"folderSheets":0}
KB=0
```

Post-reboot repeat:

```text
KB_OPEN=1
NAVDOCK={"visible":true,"mapped":true,"lock":"unlocked",...}
KB_AFTER_BACK=0
HOST_HOME_REFOCUS active=1 view_focus=1
DRAWER True repeat(3, ...) 45 overlays={"frames":0,"iframes":0,"powerMenus":0,"osd":1,"folderSheets":0}
```

WebKitGTK reports `document.hasFocus()==false` after the synthetic close, while GTK reports `active=1 view_focus=1`; the compositor has one Home toplevel and the drawer/navigation controls accept the real control path immediately.

## Final controlled reboot

```text
CTRL_MENU_SELECT index=3 id=restart
MENU_SELECT id=restart action=systemctl-reboot
REBOOT_ALLOWED  at_ms=1378361
REBOOT_SPAWNED  at_ms=1378362
REBOOT_ACCEPTED at_ms=1378464   (+102 ms)
Reached target reboot.target  16:29:51.640 CET
New boot ID                    4a1d352f-57b0-4058-9a57-57c68705104d
SSH observed again             2026-11-05T15:30:44.990Z
```

Post-reboot:

```text
systemctl --failed: 0 loaded units listed
nuxel-boot-sound.service: Result=success, KillMode=process
nuxel-wayland, nuxel-wl-fb, nuxel-button-manager, nuxel-web,
nuxel-http-bridge, nuxel-orientationd: active
Orientation: portrait, effective 0, applied True
launcher-ready: http://127.0.0.1:8000/pwa/nuxel-home/index.html?boot=os
wlfb: FRAMES_OK failures=0 display=on
NUXEL_ZOOM_POLICY injected=all-frames default=deny
NUXEL_ZOOM_GUARD installed=1 default=deny magnification=1 zoom=1 gestures=denied
osd_procs=1
keyboard=0
```

Persisted hashes after reboot:

```text
922b9a15d5ebe81bbce9eeb98b6154882ce4a647ebd9f93449dfc1b48e021277  /usr/lib/nuxel/nuxel-pwa-host
f476f30f75c0bac8ef7ce161d6045504ed2bc9d4c7e35f63bc68aa816043c42e  /usr/lib/nuxel/nuxel-osd
b47d1f16fb585c7491e1aa9c6e8463c155c62b224ae2762655f663274b2067ae  /usr/lib/nuxel/nuxel-button-manager
c9453df0400214d84fe37e2d0787420d36f0f60862235696ad523b5206d41349  /usr/share/nuxel/pwa/nuxel-home/js/app.js
c0cf4fc728c8fa494f943c8334db994efc55ca5fca10b5067fab1ca16d5ac59f  /usr/share/nuxel/pwa/nuxel-common/zoom-policy.js
```

## Four-orientation drawer rerun

```text
portrait          cols=3 vw=360  scale=1 lastRight=347.984 overflowX=false items=45
landscape         cols=3 vw=1520 scale=1 lastRight=1504    overflowX=false items=45
reverse-portrait  cols=3 vw=360  scale=1 lastRight=347.984 overflowX=false items=45
reverse-landscape cols=3 vw=1520 scale=1 lastRight=1504    overflowX=false items=45
```

Portrait was restored afterward.

## Recents gestures rerun

```text
HOST_UI_SWIPE id=recents-card-org.nuxel.Calendar dir=left
app:graceful-start id=org.nuxel.Calendar native=0 reason=recents-swipe-left
HOST_UI_SWIPE id=recents-card-org.nuxel.Doom dir=right
app:closed id=org.nuxel.Doom reason=force:recents-swipe-right
app:force-killed id=org.nuxel.Doom reason=recents-swipe-right
FINAL overlays={"frames":0,"iframes":0,"powerMenus":0,"folderSheets":0}; KB=0
```

## Power menu rerun

```text
osd_procs=1
OSD_INPUT interactive=1 rows=16 row_h=46.0 cols=2 rows_per_col=8
CTRL_MENU_SELECT index=2 id=screenshot
MENU_SELECT id=screenshot action=screenshot
gallery_before=27 gallery_after=28
CTRL_MENU_SELECT index=10 id=back
MENU_SELECT id=back action=back
OSD_INPUT interactive=0 rows=0 ...
```

## Doom / NuXtore post-reboot

```text
nuxtore-verify.py --root /usr/share/nuxel
  OK org.nuxel.Doom 2.0.0 SIGNED_VERIFIED 22 files, 3237359 bytes
  => all packages verified
WAD API /api/v1/doom/wads
  count=4
  freedm.wad, freedoom1.wad, freedoom2.wad, prboom.wad
Nuxel registry Doom entries: only org.nuxel.Doom
Standalone Chocolate Doom Nuxel app/package entries: none
```

## Blue-rectangle check after app close

A baseline desktop screenshot and a screenshot taken immediately after Calendar root-Back graceful close were captured at 720×1520. Pixel analysis of the top 500 rows:

```text
base  blue_fraction=0.01920
after blue_fraction=0.01916
top-500 mean absolute diff=0.09
rows with mean diff > 30: 0
rows >80% blue: none
```

There is no isolated stale top band or blue rectangle after the close.

## Continuation offline suites

```text
tests/pwnage80000/test_pwnage80000.py                 96 passed, 0 failed
pwa/nuxel-apps/doom/tests/test-doom.js                45 passed, 0 failed
pwa/nuxel-home/tests/test-zoom-policy.js               7 passed, 0 failed
pwa/nuxel-apps/nuxtore/tests/test-catalog.js          18 passed, 0 failed
pwa/nuxel-apps/nuxtore/tests/test-catalog.py          18 + 12 passed, 0 failed
services/nuxel-bridge/test-doom-assets.py             16 passed, 0 failed
```
