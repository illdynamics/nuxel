# FULL-PWNAGE-104600 — Audio: speaker, mic, headset and HDMI/DP routing

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104600.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Keep and complete the audio subsystem: speaker, headset and USB-C/HDMI playback,
mic capture, correct routing and persistence — verified audibly. Verify by **hearing real
audio**, not by inspecting unit states.

---

## 1. Current observed state (2026-11-14 16:05 CET)

**Correction to an earlier measurement:** `systemctl is-active pipewire wireplumber`
returns `inactive` because the daemons are **not** system units — they run inside
`nuxel-audio-session.service`. Querying them with the right runtime dir shows a healthy
stack:

```sh
export XDG_RUNTIME_DIR=/run/nuxel-wayland
wpctl status
```

```
PipeWire 'pipewire-0' [1.4.11, root@...]
Sinks:   * 31. S10+ speaker (RDMA1, 48 kHz)   [vol: 0.50]
Sources: * 32. S10+ microphone (WDMA1, 48 kHz) [vol: 1.00]
processes: pipewire (8983), pipewire-pulse (9010), wireplumber (9012)
```

`nuxel-audio-route-retry.timer` runs `nuxel-audio-route.sh` every 10 min and logs:

```
verify ABOX SIFS1=1 (SPUS OUT1) ... ABOX UAIF1 Rate=48000 ... 
default sink alsa_output.hw_0_1 verified
route applied and verified
```

So the **basic route is working**. Remaining risk areas are the things that break
silently: headset jack detection/auto-switch, USB-C HDMI/DP audio hot-plug, capture,
xruns, and routing persistence across a Wayland/session restart or reboot.

**Always export `XDG_RUNTIME_DIR=/run/nuxel-wayland` before `wpctl`/`pactl`** — without
it you get "Could not connect to PipeWire" and a false diagnosis.

Read:

- `REPORT-HDMI-AUDIO-102000.md` (routing design + stable identities)
- `full-pwnage-102000.md` (prior HDMI/DP audio mission)
- `/etc/nuxel/audio/`, `nuxel-audio-route.sh`, `nuxel-soundd`,
  `services/nuxel-audio*`, PipeWire/WirePlumber drop-ins, and the
  `nuxel-audio-route-retry` journal

## 2. Non-negotiable rules

1. "Unit active" is not audio. The acceptance bar is audible output and a real
   capture (`parecord`/`pw-record` waveform, not just an exit code).
2. Do not break the system audio stack to fix one route; speaker must keep working.
3. Persist routing in config, not in one-off `pactl` calls.
4. No `chmod 777` on ALSA devices; respect `audio` group ownership and udev rules.
5. Bound playback/record tests with timeouts; never leave the speaker blasting.

---

## 3. Work order

### Step 1 — Characterise the live stack

- With `XDG_RUNTIME_DIR=/run/nuxel-wayland`, capture `wpctl status`, `pactl info`,
  `pw-top`, and the `nuxel-audio-session` journal.
- Verify the retry timer is not masking a recurring failure
  (`journalctl -u nuxel-audio-route-retry -b`).
- Confirm the session survives a Wayland restart (`systemctl restart nuxel-wayland`)
  and a reboot.

### Step 2 — Restore the core stack

- Start PipeWire + WirePlumber under the correct user and runtime dir.
- Confirm `pactl info` / `wpctl status` lists the S10+ ALSA card(s), speaker, mics,
  headset and any HDMI/DP sink.
- Ensure the solution survives reboot and Wayland session restart.

### Step 3 — Routing

Follow the stable-identity design in `REPORT-HDMI-AUDIO-102000.md`:

- Speaker ⇄ headset auto-switch (jack detection).
- USB-C/HDMI/DP audio appears when a monitor is attached, disappears cleanly.
- Manual override and persistence.
- Mic capture from the correct source; no feedback loops.

### Step 4 — Verify (audible/physical)

1. Play a test tone on speaker — hear it.
2. Plug headphones — output moves, speaker mutes.
3. Plug USB-C HDMI/DP — sink appears and audio routes; hear it on the monitor.
4. Record a short clip from the mic; inspect waveform/spectrum (non-silent, expected
   noise floor).
5. Play + record simultaneously (no xruns).
6. Reboot — routing and stack come back automatically.

---

## 4. Report contract (`REPORT-PWNAGE-104600.md`)

Units/config changed, `wpctl status`
before/after, routing matrix, audio waveform captures, reboot persistence and
rollback. End with `FULLY_DONE` / `PARTIAL` / `BLOCKED`.

---

## 5. 104000 addendum — verify after every deploy and after reboot

- Speaker playback (alarm, media, notification `nuxel-pow.mp3`).
- Microphone capture (`pw-record` 5 s, non-silent) **and** in-app voice messages
  (ZapZap, Signal, Vesktop) — cross-check with 104B00.
- USB-C→HDMI audio: external display/speaker receives audio (cross-check 104700).
- Headset hot-plug still routes correctly.
- Boot/preload audio (`nuxel-preloading-screen.mp4`) plays (104900).
- Verify again after the §4 reboot; if PipeWire runs inside
  `nuxel-audio-session.service`, confirm it comes up without manual intervention
  and the default source/sink are restored.
