# `configs/alsa-ucm/` — ALSA UCM2 profiles

## S10+ (this build group): card `beyond-madera`

The Samsung Galaxy S10+ (SM-G975F / beyond2lte) exposes its audio as the ALSA
card **`beyond-madera`**: Cirrus Logic **CS47L93** (MADERA ASoC) as the main
codec, **2x CS35L40** smart speaker amplifiers on the I2S/TDM lines, inside the
**Exynos 9820** audio subsystem (ABox).

| File | Installs to |
|---|---|
| `beyond-madera/beyond-madera.conf` | `/usr/share/alsa/ucm2/beyond-madera/beyond-madera.conf` |
| `beyond-madera/HiFi.conf` | `/usr/share/alsa/ucm2/beyond-madera/HiFi.conf` |
| `beyond-madera/VoiceCall.conf` | `/usr/share/alsa/ucm2/beyond-madera/VoiceCall.conf` |
| `nuxel-sound-settings.json` | repository contract only (read by `nuxel-audio-diag.sh`, rendered by briq-06d) — Settings → Sound rows, the shared sound-mode state file and what each row may NOT claim |

The UCM2 directory name **is** the card name: `beyond-madera`, not the SoC or
product codename. That is why the old `SamsungBeyond2/` stub (whose own header
said the card name was "TBD from the real device") is not the canonical S10+
profile: `configs/s10plus/alsa-ucm/beyond-madera` is a symlink to this canonical
directory so the device-keyed build path and the card-keyed UCM path can never
drift apart.

### Why the sequences are empty

No mixer control name or value is invented. The MADERA/CS47L93 namespace is
large and device-specific, and a control that accepts a value is not a route that
produces sound. The concrete EnableSequence/DisableSequence are generated from
the real card:

```sh
nuxelctl audio capture      # -> /var/lib/nuxel/audio/{controls.json,HiFi.conf.generated}
nuxelctl audio ucm-install  # atomic install, backup, hash verify, rollback
nuxelctl audio pipeline     # names the FIRST silent/broken stage of the path
```

Every playback-volume control the generator emits is clamped to the low-volume
cap (`configs/nuxel/audio/audio.json`, default 25 %) so the first bring-up cannot
full-scale a speaker.

## Compatibility entries (other devices, unchanged)

| Entry | Points at | Why it is kept |
|---|---|---|
| `GoogleMustang/` | `../google-pixel-10-pro-xl/alsa-ucm/GoogleMustang/` | Historical compatibility for the Pixel/mustang tree; **does not apply to the S10+** |

## Reference

* Codec chain and firmware requirements: `configs/s10plus/alsa-ucm/README.md`,
  `firmware/s10plus/manifest.yml` (`cs47l93-dsp*.wmfw`, `cs35l40-dsp*.wmfw`).
* postmarketOS UCM2 for madera-family devices is the reference for control
  names once the real capture exists; it is not copied blindly, because a
  different board wires a different amplifier mask.
* Diagnostics: `tools/s10plus/a33/nuxel-audio-diag.sh`; user-facing rows:
  `nuxelctl audio settings` / `nuxelctl audio mode` against
  `nuxel-sound-settings.json`; manual proof:
  `docs/beta-finalization/manual-proof/06-audio.md`.
