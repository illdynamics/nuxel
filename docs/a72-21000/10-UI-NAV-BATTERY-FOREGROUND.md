# NUXEL A72 / 21000 — 10-UI-NAV-BATTERY-FOREGROUND

All three shell/launcher truth fixes are confirmed STILL DEPLOYED on the live phone
(device hashes == repo for the files that implement them):

- A69-02 single nav: `style.css:363 .native-nav-present #system-navigation{display:none}`.
- A69-13 foregrounding: `style.css:369-372 body[data-app-state=ACTIVE|LAUNCHING]` hides
  `#dock`/`#app-grid`; `app.js` has `_dismissLauncherChrome` (4 refs).
- A69-01 battery: `lockscreen.js` reads host `battery-capacity` first, renders `—` when
  unknown (never 0%); `status-bar.js` (device) has the A66-02 empty-read guard.

Launcher reload after the Maps deploy returned `STATUSBAR_OVERLAP_CHECK cells=2
overlaps=none` and `HOST_STATUS_INDICATORS ok`; phoc / nuxel-pwa-host / nuxel-navdock /
nuxel-wl-fb all running. No nav/battery regression.

Physical touch verification (Back/Home/Tabs across apps, drawer cold/return launch,
10 wake cycles) requires an owner interactive session; statuses marked NOT_TESTED
until then, not assumed PASS.
