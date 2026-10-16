# Area 7 — Headphones and USB-C audio adapters (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED).
Owner action required? **Yes** — the test needs a human to plug in headphones or
a USB-C audio adapter and listen. This area is **human-dependent by definition**
and **must not gate any other briQ**: the repository-side detection and routing
logic is finished and offline-tested, and only the audibility observation is
deferred to the owner.

**Device truth used by this document.** The S10+ (SM-G975F) has a 3.5 mm jack on
the **Cirrus Logic CS47L93 (MADERA)** codec and a USB-C port that can carry a
**USB Audio Class (UAC)** digital adapter (which enumerates as its own ALSA card)
or an analog USB-C accessory through the codec AUX pins. Pixel BCM4390 /
Pixel 10 Pro XL documentation in this repository does **not** describe any of
this and was not applied.

---

## 1. Feature

Cable-audio on the S10+:

* **3.5 mm jack detection** from ALSA jack kcontrols (`amixer -c beyond-madera
  contents`) with the codec pin registers as corroboration;
* **USB-C accessory detection** from `/sys/class/typec/port*/data_role`, a new
  USB ALSA card in `/proc/asound/cards` and (when present) `lsusb`;
* a **revert-aware route decision** driven by
  `configs/nuxel/audio/jack-routes.json` (headphones / headset / USB-C UAC /
  analog accessory / speaker);
* the bounded diagnostic `tools/s10plus/a33/nuxel-headphone-diag.sh`
  (also `nuxelctl headphone …` / `nuxelctl headphones …`) with `status`,
  `jack`, `usbc`, `route`, `watch` and `tone` sub-commands.

Control **names are never invented**: they are discovered from the live card, and
a name is used only after it has been observed. If no jack control can be found
the verdict is `UNKNOWN` — never a guess, never a silent "speaker".

## 2. Why this matters

Plugging in headphones must silence the speaker and route playback to the jack;
unplugging must return to the speaker. Getting this wrong is both a usability bug
(a phone that keeps playing out loud with headphones in) and a safety bug (a
route that stays on the CS35L40 amplifier while the owner expects silence).
Separately, the mission forbids claiming that hardware works because code exists:
insertion is a state machine that *can* be proven offline, but whether sound
reaches the ear is an observation only the owner can make, so it is deferred here
and never auto-promoted.

## 3. Preparation

1. Handset powered on, booted into Nuxel, screen unlocked, console/SSH access.
2. **3.5 mm test:** a stereo 3.5 mm plug **and** a TRRS headset with a microphone
   (a headset with a mic exercises the `Headset` route; a plain plug exercises
   `Headphones`). Low-volume default is in force, so keep the phone near your ear
   only if you intend to hear it.
3. **USB-C test (digital):** a USB-C → 3.5 mm **DAC/adapter** or USB-C headset
   (USB Audio Class). **USB-C test (analog):** a passive USB-C → 3.5 mm adapter,
   if available — the two exercise different detection paths.
4. Zero-cost snapshot first (decides whether detection works before you listen):

   ```sh
   nuxelctl headphone status            # jack/USB-C state + route decision
   nuxelctl headphone status --json     # machine-readable, for the bridge/apps
   nuxelctl headphone jack              # jack controls + codec pin evidence
   nuxelctl headphone usbc              # USB-C evidence + ALSA cards
   nuxelctl headphone usb-role          # the gadget/host role conflict (read-only)
   ```

   If `status` reports `jack: UNKNOWN`, the jack kcontrol could not be read on
   this image. Stop and record that finding; do not "listen" to a guess.

## 4. Exact action

a. Start a bounded watch so the transition is logged while you plug and unplug:

   ```sh
   nuxelctl headphone watch 30     # logs every state change; applies NO route
   ```

b. **3.5 mm headphones:** with the watch running, plug the stereo plug in and
   confirm the logged transition to `jack=INSERTED route=Headphones`, then apply
   the route deliberately with the cap in force:

   ```sh
   nuxelctl headphone route --yes
   nuxelctl headphone tone 800 --yes     # low-volume, bounded (single audio impl.)
   ```

   Listen. Then unplug: the watch/`status` must return to `route=Speaker`.

