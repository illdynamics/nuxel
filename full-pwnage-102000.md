# FULL-PWNAGE-102000 --- Nuxel USB-C HDMI Audio Routing, Detection, Override & Sound Settings

**Mission:** Make USB-C-to-HDMI audio work reliably on Nuxel, with
automatic routing when a real HDMI/DisplayPort-audio sink becomes
available, a persistent user-selectable manual output override, and
complete output-device controls in **Settings → Sound**.

**Target:** Nuxel mobile Linux OS, currently developed and tested
primarily on the Samsung Galaxy S10+ (`beyond2lte`, Exynos 9820), Fedora
43 userspace / systemd 258.11, with a headless Phoc + framebuffer-bridge
display arrangement on the S10+ and no assumed `/dev/dri` device.

**Execution style:** This is an engineering task, not a
documentation-only exercise. Inspect the actual repository and running
device, establish the current implementation and evidence, implement the
complete path, build/install/restart only what is safe, and test it. Do
not claim HDMI audio works merely because a connector, display, ALSA
card, or sink appears in a listing.

------------------------------------------------------------------------

## 0. Non-negotiable outcome

When a USB-C-to-HDMI adapter is connected and the HDMI/DP audio endpoint
is genuinely available:

1.  Nuxel detects the endpoint.
2.  The endpoint appears in **Settings → Sound → Output device** with a
    useful name (for example, `HDMI / USB-C display` plus the actual
    sink description).
3.  If the user has not explicitly selected a manual output override,
    Nuxel automatically routes new playback to that HDMI output.
4.  The output is actually usable: audio reaches the
    TV/monitor/receiver, not merely a software sink.
5.  When HDMI is disconnected or its audio endpoint disappears, Nuxel
    falls back to the previous valid output, normally the internal
    speaker, without leaving audio silent.
6.  When HDMI is reconnected, Nuxel redetects the endpoint and restores
    automatic routing if automatic mode is active.
7.  The user can manually select Speaker, HDMI, USB-C headphones/DAC,
    Bluetooth, or any other real available output in Settings → Sound.
8.  Manual selection must not be immediately overridden by hotplug
    automation.
9.  The user can return to **Automatic** at any time.
10. The selected mode and preference persist across application restarts
    and reboot, while unavailable hardware is never selected as an
    active sink.
11. The Sound settings page exposes current output, detected outputs,
    connection state, automatic/manual mode, volume, mute, and an
    audible test.
12. Existing speaker, Bluetooth, USB audio, USB-C headset, and
    USB-C-to-3.5mm behavior must not regress.

**Important:** A USB-C connector being present, USB-PD negotiation
succeeding, DP Alt Mode entering a state, an external display being
detected, or an ALSA card existing does not by itself prove HDMI audio
is available. Audio capability must be detected independently and
verified at the audio-server / ALSA level.

------------------------------------------------------------------------

## 1. Repository and runtime reconnaissance --- do this before changing code

Work from the actual Nuxel repository root. Do not assume paths from
this prompt are exact. Discover the project layout and use its existing
conventions.

### 1.1 Establish repository state

-   Record `pwd`, current branch, commit, and dirty working tree.
-   Do not discard, reset, overwrite, or reformat unrelated user
    changes.
-   Locate all audio, sound settings, USB-C, Type-C, display, DP Alt
    Mode, hotplug, device-manager, system service, and UI code.
-   Locate all `REPORT-*.md`, design notes, test fixtures, and prior
    implementation prompts relevant to audio/display.
-   Search for:
    -   `PipeWire`, `pipewire-pulse`, `WirePlumber`, `PulseAudio`,
        `pactl`, `wpctl`
    -   ALSA cards, PCM devices, UCM profiles, `alsa-card`, `snd_soc`,
        `hdmi`, `eld`
    -   USB Audio Class (`UAC`, `snd-usb-audio`)
    -   Type-C, USB-PD, CCIC, DP Alt Mode, connector events, udev
    -   `nuxel-displayd`, `nuxel-display-ctl`, `nuxel-wl-fb-ext`
    -   existing audio daemon/service and Sound settings page
    -   `nuxel-pow.mp3` and audio test controls.
