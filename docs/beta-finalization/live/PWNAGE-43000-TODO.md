# PWNAGE-43000 TODO

**Target:** Samsung Galaxy S10+ (beyond2lte) · root@192.168.178.167 · Wi-Fi SSH
**Key:** ~/.ssh/wicked_wqn_id_rsa
**Started:** 2026-10-31
**Version target:** v0.7.4-beta (released 2026-10-31)

## Status legend
- [ ] TODO · [~] IN PROGRESS · [x] DONE · [B] BLOCKED

## Checklist

| Item | State | Outcome |
|---|---|---|
| INITIAL INVENTORY AND BACKUPS | [x] | Backups under `/root/nuxel-43000-backup/20261030T162614/` and `/root/pwnage-44000/backup-20261031T054927Z`. |
| BOOT AND REBOOT PERFORMANCE ANALYSIS | [x] | Measured: ABOX reload stopped the whole Wayland session, causing a 3-restart boot storm and a ~31 s stable UI. |
| FIX BOOT CRITICAL PATH | [~] | Audio is now in its own `nuxel-audio-session.service`; a pre-wayland ABOX ordering was tried and **rolled back** because both CS35L41 DSP1s stayed `running=N`. The decoupled session ships; the pre-wayland ordering does not. |
| FIX REBOOT BLACK-SCREEN DELAY | [~] | Display priority and fast-stop drop-ins ship; measurement on a fresh reboot is still an owner check. |
| FIX PRELOADING VIDEO -> LOCKSCREEN TRANSITION | [~] | Preload cinema stays bounded/fail-open; the exact handoff timing is an owner check. |
| FIX LPM / CHARGING TOUCHSCREEN BEHAVIOR | [~] | Charger-mode recovery and device-permission units ship; LPM touch is an owner check. |
| OPTIMIZE QUICK SETTINGS | [x] | Panel-owned timers, stale-generation discard, expanded strip updates single cells; idle work is display-off gated. |
| OPTIMIZE HOME SETTINGS | [x] | Cached panel/hydration path, no `innerHTML` rebuild on reopen, one handler set. |
| FIX HOME KEYBOARD DISMISSAL | [x] | Focus restore + Hide Keyboard + one haptic path covered by the A40/A45 contracts. |
| OPTIMIZE LOCKSCREEN | [x] | Continuous indicator animations removed (PWNAGE-37000B Butterscotch Smooth); measured CPU/RSS reduction. |
| INSTALL AND VERIFY APPLICATIONS | [x] | Registry revision 8 registers eight installed native apps; Flatpak wrappers are truthful (Firefox/VLC → Fedora RPM; Signal/Stremio → blocker). |
| IMPLEMENT LOCKSCREEN USB MODES | [x] | Connection-mode selector + safe USB state machine ship; MTP responder added. |
| TEST REAL USB FILE TRANSFER | [~] | MTP responder + `nuxel-mtp.service` ship; a host-side mount is an owner check. |
| TOP BAR / TRIPLE BUTTON REGRESSION + REMOVE APP TITLE BARS | [~] | `nuxel-statusbar` (layer-shell) ships for fullscreen native clients; owner regression pass remains. |
| VERSION BUMP v0.7.4-beta + DOCS + TAG/RELEASE | [x] | VERSION/manifests/services/APKBUILDs at `v0.7.4-beta`; CHANGELOG, `docs/releases/v0.7.4-beta.md`, README, features and manifests updated; tag + release are created by the `main` push workflow. |
| RUN FULL REGRESSION TESTS | [x] | All local CI-equivalent gates green (see the release notes' verification table). |
| FINAL REBOOT | [x] | PWNAGE-44000 final gated reboot at 2026-10-31 06:56:46 with post-boot verification. |
| VERIFY COMPLETE SYSTEM | [~] | Audio, Bluetooth, Wi-Fi, touch, display, location and the service graph verified; satellite GNSS, camera, modem and full Phosh acceptance remain open. |

## Audio outcome (supersedes the PWNAGE-43000 experiments)

The PWNAGE-43000 speaker experiments tested ABOX Sound Type (`SPEAKER`), `PCM
Source = DSP` and sink levels 25 %/55 %. All three were measured **silent** and
were rolled back. The actual fault was the **CS35L41 PLL reference** (device
tree 6.144 MHz vs ABOX UAIF1 1.536 MHz), fixed in PWNAGE-40000 and
owner-confirmed; see `out.md`, `audio.md` and
`docs/releases/v0.7.4-beta.md`. The pre-wayland ABOX ordering remains
non-shippable because the amp DSP1 firmware does not load under it.

## Evidence

- `docs/beta-finalization/live/evidence/pwnage-43000/` — inventory, boot
  baseline, decoupling deploy/rollback, pre-wayland ABOX experiment, speaker
  audibility experiments, and the UI screenshots (Home/dock, Firefox, VLC).
- `docs/beta-finalization/live/PWNAGE-42000-REPORT.md` — GeoClue agent and
  network location.
- `docs/beta-finalization/live/PWNAGE-44000-REPORT.md` — Home drag, widgets,
  power menu, screenshot, Gallery thumbnails, Files send, flashlight, status.