c. **TRRS headset (with mic):** repeat with the headset. The route must become
   `Headset` (not `Headphones`); a control named like `Headset Mic Jack` is
   classified as the **microphone**, never as the output jack.

d. **USB-C adapter:** unplug the 3.5 mm first, then plug the USB-C adapter and
   confirm `nuxelctl headphone status` reports the UAC route
   (`USB-C Headset (UAC)`) or, for a passive analog accessory,
   `UNKNOWN_USBC_ACCESSORY`. Route and tone as in (b) only for a *recognised*
   accessory; an unknown one is refused by design.

e. Record the evidence:

   ```sh
   nuxelctl headphone status --json > /tmp/hp-after.json
   journalctl -b --no-pager | grep -i -E 'jack|headphone|headset|codec|madera' | tail -60
   ```

## 5. Expected result

* `nuxelctl headphone status` transitions `REMOVED → INSERTED` when the 3.5 mm
  plug goes in, and back when it comes out.
* The route decision is `Headphones` for a stereo plug, `Headset` for a TRRS
  headset, `Speaker` when nothing is plugged.
* A recognised USB-C audio accessory is reported as its own path
  (`USB-C Headset (UAC)`); an unrecognised one stays `UNKNOWN_USBC_ACCESSORY`.
* `nuxelctl headphone tone 800 --yes` renders a **low-volume** bounded tone and
  `nuxelctl audio pipeline` shows the DAC/PCM in `state=RUNNING` while it plays.
* **The owner hears the tone through the plugged accessory, and the speaker is
  silent while it is plugged.**
* On unplug, playback returns to the speaker (the revert rule).

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning / next action |
|---|---|
| `jack: UNKNOWN` even with the plug fully inserted | No jack kcontrol matched. Detection is unproven — record it; do **not** report "headphones work". |
| Route stays `Speaker` while the plug is in, but the tone is heard in the headphones | Detection/pin encoding mismatch; capture `nuxelctl headphone jack` and the codec pin dump. |
| Tone is heard **and** the speaker keeps playing | The route switched for playback but the speaker amplifier was never disabled; a real routing bug, capture the mixer delta. |
| No tone through the accessory, but the pipeline says `OK_DAC_RUNNING` | The DAC ran but the accessory path is silent: adapter/codec-AUX or cable issue, not a software PASS. Report as unproven audibility. |
| USB-C adapter not detected at all | Try the other adapter class (digital vs analog); capture `lsusb` and `nuxelctl headphone usbc`. |
| `BLOCKED_EXTERNAL_RESOURCE` on `route --yes` | `alsaucm` is not installed on the image; the decision is still valid but the switch cannot be applied. Package-completion issue. |
| `REFUSED` on `route --yes` | The accessory state is unproven or the accessory is unknown — intended behaviour, not a failure. |
| Headset reported as plain `Headphones` | The mic control was not seen. Capture the full `amixer -c beyond-madera contents` list. |

## 7. Diagnostic command / log path

* `nuxelctl headphone status|jack|usbc|route|watch|tone|usb-role` —
  `tools/s10plus/a33/nuxel-headphone-diag.sh`
* Route decision + revert policy: `configs/nuxel/audio/jack-routes.json`
  (installed to `/etc/nuxel/audio/jack-routes.json`)
* Evidence log: `/var/log/nuxel/audio-diag.log`
* Jack state record (written only after a real `route --yes`):
  `/var/lib/nuxel/audio/jack-state.json`
* Mixer/pin evidence: `nuxelctl headphone jack` and
  `/proc/asound/card*/codec#*`
* Offline regression:
  `python3 tools/s10plus/a33/tests/test-headphone-route.py` and
  `nuxel-headphone-diag.sh selftest` (seven jack/USB-C fixtures)

## 8. PASS / FAIL

* **PASS** — the route decision matches what was plugged, the owner **hears** the
  low-volume tone through the accessory, the speaker is silent while it is
  plugged, the route reverts to `Speaker` on unplug, and the status JSON plus the
  journal excerpt are attached to the report.
* **FAIL** — any of: detection stays `UNKNOWN`, no tone is heard, the speaker
  keeps playing with the plug in, no revert on unplug, or the accessory is not
  detected. Quote the exact `nuxelctl headphone status --json` line: the
  `route` and `rule` fields name the layer that failed.

