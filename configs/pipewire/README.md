# `configs/pipewire/` — PipeWire audio policy

| File | Installs to | Role |
|---|---|---|
| `nuxel-s10plus-audio.conf.part` | `/etc/pipewire/pipewire.conf.d/40-nuxel-s10plus-audio.conf` | S10+ graph policy: 48 kHz (the MADERA/ABox native rate), bounded quantum, device node kept open |
| `asound-nuxel-safe.conf` | `/etc/asound.conf` | **ALSA softvol safety cap** (`max_dB = -6.0`): ALSA consumers cannot exceed the ceiling, so the first speaker bring-up physically cannot full-scale |
| `nuxel-phone.conf.part` | `/etc/pipewire/pipewire.conf.d/40-nuxel-phone.conf` | Historical Pixel/mustang voice-call fragment (kept for compatibility; **not** S10+ policy) |

Session shutdown/restart after installing a drop-in:

```sh
systemctl --user restart pipewire pipewire-pulse wireplumber
```

The S10+ low-volume policy is deliberately enforced at the ALSA layer and in the
generated UCM csets, not by a session-manager property: a stored volume restored
by a session manager must not be able to defeat a bring-up safety cap.
See `docs/beta-finalization/manual-proof/06-audio.md` (area 6) and
`tools/s10plus/a33/nuxel-audio-diag.sh`.
