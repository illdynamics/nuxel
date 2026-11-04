# PWNAGE-62000 Evidence Index

| File | What it proves |
|---|---|
| `stremio-chrome-live.png` | First live Stremio frame with native top bar and mapped dock |
| `stremio-final-chrome.png` | Final-binary Stremio frame with native top bar and mapped dock |
| `locked-over-stremio-live.png` | Nuxel lockscreen above Stremio; OCR reads “swipe up to unlock” |
| `final-lock-state.txt` | Final lock state, toplevel activation, chrome hidden, enforcement receipt |
| `locked-activation-attempt.txt` | App focus request while locked; Home remains activated |
| `final-wlan-session-active.txt` | Real WLAN PTY session -> active; close -> inactive with availability true |
| `pre-reboot-state.txt` | Pre-reboot lock/chrome/wl-fb state |
| `first-reboot-shutdown-timeline.txt` | First reboot journal: wayland fixed, audio 4 s timeout found |
| `second-reboot-shutdown-timeline.txt` | Final reboot journal: audio 0.086 s, wayland 0.576 s, total 3.778 s |
| `reboot-timeline.txt`, `second-reboot-timeline.txt` | WiFi SSH outage/reconnect measurements |
| `reboot-policy-check*.txt` | Reboot policy gates |
| `source-sha256.txt`, `installed-sha256.txt` | Source and installed hashes |
| `deploy.log` | Full real deploy output |

Measurements are physical/compositor evidence from the S10+, not simulations. Touch-only
scenarios (drawer swipe, unlock gesture, rotation hitboxes) were not physically
exercised and are marked `NOT TESTED` in the report.