## 9. The USB-C role conflict: the live console vs host peripherals

This is the sharpest risk in this area, and it is why the tooling is read-only
about the port role.

**The conflict.** The A32/A33 bring-up carries its **live USB console as a USB
*gadget*** (CDC-ACM: `/dev/ttyACM0` on the host, `ttyGS*` on the phone). That
gadget is the only debug path into the phone. A **host-mode** peripheral — a USB
Audio Class DAC/headset, a keyboard, a hub — needs the same port in **host**
mode. One port, two roles: they cannot both be true at once.

**What the tool does.** `nuxelctl headphone usb-role` reports, read-only:

* the Type-C role files (`/sys/class/typec/port*/data_role`, `power_role`),
* the gadget side (`/sys/class/udc/*/state`, the bound `usb_gadget` functions),
* whether a console device node is visible,
* and the explicit decision `ROLE_SWITCH=REFUSED-BY-THIS-TOOL`.

**Why refuse.** Switching the role *can be done* on many Type-C ports
(`/sys/class/typec/port0/data_role`), but on this device the switch is the one
action that can remove the engineer's own way back in. So the switch is **not**
performed by any repository tool. If the owner wants USB-C audio, the bounded
procedure below is the only sanctioned route, and it terminates in
`NEEDS_OWNER_TEST` / `BLOCKED_HARDWARE` rather than in a claim:

1. **Prefer the path that needs no role change.** The **3.5 mm jack** needs no USB
   at all, and a **passive analog USB-C accessory** goes through the codec AUX
   pins, not through a USB role change. Try those first.
2. **For a digital accessory use an ACTIVE (UAC) DAC/headset.** It enumerates as
   its own ALSA card — the path the tooling is built for. A *passive* adapter is
   **not** assumed to work: if it is not detected, the recommendation is an active
   DAC, and passive-analog support is reported `NOT_SUPPORTED_ON_DEVICE` rather
   than faked.
3. **Before any role experiment, record the recovery plan** (this is the
   precondition, not a formality):
   * the console device node and the exact host-side reconnect command
     (`scripts/s10plus-debug-pack/nuxel-live.sh` / `nuxel-console-host.sh`),
   * the current role values (copy `nuxelctl headphone usb-role` output into the
     report verbatim),
   * the value to restore the role to, and the fact that a **normal reboot**
     (never Recovery/Download Mode) re-establishes the boot-time gadget role,
   * confirmation that no flashing or partition action is involved anywhere in
     this plan.
4. **Only then**, with the recovery plan recorded, a bounded experiment is
   allowed: change the role, enumerate the adapter, then **restore the role**
   (or reboot normally) inside the same session, with the console output captured.
5. If the console is lost mid-experiment and does not re-establish itself on a
   normal reboot, **stop** and record `BLOCKED_HARDWARE`: do not escalate, and do
   not attempt a bootloader path (mission invariant).

Accepted verdicts for this section: `OFFLINE_TESTED` (the read-only report),
`NEEDS_OWNER_TEST` (a real headset), `NOT_SUPPORTED_ON_DEVICE` (passive analog),
`BLOCKED_HARDWARE` (the role cannot be switched without risking the console).
**No repository tool switches the role, and no claim is made from a report.**

## Current automatic evidence (repository, this build group)

* `tools/s10plus/a33/nuxel-headphone-diag.sh selftest` → 7/7 jack/USB-C fixtures
  PASS (`tools/s10plus/a33/tests/fixtures-p3/jack-*`).
* `python3 tools/s10plus/a33/tests/test-headphone-route.py` → all checks PASS
  (route logic, the microphone-before-jack ordering fix, refusal of an unknown
  accessory, no-apply-without-`--yes`, `BLOCKED_EXTERNAL_RESOURCE` when no UCM
  tool is present, bounded `watch`, tone refusal without `--yes`, the revert rule,
  the low-volume cap, this fragment's field completeness, and no flashing
  surface).
* Audibility is **not** claimed: it stays `NEEDS_OWNER_TEST` in
  `configs/nuxel/capabilities/connectivity-time-audio-buttons.json` until the
  owner records a listening result.
* Owner test registered as `NEEDS_OWNER_TEST` in area 7 of
  `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` (report group).