-   Inspect the latest relevant history and the implementation
    associated with display work, including commit
    `b6154b67ec1e421729cea8053839ce9cfae9095d` if present. Do not assume
    it is checked out or that its described features are complete.
-   Identify the actual sound server and policy manager at runtime. Do
    not introduce a second competing sound server.

### 1.2 Capture a before-state evidence bundle

On the development host and target phone, where available, capture:

-   `uname -a`, OS release, kernel config/version, boot arguments.
-   Running audio-related processes and system/user services.
-   `wpctl status`, `pactl info`, `pactl list short sinks`,
    `pactl list sinks`, if those tools exist.
-   `aplay -l`, `aplay -L`, `arecord -l`, `amixer` controls, ALSA
    card/PCM sysfs details.
-   `/proc/asound/cards`, `/proc/asound/pcm`, `/sys/class/sound`,
    `/dev/snd`.
-   PipeWire/WirePlumber logs and journal entries.
-   udev properties and kernel logs for USB-C adapter
    connect/disconnect.
-   HDMI/DP ELD state where exposed, commonly under
    `/proc/asound/card*/eld*` or corresponding sysfs/kernel interfaces.
-   Available UCM profiles and active profile/port information.
-   Current default sink, active stream routing, volume, mute and
    profile.
-   Existing Nuxel sound configuration and persisted settings.

Commands must be guarded when unavailable; absence is evidence, not a
reason to fabricate output. Save diagnostics to a clearly named report,
for example `./REPORT-HDMI-AUDIO-102000.md`, and include timestamps and
exact commands/results. Redact secrets and private identifiers.

### 1.3 Establish the actual sound architecture

Determine whether Nuxel uses PipeWire + WirePlumber, PulseAudio, direct
ALSA, or another stack. Follow the existing architecture unless there is
a compelling, evidenced reason to change it.

If PipeWire is present: - Determine whether WirePlumber is the active
policy manager. - Inspect current default-node and route policy. - Use
supported PipeWire/WirePlumber APIs or commands for enumeration and
routing. - Do not parse human-readable CLI output as the sole production
API if a stable API is available. - Do not run multiple policy managers
or install a parallel PulseAudio daemon.

If direct ALSA is used: - Inspect card/PCM enumeration, mixer controls,
UCM and kernel drivers. - Build a small Nuxel routing abstraction that
can switch valid PCM outputs safely. - Do not hardcode `card 0`,
`device 0`, or unstable ALSA card indices.

If the current system has no functioning audio policy service, report
that as a real blocker and implement the smallest compatible missing
layer. Do not paper over missing kernel support with a fake sink.

------------------------------------------------------------------------

## 2. Understand USB-C HDMI audio as a separate capability

USB-C video and USB-C HDMI audio are related but distinct paths.

A typical USB-C display adapter may use: - DisplayPort Alt Mode over
USB-C lanes, with a DP-to-HDMI converter. - A USB hub plus a separate
USB Audio Class codec. - A DP audio transport path exposed through the
SoC/display/audio drivers. - A combination of these.

Do not assume every adapter exposes HDMI audio through the same
mechanism.

### 2.1 Detection sources to investigate

Correlate the following signals rather than relying on one event:

1.  USB Type-C partner / connector state.
2.  USB-PD and DP Alt Mode state, where supported.
3.  USB device enumeration and interface descriptors.
4.  USB Audio Class interfaces and `snd-usb-audio` binding, where
    applicable.
5.  ALSA card and PCM appearance/disappearance.
6.  Display/HDMI audio codec or SoC audio endpoint state.
7.  HDMI ELD (EDID-Like Data) validity and audio capabilities, where
    exposed.
8.  PipeWire/WirePlumber sink and port appearance.
9.  Sink availability state and profile availability.
10. Actual successful playback.

Use stable identifiers: - PipeWire node object serial / stable
properties where available. - ALSA long card ID, device ID and hardware
path. - USB vendor/product/interface and physical path when
applicable. - EDID/ELD-derived display identity where available.

