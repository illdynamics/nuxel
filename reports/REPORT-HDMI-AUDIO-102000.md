# REPORT-HDMI-AUDIO-102000 — USB-C HDMI/DP audio routing, override and Sound settings

**Date:** 2026-11-09
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
**Live access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`
**Repository:** `/Users/wicked/x/nuxel`, branch `feature/v0.8.2-beta-pwnage-97000`,
HEAD `b6154b67ec1e421729cea8053839ce9cfae9095d` (dirty working tree preserved)
**Result:** Software detection, automatic routing, manual override, persistence,
fallback policy and Settings integration are implemented and live. Physical TV
audibility is **NOT VERIFIED**.

---

## 1. Executive summary

The S10+ already had a real Samsung DisplayPort audio DMA endpoint, but Nuxel
classified it as unavailable and never exposed it to PipeWire:

* The live DP audio-info switch was `70975746` (`0x043b0102`), an EDID-derived
  bitmask meaning 2-channel LPCM, 48 kHz, DP. Existing code compared it with
  the literal `== 1`, producing a false negative.
* `/proc/asound/pcm` exposed `00-22: DP Audio … playback 1`, but the only
  PipeWire sink was the static RDMA1 speaker sink. No HDMI sink existed to
  select.
* No component owned automatic/manual routing, stable output identity, or
  persistent user preference. `nuxel-displayd` made a small, conflicting
  default-sink change attempt.

Implemented:

* A single audio-output policy in `nuxel-soundd`.
* Correct non-boolean DP audio-info decoding.
* On-demand real PipeWire sink for the Samsung DP PCM.
* Automatic HDMI preference and safe non-HDMI fallback.
* Manual output selection that is never overridden by HDMI hotplug.
* Stable identity persistence (`alsa:beyond-madera:rdma1`,
  `alsa:beyond-madera:dp-audio`, `pipewire:<node.name>`).
* Live Settings → Sound output list, Automatic, volume, mute and Test sound.
* Diagnostics and CLI commands.
* Unit/fixture coverage for all required routing cases.

Live verification proved software routing: the DP PCM appeared, PipeWire
created `alsa_output.nuxel_hdmi`, the default sink switched to it in Automatic
mode, and the persistent playback stream moved to it. The TV was not audibly
confirmed by a human. A microphone-based physical probe was inconclusive, so
physical HDMI audio remains explicitly **NOT VERIFIED**.

---

## 2. Before-state architecture and evidence

### 2.1 Actual audio stack

* PipeWire `1.4.11`, WirePlumber, and `pipewire-pulse` were already running as
  the existing Nuxel session. No PulseAudio daemon was added and no competing
  sound server was installed.
* Runtime socket: `/run/nuxel-wayland`.
* Existing static speaker sink: `alsa_output.hw_0_1` → `hw:0,1` (RDMA1,
  48 kHz).
* Before deployment only that speaker sink was visible:

```text
31  alsa_output.hw_0_1  PipeWire  s16le 2ch 48000Hz  RUNNING
```

### 2.2 Real DisplayPort audio evidence

```text
/sys/class/switch/secdp/state              = 1
/sys/class/extcon/extcon0/state            = DP=1
/sys/class/switch/ch_hdmi_audio/state      = 70975746  (0x043b0102)
/proc/asound/pcm                           = 00-22: DP Audio snd-soc-dummy-dai-22 :  : playback 1
/sys/class/dp_sec/audio_test               = channel: 0, bit rate: 0, sample rate: 0
```

The vendor display driver source confirms the encoding:

* `sound/soc/samsung/dp_dma.c`: real Samsung displayport ADMA platform.
* `drivers/video/fbdev/exynos/dpu20/displayport_edid.c:edid_audio_informs()`:
  bits 0..7 channel mask, bits 8..15 speaker allocation, bits 16..18 bit rates,
  bits 19..21 sample rates, bit 26 DP/HDMI flag.
* `displayport_drv.c`: `audio config(0 ==> 1)` and
  `Start DP DMA request DP Audio En status = 0x0004001f` were observed when the
  PCM was opened and played.

A direct 48 kHz S16_LE stereo one-second PCM test to `hw:0,22` returned `rc=0`
and produced the following kernel proof:

```text
Displayport: audio config(0 ==> 1)
Displayport: audio_enable:1, ch:2, fs:2, bit:0, packed:2, word_len:0
Displayport: audio_infoframe: type and ch_cnt 01, ...
dma_trigger: Start DP DMA request DP Audio En status = 0x0004001f
```

The `snd-soc-dummy-dai` name is the vendor ASoC codec DAI name used by this
DP DMA link; it is not a null/dummy audio sink.

### 2.3 Existing display/audio code

* `services/nuxel-display/lib/nuxel_display.py` detected `dp_audio_pcm` and
  `ch_hdmi_audio`, but required `ch_hdmi_audio == 1`.
* `services/nuxel-bridge/src/hw_providers.py:_hdmi_audio_status()` used the
  same boolean assumption.
* `services/nuxel-display/bin/nuxel-displayd` attempted to restore a PipeWire
  sink on audio transitions without creating the missing DP sink.
* Settings → Sound had hardcoded “HDMI audio” and “Phone speaker” buttons and
  no dynamic output list or routing mode.
* No persisted output policy existed.

### 2.4 Historical reports inspected

`REPORT-PWNAGE-102000.md` was the prior blue-overlay display report, not this
audio mission. The current prompt in `full-pwnage-102000.md` was read in full.
Existing audio/display test suites and reports were inspected before edits.

---

## 3. Root causes

1. **False-negative DP audio capability.** The live value `0x043b0102` was
   interpreted as “not 1”, so the kernel’s real DP audio capability was
   discarded.
2. **No routable PipeWire endpoint.** The static PipeWire configuration only
   created RDMA1. Even correct detection had no HDMI sink to select.
3. **No authoritative routing owner.** The display daemon and legacy audio
   provider had overlapping, non-persistent default-sink behavior.
4. **No manual override model.** Hotplug had no stable identity or way to
   distinguish user intent from automatic policy.
5. **Settings did not expose real outputs.** The UI could not enumerate or
   select Bluetooth/USB/other real sinks and had no routing mode.

No kernel, firmware, DT or boot-image change was required for the software
routing implementation. The DP link and DP audio DMA already existed.

---

## 4. Files changed and why

### New files

* `services/nuxel-sound/nuxel_audio_outputs.py` — testable discovery, DP-audio
  decoder, PipeWire sink lifecycle, stable identities, routing policy,
  persistence, uevent/reconciliation loop.
* `tests/pwnage102000/test_hdmi_audio_routing.py` — 28 unit/integration tests.
* `docs/audio-output-routing-102000.md` — architecture, policy and commands.
* `configs/nuxel/audio/output-policy.example.json` — persisted-policy example.
* `evidence/hdmi-audio-102000/` — before/after device and test evidence.

### Modified files

* `services/nuxel-sound/nuxel-soundd.py` — owns the audio output manager;
  speaker-route gate is only required for the speaker path; new output-policy
  socket commands; Test sound uses the current route; diagnostics/health.
* `services/nuxel-sound/nuxel-soundctl` — new `outputs`, `diagnostics`,
  `automatic`, `select`, `volume`, `mute`, `test` subcommands; accepts
  `--json` before or after the subcommand.
* `services/nuxel-bridge/src/api.py` — forwards new `sound.*` output verbs and
  merges authoritative output policy into legacy `audio.status`/`audio.sinks`;
  audio volume/mute/set-output delegate to the single manager.
* `services/nuxel-bridge/src/hw_providers.py` — DP audio-info uses the shared
  non-boolean decoder.
* `services/nuxel-display/lib/nuxel_display.py` — same shared decoder; reports
  DP audio capability correctly.
* `services/nuxel-display/bin/nuxel-displayd` — no longer changes PipeWire
  defaults; publishes the display-side capability only.
* `pwa/nuxel-apps/settings/index.html` — new Output card with Automatic, live
  output list, current route/status, volume, mute, Test sound.
* `pwa/nuxel-apps/settings/sound-settings.js` — live policy rendering,
  2-second visible refresh, manual selection, fallback/pending messaging,
  volume/mute and test actions.
* `pwa/nuxel-apps/settings/settings.css` — output list styling.
* `pwa/nuxel-apps/settings/hardware-settings.js` — old audio card refresh is a
  no-op now that Sound owns output policy, preventing two owners.
* `pwa/nuxel-common/bridge.js` — new sound output verbs are never mocked.
* `scripts/nuxel-deploy-live.py`, `tools/s10plus/a43/package-live.py`,
  `images/s10plus/build-phone-rootfs-inside-fedora.sh` — install the policy
  module and `nuxel-audio-ctl`.
* `services/nuxel-display/tests/test-display-model.py` — fixture uses the real
  `0x043b0102` value.
* `services/nuxel-display/README.md` — audio ownership and decoder note.

---

## 5. Routing policy and stable identity design

### Stable identities

| Output | Stable ID | Runtime sink |
|---|---|---|
| Internal speaker | `alsa:beyond-madera:rdma1` | `alsa_output.hw_0_1` |
| HDMI/DP display | `alsa:beyond-madera:dp-audio` | `alsa_output.nuxel_hdmi` (dynamic) |
| Bluetooth/USB/other | `pipewire:<node.name>` | actual PipeWire node name |

The DP PCM is resolved at runtime from `/proc/asound/pcm` (currently
`hw:0,22`). Neither the ALSA card index nor any transient PipeWire node ID is
persisted.

### Automatic

1. Verified HDMI/DP audio endpoint.
2. Last valid non-HDMI output.
3. Current non-HDMI output.
4. Phone speaker.
5. Other real physical output.

Display connection alone is not enough. HDMI is eligible only when the DP link
is ready, the DP PCM exists, and the EDID audio-info word contains usable LPCM
channels and sample rates.

### Manual

The explicit stable identity wins. HDMI hotplug does not change it. If the
selected device disappears, a safe fallback is routed immediately and the
preference remains pending. If the preferred stable identity returns, it is
restored. Selecting Automatic immediately re-evaluates all current endpoints.

### Persistence

`/var/lib/nuxel/audio/output-policy.json` stores only mode, stable ID, preferred
display label and fallback ID. It is written atomically with mode `0600`. Malformed
documents fall back to Automatic.

---

## 6. Service / config / UI changes

* `nuxel-soundd` starts the output manager asynchronously. PipeWire socket
  readiness and the speaker ABOX route are handled independently.
* HDMI sink lifecycle uses `pactl load-module module-alsa-sink` with a stable
  `sink_name`, the runtime-resolved DP PCM path, 48 kHz stereo S16_LE.
* The sink module is unloaded only after routing has left it.
* Active sink inputs are moved with `move-sink-input`; the default sink is
  verified by exact readback.
* A failed switch keeps the previous working default and reports the failure.
* No audio stack restart is used for hotplug.
* `nuxel-displayd` no longer races the audio manager.
* Settings uses the local bridge and refreshes every two seconds while visible.
* `/run/nuxel/audio-outputs.json` exposes machine-readable state.
* `nuxel-audio-ctl` provides safe list/status/automatic/select/volume/mute/test
  commands.

---

## 7. Kernel / firmware / DT blockers

No kernel, firmware, DT or boot-image blocker was found for the DP audio
endpoint on this adapter:

* DP link was ready (`secdp=1`, `extcon DP=1`).
* The DP audio PCM was present.
* The vendor driver programmed the DP audio infoframe and DMA on playback.
* PipeWire exposed and routed the dynamically created real sink.

The remaining uncertainty is physical acoustic output, not software endpoint
presence. No flash/reboot was performed because it was not required and not
approved as a shortcut.

---

## 8. Tests run and exact results

All test artifacts are under `evidence/hdmi-audio-102000/tests/`.

### New PWNAGE-102000 suite

```text
$ python3 -m pytest -q tests/pwnage102000
............................                                             [100%]
28 passed in 3.22s
```

Required scenario coverage in that suite:

* Speaker only.
* HDMI endpoint available.
* Display connected but HDMI audio unavailable.
* Delayed HDMI enumeration.
* HDMI unplug/during-playback fallback (fake backend).
* HDMI reconnect.
* Manual speaker + HDMI hotplug.
* Manual Bluetooth + HDMI hotplug.
* Manual USB audio + HDMI hotplug.
* Selected device disappears, fallback applied, preferred retained, restored.
* Return to Automatic while HDMI is already connected.
* Audio-server unavailable/restart reconciliation.
* Boot/start with HDMI already attached (first reconciliation).
* Rapid hotplug/idempotent sink lifecycle.
* HDMI sink activation failure and route-switch failure.
* No speaker fallback available.
* Volume/mute follow the current sink.
* Persistence by stable ID and malformed-policy migration to Automatic.
* Settings HTML/JS contract, bridge forwarding and no-mock policy.
* Shared non-boolean DP audio-info decoder.

### Existing audio/display suites

```text
$ python3 -m pytest -q <relevant audio suites>
4 failed, 60 passed in 0.98s
```

The four failures are pre-existing and unrelated to this change; the same
failures were present before implementation:

1. `test_audio_route_service_keeps_bounded_timeout` expects an exact
   `After=sound.target` line; current live unit has additional ordering.
2. `test_boot_cue_waits_instead_of_failing_on_first_sample` expects the retired
   `ExecStartPre=...--wait 200` form.
3. `test_route_keeps_25_percent_ceiling` expects the retired 25% cap; current
   owner-approved policy is 100%.
4. `test_abox_wrapper_starts_session_before_route_and_waits` expects retired
   service-order text.

Other suites:

```text
services/nuxel-bridge/test-hw-providers.py       ALL PASS
services/nuxel-display/tests/test-display-model  ALL PASS
services/nuxel-display/tests/test-colour-format  PASS
tools/s10plus/a33/tests/test-audio-diag.py       0 failing checks
tools/s10plus/a33/tests/test-headphone-route.py  0 failing checks
```

Display daemon suite:

```text
1 failed, 21 passed
```

The single failure (`test_bridge_supervisor_restarts_a_dead_bridge`) was also
present before this change and is unrelated to audio.

Full-repository pytest collection could not run because a pre-existing test
module calls `sys.exit(1)` during collection:
`tests/pwnage44000/test_files_send_and_render.py`. Relevant suites were run
individually and their exact logs saved.

### Static/build checks

```text
git diff --check …                               PASS (no whitespace errors)
python3 -m py_compile <all touched Python files> PASS
node --check sound-settings.js hardware-settings.js PASS
```

---

## 9. Device test matrix

| Test | Endpoint seen | Route selected | Playback command | Physical TV audio |
|---|---|---|---|---|
| Deploy with adapter/TV attached | Yes, `DP Audio` + EDID audio-info | Automatic → HDMI | Test cue queued through `alsa_output.nuxel_hdmi` | **NOT VERIFIED** |
| Manual Phone speaker | Yes | Manual → speaker, HDMI sink retained but not default | Cue queued through speaker | **NOT VERIFIED** |
| Return to Automatic while HDMI present | Yes | Automatic → HDMI immediately | Queued through HDMI | **NOT VERIFIED** |
| Manual persistence across `nuxel-soundd` restart | Yes | Manual speaker persisted and re-applied | Route only | **NOT VERIFIED** |
| Audio service restart with HDMI attached | Yes | Automatic reconciled back to HDMI | Route only | **NOT VERIFIED** |
| Invalid output selection | N/A | Refused `OUTPUT_UNAVAILABLE`; default unchanged | None | N/A |
| `nuxel-displayd` restart | Yes | External display `state RUNNING` restored; audio stayed HDMI | Route only | N/A |
| Physical unplug/replug | Not performed remotely | Fixture tests pass | — | **NOT TESTED** |
| Boot with HDMI already attached | Service-start equivalent passed | HDMI on first reconciliation | — | Actual reboot **NOT PERFORMED** |
| Bluetooth output | No BT sink connected on device | Fixture test passed | — | **NOT TESTED** |
| USB-C DAC/headset | No USB sink connected on device | Fixture test passed | — | **NOT TESTED** |
| Internal speaker regression | Speaker sink present/routable | Manual and Automatic fallback pass | Existing route unchanged | **NOT VERIFIED THIS RUN** |

### Physical mic probe

A 1 kHz tone was played to the HDMI sink while the phone’s WDMA1 microphone
recorded ambient audio. Result metrics:

* baseline RMS `877.1`, peak `4212`, crude 1 kHz Goertzel `2471360.5`;
* tone RMS `216.3`, peak `1100`, crude 1 kHz Goertzel `43798.1`.

There was no reproducible 1 kHz increase. This does **not** prove failure; the
TV may have been muted, its volume low, or the microphone may not have captured
the TV. It does mean software cannot claim physical confirmation. Raw ambient
recordings were analyzed and deleted, not retained.

---

## 10. Physical HDMI audio confirmation status

**NOT VERIFIED.**

Confirmed at software/device level:

* real DP link;
* real EDID audio capability (`0x043b0102`);
* real `DP Audio` ALSA PCM;
* driver audio infoframe/DMA enable messages;
* real dynamically created PipeWire sink;
* default-sink and active-stream movement to HDMI;
* test cue queued through that sink.

Not confirmed:

* audible sound from the TV/receiver;
* physical unplug/replug;
* actual reboot with adapter attached.

No report or UI string in this implementation treats software routing as
acoustic proof. `nuxel-audio-ctl test --json` returns
`"audible": "unverified"` and `"physical_confirmation": "not performed by software"`.

---

## 11. Reboot / hotplug / persistence results

* Manual mode/preference persisted by stable ID and survived a live
  `nuxel-soundd` restart.
* Automatic mode re-selected HDMI after the same restart while the adapter was
  attached.
* Display daemon restart preserved the live external display
  (`ext.state RUNNING mode=mirror-portrait`, `HDMI` still routed).
* Physical unplug/replug was not possible from this remote session. The fake
  backend integration tests cover disconnect fallback, reconnect, rapid
  hotplug and manual-override protection.
* Actual reboot with HDMI attached was not performed.

---

## 12. Remaining blockers and exact next steps

1. **Human confirmation of TV audio.** With the adapter/TV connected and the
   phone in Automatic, run:

   ```sh
   nuxel-audio-ctl outputs --json
   nuxel-audio-ctl test --json
   ```

   Confirm whether the TV physically emits the Nuxel cue. Record PASS/FAIL
   separately from the software result.
2. **Physical hotplug test.** While a cue or music is playing, disconnect and
   reconnect the adapter/TV. Confirm speaker fallback and HDMI restoration.
3. **Physical reboot test.** Reboot normally with the adapter attached and
   confirm Automatic selects HDMI on the first settled reconciliation.
4. **TV/audio-path controls.** If the TV remains silent while software proves
   the DP audio infoframe/DMA path, check TV input-specific audio settings,
   TV mute/volume, and whether the HDMI adapter passes DP audio. The same
   adapter/cable/TV working on the Pixel is a useful control but not proof for
   this vendor DP path.
5. **BT/USB device tests.** Connect real Bluetooth and USB-C audio devices and
   confirm manual selection plus HDMI hotplug does not steal them.

No kernel/firmware reflash is proposed at this point. The observed blocker is
physical acoustic confirmation, not absent kernel or userspace routing support.

---

## 13. Deployment and rollback

Targeted userspace deployment was performed over SSH; no flash/reboot occurred.
Backups:

```text
/var/lib/nuxel/live-deploy/rollback-hdmi-audio-20261109T214436Z
/var/lib/nuxel/live-deploy/rollback-hdmi-audio-20261109T214523Z
```

Installed live hashes matched the checked-out sources for all changed runtime
files; see `evidence/hdmi-audio-102000/after/deployed-hashes.txt`.

## 14. Commit

No commit was created. The repository working tree contains pre-existing user
changes and this implementation; those changes were preserved.

---

## 15. Concise final summary

**Software result: HDMI/DP audio detection and routing work on the real live
endpoint. Physical TV audio: NOT VERIFIED.**

Changed: `nuxel-soundd` + new `nuxel_audio_outputs.py`, bridge API,
`hw_providers`, display model/daemon, Settings → Sound UI, bridge JS,
deployment/image installers, tests, docs and config example.

Commands run include: repository recon, live ALSA/PipeWire/DP diagnostics,
targeted deployment, `pactl`/`wpctl` verification, `nuxel-audio-ctl` manual and
automatic routing, `nuxel-displayd`/`nuxel-soundd` restarts, HTTP bridge RPC
tests, API test cues, and the test suites in §8.

Test counts: **28/28 new PWNAGE-102000 tests pass**; **60 relevant existing
tests pass with 4 documented pre-existing failures**; bridge/display model/
colour/audio-diagnostic/headphone-route suites pass. Display daemon suite has
one documented pre-existing failure. Full pytest collection is blocked by a
pre-existing `sys.exit(1)` in `tests/pwnage44000/test_files_send_and_render.py`.

Device result: live Automatic HDMI route, manual speaker override, manual
persistence across soundd restart, return-to-Automatic re-evaluation, invalid
selection refusal, real DP DMA/infoframe logs, Test sound queued through HDMI,
and preserved external display after displayd restart.

**Physical HDMI audio is NOT VERIFIED.**
