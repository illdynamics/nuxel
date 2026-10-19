# Nuxel — Deploy

Live deployment and runtime configuration for Nuxel on the Samsung S10+ (A36).

## Quick reference

- **Live deployer:** `tools/beta/live/nuxel-live-deploy.py` (guarded, checksummed transfers)
- **Sound cues helper:** `tools/s10plus/a33/nuxel-sound-cue.py`
- **Haptics + button-manager deploy script:** `tools/touchable/deploy-haptics-system.py`
- **Boot sound service:** `services/nuxel-session/systemd/nuxel-boot-sound.service`
- **Haptics service:** `services/nuxel-haptics/` (preferences in `configs/nuxel/haptics/settings.json`)

## Live USB deployment (MacBook → S10+)

See [`DEPLOY-A36.md`](./DEPLOY-A36.md) for the full, step-by-step work order.
Summary: apply the `nuxel-branding-sounds-and-icons` extension group via the
guarded live deployer, install/verify audio cues + icon PNGs, build and install
the patched `nuxel-button-manager`, then enable `nuxel-boot-sound.service`.
**Never flash.** Only touch USERATA userspace over a framed USB live console.

## Runtime services

- `nuxel-boot-sound.service` — plays `assets/nuxel-boot-audio.mp3` after the
  animation→launcher ownership handoff (not on early web load).
- `nuxel-haptics.service` / bridge — **only one** may write the vibration motor.
- `nuxel-button-manager` — requests `nuxel-pow.mp3` after each successful mixer
  change; respects mute/vibrate mode and rate-limiting.

## Verify after deploy

```bash
python3 tools/s10plus/a34/tests/test-sound-cues.py
python3 tools/s10plus/a34/tests/test-icon-assets.py
bash   tools/s10plus/a34/tests/run-a34-tests.sh
```
