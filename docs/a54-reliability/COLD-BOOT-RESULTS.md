# A54 Cold-Boot Acceptance (pending owner-approved reboot)

## Status
No reboot was issued this session. The mission constraints require owner approval
before a controlled cold boot, and the console recovery/rollback path must be
confirmed first. A single **hot** service restart of `nuxel-wayland` was
performed to reload the redeployed launcher (console stayed alive throughout).

## Acceptance table (post-deploy, hot-verified)

| Gate | Result | Evidence |
|---|---|---|
| WIFI-L2 | PASS_INTEGRATION | `wlan0:connected`, association/auth complete (NM state 100) |
| WIFI-IP | PASS_INTEGRATION | IP 192.168.178.x, default route, DNS, HTTPS `204` |
| WIFI-PERSIST (profile) | PASS_INTEGRATION | 3 autoconnect=yes wireless profiles persisted |
| WIFI-PERSIST (cold boot) | NOT_TESTED | reboot needs owner approval |
| ROT-MENU | PASS_INTEGRATION | 7 hyphenated modes, no `undefined`, migration tested (40 tests) |
| ROT-FORCED | PARTIAL | policy/state correct; compositor transform backend absent |
| ROT-AUTO | BLOCKED_HARDWARE | no auto-capable IIO/proxy sensor source |
| STATUS | PASS_INTEGRATION | collision detector `cells=2 overlaps=none`; safe-zones moved right cluster only |
| BATTERY | PASS_INTEGRATION | level=100 status=full charging=false via bridge |
| CAMERA-NUXEL | PASS_INTEGRATION | media store + camera RPC live; native GTK4 app launches/stays alive |
| CAMERA-NATIVE (Snapshot) | BLOCKED_EXTERNAL_RESOURCE | no dnf/microdnf + missing pipewire/wireplumber/libcamera deps |
| CAMERA-FRAMES | BLOCKED_HARDWARE | FIMC-IS `VIDIOC_S_FMT → ENOTTY`, no `/dev/media*` |
| RECOVERY | PASS | `nuxel-console`/USB console untouched and responding |

## Endurance (hot)
- After `nuxel-wayland` restart: no failed units; `nuxel-wayland`, `nuxel-wl-fb`,
  `nuxel-button-manager`, `nuxel-touch-arm`, `seatd` all `active`; `:8000` serves
  200; `:8080` bridge RPC answers; orientation modes correct.
- Idle thermals were not stress-tested this session (screen-off polling rules
  unchanged; no always-on animation was added).

## To complete (owner-assisted)
1. Approve one cold boot; repeat the above gates at 0/+1/+3/+5/+10/+30/+60 s.
2. Visually confirm battery percentage on first interactive frame and that the
   status bar shows no overlap during disconnected→connecting→connected.
3. Physically confirm forced 0/90/180/270 once a compositor transform backend is
   present, and auto rotation once an IIO/proxy gravity source is exposed.
