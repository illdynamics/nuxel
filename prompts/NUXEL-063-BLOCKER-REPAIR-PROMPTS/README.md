# Nuxel v0.6.3-beta — 31 isolated blocker-repair missions

**Baseline:** The independent audit of `nuxel-v0.6.3-beta-FULL-dropin.zip` against `final(1).md`.

**What's included:** 27 distinct prompts mapped 1:1 to the final.md acceptance matrix, plus 4 crosscutting repair missions: 28 clean image parity, 29 GitHub release, 30 documentation/evidence, 31 gesture/performance. The files are **instructions for future implementation; these repairs have not been performed**.

Each Markdown is standalone and includes: observed source-specific defect, exact code paths to inspect, a distinct ordered work plan, negative tests, live device acceptance criteria and safe rollback instructions. Prompts are for **one component at a time**, not simultaneous implementation.

## Recommended execution

Use `EXECUTION-ORDER.tsv` (not numeric filename order) as the preferred sequence. Where hardware dependencies block one component, record a blocker and continue independent components. A clean image parity pass should happen early, and again after userspace integration; the release job must be last after tests and evidence.

On a MacBook, after extracting and switching to the appropriate Nuxel working branch:

```bash
csl "$(cat /path/to/NUXEL-063-BLOCKER-REPAIR-PROMPTS/prompts/02-four-app-dock-bg.md)"
```

Run **one** agent mission at a time with explicit owner review of the diff and physical confirmations. Do **not** execute the whole pack as a parallel queue against one live phone. These prompts instruct the agent to implement and deploy (unlike your earlier prompt-factory requests).

## Release policy and proof levels

- Source compiled/tests passed ≠ S10+ hardware works.
- Source image passes CI ≠ successful physical boot or speaker/network acceptance.
- Missing kernel firmware/support must be reported as BLOCKED, not papered over with fake controls or unsafe driver writes.
- No flashing or raw partition writes are authorized by any prompt.
- `final.md` remains the *acceptance contract*; never silently reduce it.

## Scope crosswalk

| ID | Area | Priority | Depends on |
|---:|---|---|---|
| 01 | [Bottom navigation dock artwork and layering](prompts/01-navigation-dock-artwork.md) | P0 | 04,31 |
| 02 | [Four-app dock BG1/BG2 invisible or unswitchable](prompts/02-four-app-dock-bg.md) | P0 | 04,31 |
| 03 | [Quick Settings shade and notification panel graphics](prompts/03-quick-settings-artwork.md) | P1 | 01,02,04,27 |
| 04 | [Custom icon loading and WebKit asset/cache consistency](prompts/04-icon-and-cache-delivery.md) | P0 | none |
| 05 | [Actual CPU utilization and frequency meter](prompts/05-cpu-meter.md) | P1 | 28 |
| 06 | [Real RAM usage, percentage and quantities](prompts/06-ram-meter.md) | P1 | 28 |
| 07 | [Mali GPU utilization and frequency](prompts/07-gpu-meter.md) | P1 | 28 |
| 08 | [Mali shared GPU allocation accounting](prompts/08-gpu-shared-memory.md) | P2 | 28,07 |
| 09 | [S10+ Broadcom radio firmware and driver bring-up](prompts/09-wifi-hardware.md) | P0 | 28 |
| 10 | [Full NetworkManager-backed Wi-Fi Settings](prompts/10-wifi-manager.md) | P0 | 09,28 |
| 11 | [End-to-end IP, DNS, TLS, browser connectivity](prompts/11-internet-verification.md) | P0 | 09,10,12 |
| 12 | [Full native WebKit multi-tab Nuxel Browser](prompts/12-native-webkit-browser.md) | P0 | 10,11,28 |
| 13 | [Real filesystem File Explorer operations and security](prompts/13-real-file-explorer.md) | P0 | 28 |
| 14 | [Secure ZIP create, inspect and extract in Files](prompts/14-safe-zip-operations.md) | P1 | 13 |
| 15 | [S10+ Exynos/Madera physical speaker playback path](prompts/15-speaker-route.md) | P0 | 28 |
| 16 | [Boot cue and rapid volume feedback through verified output](prompts/16-boot-volume-cues.md) | P0 | 15,25 |
| 17 | [System-wide Normal/Vibrate/Silent sound behavior](prompts/17-sound-modes.md) | P1 | 15,16,27 |
| 18 | [BlueZ HCI, pairing, profiles and connected devices](prompts/18-bluetooth-bringup.md) | P1 | 28,27 |
| 19 | [Native S10+ NFC NCI and NDEF reader](prompts/19-nfc-bringup.md) | P2 | 28,27 |
| 20 | [Real GNSS, GeoClue, permissions and location lifecycle](prompts/20-gnss-location.md) | P2 | 09,28 |
| 21 | [Nuxel Maps online tiles, OSM behavior and GNSS](prompts/21-maps.md) | P2 | 11,20,12 |
| 22 | [S10+ V4L2/ISP camera and real capture](prompts/22-camera.md) | P1 | 28,24 |
| 23 | [Real LED torch backend and fail-honest toggle](prompts/23-flashlight.md) | P1 | 25,27 |
| 24 | [Power+VolumeDown authentic live-frame screenshots](prompts/24-real-screenshots.md) | P1 | 25,28 |
| 25 | [Deterministic Power/Bixby/volume input FSM](prompts/25-button-shortcuts.md) | P1 | 22,23,24,16 |
| 26 | [Truthful single-instance status icons + battery/sound](prompts/26-honest-status-bar.md) | P1 | 09,10,17,18,19,20,27 |
| 27 | [Actual Quick Settings toggles with synchronized backend](prompts/27-quick-settings-backends.md) | P0 | 09,10,17,18,19,20,23,26 |
| 28 | [Fresh Fedora S10+ rootfs parity with live userspace](prompts/28-fresh-image-parity.md) | P0 | none |
| 29 | [Main-merge CI, tag, prerelease and verified S10+ artifacts](prompts/29-github-release-automation.md) | P0 | 28 |
| 30 | [Evidence-based documentation, progress and feature claims](prompts/30-evidence-docs.md) | P1 | 01-29 |
| 31 | [Home gesture arbitration, app drawer, zoom and smoothness](prompts/31-gestures-zoom-performance.md) | P1 | 02,04,27 |

### Important hardware order

- Wi-Fi: physical radio (#09) → NM settings (#10) → verified internet (#11) → real browser (#12).
- Audio: physical Madera/amp route (#15) → boot/volume cues (#16) → sound-mode enforcement (#17).
- Files: scoped real filesystem backend (#13) → archive operations (#14).
- Inputs: camera (#22)/torch (#23)/screenshot (#24) need coherent shortcut ownership (#25); those issues should be developed with clear stubs/blocked paths and retested together.
- Release: image parity (#28) → verified workflows (#29) → truthful documentation (#30).

**Do not equate production-ready with every app compiling.** The owner must confirm every physical test (or an exact hardware blocker must be documented).
