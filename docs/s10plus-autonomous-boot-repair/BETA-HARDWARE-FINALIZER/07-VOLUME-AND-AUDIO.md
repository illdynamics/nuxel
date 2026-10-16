# 07 — VOLUME BUTTONS AND AUDIO

**Status: userspace control path implemented and measured against the device’s real
ALSA mixer; the OSD is published; **audio playback itself is NOT verified** and is
reported as unsupported until it is.**

## 1. What exists on the handset (measured)

```
$ cat /proc/asound/cards
 0 [beyondmadera   ]: beyond-madera - beyond-madera
 1 [aboxvdma       ]: abox_vdma - abox_vdma
 2 [aboxdump       ]: abox_dump - abox_dump
$ ls /dev/snd/ | head            # controlC0..C2, pcmC0D0p… (playback + capture)
$ command -v amixer alsactl aplay pactl pw-play wpctl
(all MISSING)
$ rpm -q alsa-utils pipewire wireplumber
alsa-utils is not installed / pipewire is not installed / wireplumber is not installed
```

So: kernel audio devices and **alsa-lib** are present, but there is **no** mixer tool,
no sound server and no player in this image.  Previous “Fedora packaging exists”
evidence therefore proved nothing about this device — which is why the manager talks to
alsa-lib directly and reports what it finds.

## 2. The control it uses

`snd_mixer_open/attach("default" → "hw:0")/load` then, in priority order,
`Master`, `Speaker`, `Headphone`, `Digital Volume`, `PCM`, `Playback`, else the first
active element with a playback volume.  On this handset the winner is

```
MIXER_READY element=Left AMP PCM Gain min=0 max=20 current=19
```

and every candidate decision is written to `/var/lib/nuxel/buttons`, so the choice is
auditable rather than assumed.  If no writable playback control existed, the OSD would
say “audio path unavailable” and the manager would report
`VOLUME_UNSUPPORTED reason=no-playback-element` — it never fakes a level.

## 3. Behaviour

* VOLUMEUP/VOLUMEDOWN: one step = 5 % of the mixer range, with a 400 ms debounce and
  then 250 ms autorepeat while held; values are clamped to the mixer’s own min/max.
* VOLUMEMUTE: toggles the element’s playback switch when it has one, and says so when
  it does not.
* The current value is published as an OSD document
  (`/usr/share/nuxel/runtime/osd.json`, i.e. inside the launcher’s own docroot) which
  `pwa/nuxel-home/js/osd.js` polls and renders as the visible volume indicator
  (percentage + bar), auto-hiding after 1.8 s.  Polling backs off to 10 s when there is
  no publisher, so it cannot hammer the static server.
* The same actions are reachable from the console (`nuxelctl volume up|down|mute`), the
  Settings Sound page and the hardware keys — one code path.

## 4. Live evidence

```
$ nuxelctl volume up ; nuxelctl volume down
/run/nuxel-buttons.cmd <- volume-up
/run/nuxel-buttons.cmd <- volume-down
$ cat /usr/share/nuxel/runtime/osd.json
{"schema_version":1,"kind":"volume","text":"95%","value":95,"max":100,"ts":1789434226}
$ cat /var/lib/nuxel/buttons
2026-09-15T01:03:46Z VOLUME element=Left AMP PCM Gain value=19 pct=95
```

The mixer value moved (and moved back) on the real card0 element.

## 5. Not claimed

* **No audio was played.**  There is no player in the image, and the mission forbids
  unbounded/loud playback during testing.  The route (card0 → RDMA0 → madera → speaker)
  is present in the kernel but its userspace wiring (UCM/ALSA state, abox routing) is
  unproven: `snd_mixer` exposes only the amp gain element we found, which is *not*
  evidence that a full PCM path works.
* Therefore the correct status is: **volume control path = working; audio output =
  unverified / not yet supported**, with the exact blocker recorded in
  `12-REMAINING-HARDWARE-BLOCKERS.md`.
* Hardware-key → mixer mapping is verified by the state file; the user’s listening
  confirmation is still required before “audio works” may be written anywhere.