Never persist transient ALSA card numbers or PipeWire object IDs as the
identity of a device.

### 2.2 HDMI audio endpoint validity

A candidate output should only be marked available when the actual audio
stack reports a usable output route/profile. Where ELD exists,
inspect: - ELD valid flag. - Monitor name and connection state. -
Supported audio formats / SADs. - Supported channel counts and rates. -
Codec/driver errors.

If ELD is unavailable on this hardware/driver path, document that and
use the strongest available evidence. Do not interpret missing ELD as
proof of either success or failure.

A display may be connected while its audio endpoint is absent. The UI
must represent this accurately, e.g.: -
`External display connected — HDMI audio unavailable` -
`HDMI audio available` - `HDMI audio reconnecting` -
`HDMI audio disconnected`

### 2.3 Keep the display and audio state machines coordinated, not conflated

The existing display work uses a state model described as:

`DISCONNECTED → PARTNER_NO_PD → PD_NO_DP → DP_NO_FB → DP_LINK_READY`

Inspect the real implementation and preserve its semantics. Do not add
audio states to the display state machine in a way that makes display
success depend on audio success.

Create a separate audio endpoint state model, for example:

`ABSENT → DISCOVERING → PRESENT_UNVERIFIED → AVAILABLE → ACTIVE`

with failure/recovery states as needed: - `UNAVAILABLE` -
`PROFILE_SWITCHING` - `RECONNECTING` - `ERROR`

The display daemon and audio manager may exchange events, but each
subsystem must retain its own source of truth.

When display hotplug happens: - Notify the audio manager that a
connector/partner event occurred. - The audio manager independently
checks the audio stack for a usable endpoint. - Retry discovery with
bounded backoff for a short, documented period to accommodate delayed
enumeration. - Cancel retries when disconnected. - Debounce duplicate
hotplug events. - Do not block display initialization on audio
discovery. - Do not assume the same adapter/monitor will always
enumerate the same way.

------------------------------------------------------------------------

## 3. Implement a robust audio output manager

Create or extend the existing Nuxel audio service rather than creating
duplicate services. Use the project's language, service model, logging,
configuration, and IPC conventions.

### 3.1 Required responsibilities

The audio manager must: - Enumerate actual output devices. - Track
stable device identities and changing availability. - Distinguish
physical outputs from virtual/monitor/null sinks. - Track active output
and user preference. - Support `automatic` and `manual` routing modes. -
Apply safe routing changes. - Preserve volume and mute sensibly across
output changes. - Handle device removal during active playback. -
Recover after audio-server restarts. - Publish events/state to Settings
and other Nuxel clients. - Expose diagnostics and a test action. - Avoid
polling aggressively when event-driven subscriptions are available.

### 3.2 Routing modes

Implement exactly these user-facing modes:

**Automatic** - HDMI/USB-C display audio is preferred when a verified
HDMI audio endpoint becomes available. - When HDMI audio disappears,
switch to the last valid non-HDMI output; prefer the internal speaker if
it is available. - If HDMI returns, route back to HDMI, provided the
user has not switched to manual mode. - If there is no HDMI audio
endpoint, use the normal Nuxel default output policy. - Automatic
routing must not unexpectedly select a newly plugged-in USB headset over
a user's existing explicit preference unless that is already the
established Nuxel policy. Document the priority order.

