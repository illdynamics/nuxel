
| Check | Result |
|---|---|
| OpenMTP GUI session | `session_open: true`, storage `65537 nuxel`, 18 objects |
| Phone → Mac | sha256 `699b9927…b43dd` matches |
| Mac → phone | object 19, sha256 `a09c3f92…e6bb6` matches |
| OpenMTP error log | empty |
| Failure reproduced | replug → config `#2` → `0xe00002c5` |
| Helper repair | config `2`→`1`, engine claims device |

I created `scripts/nuxel-mtp-openmtp.sh` (`--status`, `--claim`, `--app`) and documented the root cause in `docs/beta-finalization/live/PWNAGE-51000-MTP-MACOS.md`.

## Two things you should know

1. **Tradeoff:** on config `#1` there's no CDC-ACM, so `/dev/cu.usbmodem101` disappears while OpenMTP is connected. On macOS the USB serial console and OpenMTP file transfer are mutually exclusive. Wi-Fi SSH is unaffected.      
2. **This will recur.** Every unplug/replug or phone reboot sends it back to config `#2` and OpenMTP will fail again until you run the helper.

The real fix belongs on the phone: stop advertising ACM+MTP as a *separate higher-priority* configuration for macOS — either make config `#1` the default or move the console to a vendor interface inside one configuration. That gets both working simultaneously. I didn't touch the gadget because `nuxel-usb-mode.sh` deliberately preserves ACM, and that's a design decision rather than a bug fix.

Also noticed: `/run/nuxel/mtp-media.mounts: No such file or directory` at line 154 of `nuxel-usb-mode.sh`, so the Gallery/Pictures/Videos/Downloads bind mounts silently fail on the restore pass. Worth fixing separately if you expected those folders to appear.

Want me to attempt the phone-side gadget change so OpenMTP works on first connect without the host helper?        
tokens used
1,970,662
[codeseeq] stopping owned bridge process (pid=41832)
(base) ╭─[ꝖꝖ]─wicked↯infranux in ~/x/nuxel
╰─❯❯❯ 

