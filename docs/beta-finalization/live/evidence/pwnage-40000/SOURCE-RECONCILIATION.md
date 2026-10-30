# PWNAGE-40000 — source ↔ deployed reconciliation

Run: 2026-10-30 continuation. All deploys used staged upload + sha256 check +
`mv`; the previous live copy of every file was archived first to
`/var/backups/nuxel/pwnage-40000-20261030T094225Z/`.

| Source | Deployed | Notes |
|---|---|---|
| `services/nuxel-s10/bin/nuxel-audio-route.sh` | `/usr/lib/nuxel/nuxel-audio-route.sh` | live route reconciled; `ABOX RDMA1_EN` gate kept |
| `services/nuxel-s10/bin/nuxel-abox-firmware-reload-boot.sh` | same path | session-before-route + synchronous route |
| `services/nuxel-session/systemd/nuxel-boot-sound.service` | `/etc/systemd/system/nuxel-boot-sound.service` | `--wait 200`, `TimeoutStartSec=240` |
| `tools/s10plus/a33/nuxel-sound-cue.py` | `/usr/libexec/nuxel/nuxel-sound-cue` | docstring only; behaviour unchanged |
| `tools/s10plus/a33/notes-works-detector.py` | `/usr/local/bin/nuxel-notes-works-detector` | new AT-SPI bus discovery + store corroboration |
| `services/nuxel-bridge/src/hw_providers.py` | `/usr/lib/nuxel/nuxel-bridge/hw_providers.py` | 48 kHz + null-default checks, `_route_ready()` |
| `services/nuxel-s10/pipewire/99-nuxel-s10.conf` | `/etc/pipewire/pipewire.conf.d/99-nuxel-s10.conf` **and** `/usr/lib/nuxel/stage36000/nuxel-s10/pipewire/99-nuxel-s10.conf` | the staged copy is what had been restoring 44.1 kHz |

## Deliberate non-changes (protected live configuration)

- Amplifier PCM gain left at the live value (19/19); the old "12" from
  `audio-fix-20261029c.txt` was **not** re-imported.
- The static sink `alsa_output.hw_0_1` (S16LE, 48 kHz, 2ch) was not replaced.
- `nuxel-audio-route.sh` still selects the card by name (`beyond-madera`), not
  by a hard-coded index.
- The stub UCM profile was not populated.
- `systemd-udevd` remains masked.

## Restored side effect

`/etc/nuxel/display/screen-timeout.json` had been left at
`{"timeout_ms": 0, "never": true}` by the 2026-10-29 session. Restored to the
repo default `{"timeout_ms": 300000, "never": false}`; the old value is kept at
`/var/backups/nuxel/pwnage-40000-20261030T094225Z/screen-timeout.json.never`.
