# A49 Owner test — wireless casting

**Status: NEEDS_OWNER_TEST, capability-first. No Miracast button unless the
capture/transport/encode pipeline actually functions.**

## 1. Capability probe (read-only, safe)
```sh
nuxel-cast-diag.sh status --json      # p2p, capture, encoders, verdict
```
`MIRACAST_CANDIDATE` still needs a real Phoc screencast implementation; it is a
candidate, not a drop-in. `LAN_SCREENSHARE_CANDIDATE` must be labelled "Share
screen" (WebRTC), never Chromecast/Miracast discovery of smart TVs.

## 2. Path A — Miracast / Wi-Fi Display
Prove each stage: `iw phy` P2P capabilities → NetworkManager/wpa_supplicant P2P
device → P2P group association → RTSP session → working H.264 encoder
(`gst-inspect-1.0 openh264enc|x264enc|vah264enc`) → real Phoc screencopy/portal
capture → optional audio. Only then expose a Cast tile.

## 3. Path B — LAN / WebRTC screen share
Only when real compositor capture exists. Require: explicit user start, pair
code/token, network scoping + authentication, session stop/revoke, no background
broadcast, quality caps, frame pacing, and **pause/redact on lock** (never
capture the lockscreen). No unauthenticated public LAN frame endpoint.

## 4. Acceptance
Show actual moving Nuxel pixels on a real receiver (or an accurately-labelled
authenticated browser share), measure rate/frame latency, audio separately,
verify screen-off/lock privacy, disconnect and retry, and Wi-Fi reconnection.
Confirm zero GPU/CPU drain while casting is off.