**Manual** - The user explicitly chooses an output. - Hotplug automation
must not override that choice. - If the selected output disappears,
immediately choose a safe fallback (internal speaker if available;
otherwise the sound server's valid default) while retaining the user's
preferred device identity as a pending preference. - If the manually
preferred device returns, restore it only if the product's existing UX
semantics support restoration; otherwise show it as available and
require explicit selection. Choose one behavior, document it, and test
it. - Switching to manual must be possible even when HDMI is
connected. - Selecting `Automatic` must immediately re-evaluate all
currently available endpoints and apply the automatic policy.

### 3.3 Suggested priority policy

Inspect current Nuxel conventions before finalizing. A reasonable
initial policy is:

1.  Explicit manual output selection (highest priority).
2.  Automatic HDMI output when a valid HDMI audio sink is available.
3.  Existing Nuxel automatic policy for other outputs.
4.  Internal speaker fallback.

Bluetooth behavior must not regress. If Bluetooth is connected and the
user explicitly selected it, HDMI hotplug must not steal audio. In
automatic mode, document how Bluetooth and HDMI priorities interact;
HDMI can be the preferred display output, but never override manual
intent.

### 3.4 Safe switching

-   Validate the target sink is present, available and not suspended due
    to an error.
-   Switch default output and move active streams where supported.
-   Avoid abrupt audio pops: use the sound server's supported ramp/fade
    or safe transition mechanism where practical.
-   If switching fails, restore the last known working output.
-   Never leave the user silently routed to a nonexistent sink.
-   Do not restart the entire audio stack for ordinary device changes.
-   Do not kill applications or terminate playback streams
    unnecessarily.
-   Keep per-device volume/mute policy consistent with existing Nuxel
    behavior.
-   Prevent feedback loops where a routing change triggers another
    policy change.
-   Serialize concurrent hotplug and user-selection operations.

### 3.5 Event handling and lifecycle

Handle: - Adapter inserted. - Display connected after adapter
insertion. - Display disconnected while adapter remains inserted. -
Adapter removed. - USB hub/USB audio codec enumerating late. - Audio
server starting after the display daemon. - Audio server restarting
while HDMI remains connected. - Screen lock/unlock. - Suspend/resume, if
supported. - Reboot with adapter already connected. - Rapid repeated
connect/disconnect. - Switching output while a stream is playing. - User
choosing manual output during an in-progress automatic switch.

Use event subscriptions first, with a bounded reconciliation scan at
service start and after audio-server reconnect. Ensure only one
authoritative manager owns policy.

------------------------------------------------------------------------

## 4. Settings → Sound UI

Extend the existing Settings application. Do not create a second
settings app or a separate floating audio panel.

### 4.1 Output section

Add a clear **Output** section with:

-   Current output name.
-   Output type/icon (speaker, HDMI/display, USB, Bluetooth, headset).
-   Connection/availability status.
-   `Automatic` selection.
-   A list of all real, currently available output devices.
-   Selected-device indicator.
-   Manual override state.
-   A clear way to return to Automatic.
-   Volume slider.
-   Mute toggle.
-   Test sound button.

Suggested layout:

``` text
Settings
  Sound

  OUTPUT
  Routing mode:  [ Automatic v ]

  Current output
  [ HDMI / USB-C display       Connected ]

  Available outputs
  ( ) Automatic
  ( ) Phone speaker
  (•) HDMI / USB-C display
  ( ) USB-C audio device
  ( ) Bluetooth headphones

  VOLUME
  [---------●----------] 70%

  [ ] Mute

  [ Test sound ]
```

This is an illustrative information hierarchy, not a mandate to copy a
visual design. Follow the existing Nuxel UI style, mobile sizing and
component conventions.

### 4.2 Interaction semantics

-   Selecting `Automatic` sets policy mode to automatic and immediately
    recalculates the best route.
-   Selecting a device sets manual mode and stores that device's stable
    identity as the user's preferred output.
-   If a selected device vanishes, show that it is disconnected and
    explain which fallback is active.
-   Do not show phantom devices, null sinks, monitor sources, or
    duplicate entries as physical outputs.
-   A disconnected but remembered manual preference may appear in a
    separate `Preferred device (disconnected)` status, not as a
    selectable available device.
-   UI must update when devices appear/disappear without requiring a
    Settings restart.
-   Do not display stale output names or stale connected badges.
-   Keep accessibility, focus, touch targets, keyboard navigation and
    screen scaling consistent with the rest of Nuxel.
-   Avoid controls that look interactive but do nothing.

### 4.3 Test sound

Use the existing `./assets/nuxel-pow.mp3` asset as the standard Nuxel
audio test if it is still present and appropriate.

-   The Test sound button plays the sound through the currently selected
    output.
-   On volume change, follow existing Nuxel behavior and play the test
    sound only if that behavior is already intended; avoid surprising
    repeated audio.
-   When the user confirms a route change, use the existing audio test
    convention if appropriate.
-   The historical desired validation includes playing
    `./assets/nuxel-pow.mp3` three times for a focused route test. Do
    not spam the sound on every internal event.
-   Test playback must not be confused with proof that sound physically
    reached the TV. Software success and physical confirmation are
    separate results.

### 4.4 Settings persistence

Persist: - routing mode (`automatic` / `manual`); - preferred stable
output identity; - last known working non-HDMI fallback, if useful; -
any per-device settings that the current system already persists.

Do not persist: - ephemeral PipeWire node IDs; - ALSA card index; -
transient object serials; - stale availability.

Use the existing Nuxel settings/config mechanism. Validate schema,
defaults and migration behavior. Make malformed or missing settings fall
back safely to Automatic. Do not write settings on every hotplug tick.

------------------------------------------------------------------------

## 5. Hardware and kernel investigation for the Galaxy S10+

The current primary target is the Samsung Galaxy S10+ (`beyond2lte`,
Exynos 9820). Prior work indicates: - Fedora 43 userspace / systemd
258.11. - Headless Phoc + framebuffer bridge. - No `/dev/dri` in the
current configuration. - USB-C display work has its own daemon/control
path. - The same USB-C-to-HDMI adapter, HDMI cable and TV work with a
Google Pixel 10 Pro XL, while the S10+ has had display-path issues. -
Earlier diagnostics mentioned `secdp=0`, `usbpd_ids=0000:0000`, and CCIC
negotiation/DP Alt Mode blockers. These are historical clues only;
recapture current evidence. - Earlier audio work established normal
internal speaker playback and Bluetooth operation, but physical HDMI
audio must be independently proven.

Investigate the actual Exynos audio/display/USB-C topology: - Kernel
configuration and modules. - Exynos audio machine driver / ASoC card
registration. - HDMI/DP audio codec or bridge support. - Type-C
controller and DP Alt Mode drivers. - USB-PD and CCIC/PD event chain. -
USB Audio Class support and `snd-usb-audio`. - Relevant device tree
nodes, overlays and firmware. - ALSA PCM devices and mixer controls. -
ELD reporting and codec state. - Any vendor-specific Samsung
audio/display components and whether they are enabled in this Nuxel
kernel.

Do not assume that the TV's HDMI audio endpoint is a USB Audio Class
device. Identify the actual transport on this adapter and SoC.

If the current kernel cannot expose an HDMI audio PCM/sink: 1. Prove the
missing layer with logs, kernel config, driver binding and device
enumeration. 2. Identify the exact required kernel
driver/config/device-tree/firmware work. 3. Implement it if it is safely
in scope and the source/build workflow exists. 4. If a kernel reflash is
required, do not silently initiate a risky flash. Produce a precise
prerequisite report with exact config symbols, drivers, modules,
firmware, DT changes, build artifacts, backup/rollback plan and
validation steps. 5. Do not fake an HDMI sink or claim success by
routing to a null sink.

Do not break the existing live USB console, USB networking, USB host
behavior or Type-C role switching. Respect known USB-C role conflicts
and existing display work.

------------------------------------------------------------------------

## 6. Diagnostics and observability

Add a Nuxel diagnostic command or extend the existing audio diagnostic
tooling. It should report, in a human-readable and machine-readable
form:

-   Audio server and policy manager.
-   Available physical outputs.
-   Stable output IDs and current names.
-   Active output.
-   Automatic/manual mode.
-   User-preferred output.
-   Fallback output.
-   HDMI connector/display state (as received from display subsystem).
-   HDMI audio endpoint state (independently detected).
-   ALSA card/PCM/profile.
-   ELD status/capabilities, if available.
-   PipeWire node/profile/port state, if applicable.
-   Last hotplug event and timestamp.
-   Last route decision and reason.
-   Last routing error.
-   Audio service health.

Provide a safe command/API to: - list outputs; - show status; - set
automatic mode; - select a specific available output; - test current
output; - collect a diagnostic bundle.

Use the existing Nuxel CLI conventions. Avoid exposing dangerous
arbitrary shell execution over IPC.

Logs should explain *why* a route was chosen, e.g.:
`automatic: HDMI audio endpoint became available; selected stable sink ...`
or
`manual: retaining user-selected phone speaker; ignoring HDMI hotplug`.

Do not log private audio content.

------------------------------------------------------------------------

## 7. Testing strategy --- tests are mandatory

Build a comprehensive test suite at multiple levels.

### 7.1 Unit tests

Test: - Stable device identity generation. - Device classification. -
HDMI audio endpoint availability. - ELD valid/invalid/missing cases. -
Automatic route selection. - Manual override protection. - Return to
Automatic. - HDMI disconnect fallback. - HDMI reconnect. - Missing
preferred device. - Duplicate and out-of-order events. - Delayed audio
endpoint enumeration. - Audio-server restart. - Device removal during
playback. - Failed route switch and rollback. - Settings persistence and
migration. - Invalid/stale IDs. - Concurrent hotplug and user selection.

### 7.2 Integration tests with fixtures/mocks

Use the project's existing fixture style. Simulate: 1. Speaker only. 2.
Speaker + HDMI connected and audio sink available. 3. Display connected
but HDMI audio unavailable. 4. Adapter inserted; HDMI sink appears after
delay. 5. HDMI removed during playback. 6. HDMI reconnected. 7. Manual
speaker selected; HDMI connected. 8. Manual USB audio selected; HDMI
connected. 9. Manual Bluetooth selected; HDMI connected. 10. Manual
device removed; fallback applied. 11. User returns to Automatic while
HDMI is already connected. 12. Audio server restart with HDMI connected.
13. Reboot/startup with HDMI already attached. 14. Rapid
connect/disconnect. 15. Invalid ELD / unsupported format. 16. HDMI sink
exists but profile cannot activate. 17. Route operation fails. 18. No
speaker fallback available.

Verify not only the selected default but also active stream movement and
fallback behavior where the test backend supports it.

### 7.3 Device tests

On the actual S10+: - Test internal speaker. - Test Bluetooth. - Test
USB-C audio device, if available. - Test USB-C-to-3.5mm DAC, if
available. - Test USB-C-to-HDMI with the same adapter, cable and TV
previously used. - Record exact hardware and connection topology. -
Connect HDMI before boot and after boot. - Unplug/replug while playback
is active. - Switch output manually in Settings. - Switch back to
Automatic. - Reboot with adapter attached. - Verify normal speaker
fallback after disconnect.

For every test record: - software sees endpoint? yes/no; - route
selected? yes/no; - playback stream starts? yes/no; - ALSA/PipeWire
reports errors? yes/no; - physical TV/receiver emits audible sound?
yes/no/NOT VERIFIED; - human confirmation method and result.

Never mark physical HDMI playback as PASS based solely on `aplay`,
`pw-play`, `paplay`, a successful process exit, a default-sink change,
or a visible UI state.

### 7.4 Audio test asset

Use `./assets/nuxel-pow.mp3` if present. Confirm it is a valid decodable
audio file and inspect its duration/format. Do not assume it exists or
is valid without checking.

Run controlled tests: - test current speaker output; - test HDMI
output; - test manual override; - test disconnect fallback; - test
reconnect auto-routing.

Do not repeatedly play it without purpose. The focused historical
route-validation convention is three plays per test scenario when
appropriate, with human confirmation of physical output.

### 7.5 Regression tests

All existing audio tests must continue to pass. In particular, locate
and run the existing seven offline headphone fixtures/routing tests and
any A49 pytest tests mentioned in prior work. Confirm the current count
and names rather than assuming those tests still exist.

Run project lint, type checks, unit tests, integration tests, build and
relevant smoke tests. Report unrelated existing failures separately; do
not conceal or relabel them as passes.

------------------------------------------------------------------------

## 8. Security, reliability and performance

-   Run services with least privilege.
-   Use existing system/user service boundaries.
-   Validate all IPC input.
-   Avoid shell interpolation and command injection.
-   Avoid world-writable state/config files.
-   Do not expose audio control APIs over the LAN unless explicitly
    intended and authenticated.
-   Rate-limit repeated hotplug/retry events.
-   Avoid busy loops and aggressive polling.
-   Keep memory and CPU overhead low on the S10+.
-   Avoid keeping the CPU awake unnecessarily.
-   Handle audio server and device failures gracefully.
-   Ensure logs rotate and diagnostic bundles do not include secrets.
-   Never break lockscreen, call audio, alarm/system sounds, or
    emergency audio routing if those features exist.

------------------------------------------------------------------------

## 9. Implementation constraints

-   Inspect before editing.
-   Preserve existing architecture and code style.
-   Do not replace working speaker/Bluetooth routing.
-   Do not create a fake HDMI sink.
-   Do not hardcode unstable ALSA card numbers or PipeWire object IDs.
-   Do not equate display connection with audio availability.
-   Do not claim NPU/GPU or hardware support without real evidence.
-   Do not modify kernel boot flags or flash the phone without a
    separately documented, approved reflash plan.
-   Keep changes focused on HDMI audio routing, output selection,
    Settings integration and necessary diagnostics.
-   Add comments for non-obvious policy decisions.
-   Update docs and configuration examples.
-   Ensure service startup ordering and recovery are robust.
-   Ensure a failed HDMI route returns to a known-good output.

------------------------------------------------------------------------

## 10. Definition of Done

The task is complete only when all applicable items below are satisfied.

### Core functionality

-   [ ] Real HDMI audio endpoint is detected independently from display
    connection.
-   [ ] HDMI audio appears in Settings → Sound when actually available.
-   [ ] Automatic mode routes audio to HDMI when the endpoint is usable.
-   [ ] HDMI disconnect falls back to a working output.
-   [ ] HDMI reconnect is redetected and auto-routing resumes in
    Automatic mode.
-   [ ] Manual output selection works.
-   [ ] Manual selection is never overridden by HDMI hotplug.
-   [ ] Returning to Automatic immediately re-evaluates endpoints.
-   [ ] Preferred routing mode/device persists safely across reboot.
-   [ ] Existing speaker, Bluetooth and USB audio routing still works.
-   [ ] Test sound button plays through the selected output.
-   [ ] No fake sink or false-positive HDMI status is used.

### Quality

-   [ ] Unit tests pass.
-   [ ] Integration/fixture tests pass.
-   [ ] Existing audio regression tests pass.
-   [ ] Build/lint/type checks pass.
-   [ ] Service restart and hotplug recovery work.
-   [ ] Settings updates live without restarting the UI.
-   [ ] Diagnostic report contains real evidence.
-   [ ] Physical HDMI audio is explicitly marked PASS only after audible
    confirmation.

### Final report

Create `REPORT-HDMI-AUDIO-102000.md` containing: 1. Executive summary.
2. Before-state architecture and evidence. 3. Root cause(s), with exact
files/drivers/log evidence. 4. Files changed and why. 5.
Service/config/UI changes. 6. Routing policy and stable identity design.
7. Kernel/firmware/DT blockers, if any. 8. Tests run and exact results.
9. Device test matrix. 10. Physical HDMI audio confirmation status. 11.
Reboot/hotplug persistence results. 12. Remaining blockers and exact
next steps. 13. Commit hash, if committed; do not commit unless
repository workflow and user intent permit it.

If the kernel/driver path prevents physical HDMI audio, finish all safe
userspace work, provide a precise blocker report and reflash
prerequisites, and clearly state that physical HDMI audio remains
unverified/not working. Do not declare the task fully done.

**Final instruction:** Make the real system work. Do not optimize for a
green test suite while the TV remains silent. The decisive result is
reliable automatic HDMI audio routing plus a working manual output
selector in Nuxel Settings → Sound, with honest physical validation.
