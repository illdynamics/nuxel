# `configs/wireplumber/` — WirePlumber session policy

| File | Installs to | Role |
|---|---|---|
| `nuxel-s10plus-audio.conf.d/51-nuxel-s10plus-audio.conf` | `/etc/wireplumber/wireplumber.conf.d/51-nuxel-s10plus-audio.conf` | S10+ device policy: no autosuspend on ALSA output nodes; keep the UCM profile authoritative (`api.alsa.use-ucm = true`) |
| `nuxel-voice-call.lua.d/` | `/etc/wireplumber/nuxel-voice-call.lua.d/` | Historical Pixel/mustang voice-call profile (compatibility entry; **not** S10+ policy) |

Target version: **WirePlumber >= 0.5** (`monitor.alsa.rules` with
`matches` → `actions.update-props`). The 0.4 equivalent (`alsa_monitor.rules`)
is documented, commented out, in the drop-in itself so an older session manager
does not fail on an unknown section.

Honesty note: the rules are validated structurally offline
(`tools/s10plus/a33/tests/test-audio-diag.py`) and in the VM by the VM parity
group; an on-device `wpctl status`/`pw-dump` confirmation is part of the area 6
manual proof. Nothing in this directory asserts audibility.
