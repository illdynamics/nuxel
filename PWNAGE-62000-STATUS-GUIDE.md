# PWNAGE-62000 Operator Status Guide

## Home (unlocked)

- Home’s DOM status bar is the only top bar.
- DOM Back/Penguin Home/Tabs is hidden when the native dock has proved it is mapped;
  otherwise it is the fallback.
- Native top bar is hidden.
- Expected state: `statusbar.state.visible=false`, `visible=true/mapped=true` in
  `nuxel-navdock.json`.

## Native/Flatpak app foreground (unlocked)

- App toplevel is `act=1`.
- Native top bar is visible above it; `foreground.state` contains
  `locked=0 native=1 app_id=<id>`.
- Native Back/Home/Tabs dock is mapped.
- Home DOM bar/nav remain behind the app and are not duplicated.
- Dialogs/popovers should remain usable; the top bar has an empty input region.

## Lockscreen

- Lock wins over everything: Home is activated/maximized above all non-Home toplevels.
- Native bar and dock are hidden.
- `/run/nuxel/security/lock-state.json` is authoritative; missing/invalid = locked.
- `/run/nuxel/lock-enforcement.state` should show `locked:true`, `home_raised:true`,
  and `hidden_non_home` for apps that were open.
- An app activation attempt while locked must leave Home `act=1` and the app `act=0`.
- Unlock returns to canonical Home; the dock is restored only after auth succeeds.

## Live-console indicators

- **Base penguin**: Live Console service/daemon ready in the background.
- **Serial/USB icon**: only a real USB CDC-ACM interactive session with physical
  USB data link.
- **USB-network icon**: unavailable on the current 4.14.253 NCM path; never fabricated.
- **WLAN icon**: only an interactive, PTY-backed `nuxel` SSH shell whose local address
  belongs to the Wi-Fi interface. Wi-Fi up / sshd listening / keyscan / one-shot
  command / port-forward / SFTP-only never light it.
- Closing the last WLAN session turns only the WLAN icon off; the base penguin stays on
  while the service is ready.

## Quick diagnostics

```sh
cat /run/nuxel/shell-chrome.json
cat /run/nuxel-navdock.json
cat /run/nuxel-statusbar.state
cat /run/nuxel/foreground.state
cat /run/nuxel/lock-enforcement.state
cat /run/nuxel/security/lock-state.json
cat /run/nuxel/preload-cinema.receipt
journalctl -b -o short-monotonic | grep -E 'nuxel-(wayland|wl-fb|audio-session)'
```
