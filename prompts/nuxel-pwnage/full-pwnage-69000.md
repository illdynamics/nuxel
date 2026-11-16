# FULL-PWNAGE-69000 — NUXEL USB-C AUDIO, DISPLAYPORT/HDMI, NUXTREAM & OPEN MULTI-TRANSPORT CASTING MISSION

**Target implementation:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` (Exynos 9820) first.  
**Project:** Nuxel — native Fedora-based Linux mobile OS.  
**Mission class:** deep hardware/software investigation + implementation + UI/application + integration + owner-assisted physical validation.  
**Primary product:** NuXtream — Nuxel's open external-display and screen-streaming control centre.  
**Critical rule:** no feature may be marked working merely because a cable is detected, a sysfs node exists, a codec appears in a package list, a service starts, or a test fixture passes.

---

## 0. EXECUTIVE ORDER — DO NOT SKIM THIS SPECIFICATION

You are the lead Linux platform, kernel integration, audio, display, networking and Nuxel application engineer. Execute the entire specification against the current repository checkout. This is an implementation mission, not a research-only response and not a mockup-only task.

The owner wants to test two distinct USB-C audio accessories on the S10+:

1. **Samsung USB-C wired earphones connected directly to the phone's USB-C port.** Identify the exact accessory from USB descriptors/IDs during a real supervised test. Do not assume its protocol from the Samsung brand name. It may enumerate as USB Audio Class (UAC), and it needs the phone's USB controller in host/DFP mode.
2. **Beyerdynamic headphones with a 3.5 mm plug through a USB-C-to-3.5 mm adapter.** Establish whether that adapter contains an active USB DAC (normally a separate UAC audio device) or is a passive analog accessory. Do not conflate the two. An active UAC DAC and passive USB-C analog audio accessory mode are different hardware paths.

Normal Nuxel speaker audio already works. Preserve it. Implement reliable accessory detection, audio-node creation, route selection, audible playback, microphone handling where supported, and automatic return to speakers on unplug.

The owner also has a USB-C-to-HDMI cable/adapter. An external display/connection indication is now visible on the phone, but the TV remains blank. Your job is to find exactly which layer says “connected” and why actual pixels do not reach the TV. The chain must be verified from Type-C/CCIC and DisplayPort Alternate Mode negotiation through mux/PHY, display controller/scanout, connector, EDID/mode selection, compositor output, and visible TV pixels. Do not accept a UI indicator as proof of a real DP link or active scanout.

Create **NuXtream**, a first-party Nuxel application that controls:

- Local USB-C DisplayPort external displays: mirror and, where the compositor and hardware expose a genuine second output, extend the desktop.
- Output configuration: resolution, refresh rate, scale, orientation, primary output, arrangement and safe fallback.
- Open casting: mirror Nuxel to supported receivers over Wi-Fi, wired LAN/Ethernet, and USB networking where a real USB network link can be safely offered.
- Receiver pairing, connection state, quality controls, audio options, privacy/lock handling and session teardown.

Build Nuxel's own open, documented casting system instead of requiring Google Cast/Chromecast services, proprietary Google SDKs, proprietary receiver enrollment or Google account/cloud infrastructure. Borrow proven architectural ideas (receiver discovery, pairing, negotiation, adaptive bitrate, media sessions and receiver UX), but implement with open protocols and independently written code. Do not copy proprietary code, reverse engineer private protocols, impersonate Google devices, bypass receiver access controls, or claim compatibility with arbitrary televisions that have no compatible receiver.

You own the investigation and should discover additional related defects yourself. Fix confirmed, safe issues, write tests, wire the changes into the S10+ image, and document every hardware-only blocker honestly.

**Do not stop after producing a plan.** Read the source, trace the implementation, change it, build it, test it, review the diff, and repeat until every safe repository-side task is complete.

---

## 1. REPOSITORY-SPECIFIC BASELINE — FACTS YOU MUST RECONCILE

The supplied Nuxel source archive contains substantial groundwork. Treat the facts below as a starting point, not an immutable truth. A newer working tree or live handset may contain changes not present in this archive. Capture live state before changing anything and reconcile every discrepancy.

### 1.1 S10+ target identity and platform constraints

- Device: Samsung Galaxy S10+ SM-G975F, codename `beyond2lte`, Exynos 9820.
- Downstream Linux kernel family in the supplied tree: Samsung 4.14.253.
- USB-C/PD controller evidence in older captures: Maxim MAX77705 / Samsung CCIC/MUIC stack.
- The live USB console has historically been a USB gadget (CDC-ACM), with the phone acting as a USB device/UFP.
- The same physical USB-C port is required for USB host/DFP peripherals such as digital USB-C earbuds and active USB DAC adapters. One port cannot simultaneously be a host for an attached UAC device and a device/gadget connected to a PC unless the actual controller and a supported simultaneous topology demonstrate otherwise.
- Normal speaker audio already works. Avoid changing the working MADERA/ABOX speaker route while investigating accessory audio.
- The S10+ display is a Samsung S6E3HA9 AMOLED panel. The phone's internal display is separate from the external USB-C DP/HDMI output path.

Never apply S10+ hardware assumptions to the G7 Power or Pixel 10 Pro XL targets. New NuXtream code may be cross-device, but all hardware-specific code, kernel fragments, device manifests, and tests must be target-scoped.

### 1.2 Existing headphone/USB-C audio files

Important files found in the supplied repository:

- `configs/nuxel/audio/jack-routes.json`
- `tools/s10plus/a33/nuxel-headphone-diag.sh`
- `tools/s10plus/a33/nuxel-audio-diag.sh`
- `tools/s10plus/a33/nuxelctl`
- `tools/s10plus/a33/tests/test-headphone-route.py`
- `tools/s10plus/a33/tests/fixtures-p3/jack-*`
- `configs/alsa-ucm/beyond-madera/`
- `configs/wireplumber/nuxel-s10plus-audio.conf.d/51-nuxel-s10plus-audio.conf`
- `configs/s10plus/udev/90-nuxel-audio.rules`
- `docs/beta-finalization/manual-proof/07-headphones.md`
- `docs/beta-finalization/workqueue/briq-03d-headphones-usbc.json`

The existing diagnostics intentionally distinguish:

- 3.5 mm jack headphones;
- 3.5 mm TRRS headset with microphone;
- USB-C digital UAC accessory as a separate ALSA card;
- USB-C passive analog accessory as a distinct, uncertain class;
- absent/unknown accessories.

Existing verified offline results from the supplied archive:

- `bash tools/s10plus/a33/nuxel-headphone-diag.sh selftest` — 7/7 fixture cases pass.
- `python3 tools/s10plus/a33/tests/test-headphone-route.py` — all checks pass.

These are **offline detection and route-policy tests only**. They do not prove that the owner's Samsung USB-C earphones enumerate, that the Beyerdynamic headphones make sound through the actual adapter, that the speaker becomes silent when required, or that the route restores correctly on unplug.

The existing policy currently describes a USB-C UAC route and an analog accessory route. The manual proof document says an active UAC DAC is the supported path to pursue and does not assume a passive analog adapter will work. Preserve this distinction and correct any inaccurate or overconfident descriptions.

### 1.3 USB-C role conflict — critical existing safety constraint

`nuxel-headphone-diag.sh usb-role` is deliberately read-only and reports `ROLE_SWITCH=REFUSED-BY-THIS-TOOL`. Its comments and `docs/beta-finalization/manual-proof/07-headphones.md` explain why: the live USB console uses the UDC/gadget path, while an attached UAC DAC/headphone generally requires host mode. Switching role can immediately destroy the very console required to recover the phone.

Existing relevant document:

- `docs/s10plus-autonomous-boot-repair/TOUCHDOWN/USB-C-HOST-CAPABILITY.md`

That older capture reported Type-C port support for dual roles, while the live state was `data_role=device`, `power_role=sink`, an active USB gadget/UDC, and no enumerated host peripheral. This is evidence of a role conflict, not proof that the host path cannot work.

**Never remove the role-change refusal simply to make the accessory indicator light up.** Design a safe owner-supervised path with an alternate management channel and tested recovery before any role experiment.

### 1.4 Existing Type-C / HDMI diagnostics

Important files:

- `tools/s10plus/a33/nuxel-typec-diag.sh`
- `tools/s10plus/a33/tests/hw-subsystems/test-a49-typec-cast.py`
- `docs/A49/OWNER-TEST-EXTERNAL-DISPLAY.md`
- `docs/A49/DEPLOY-20261021-live.md`
- `docs/A49/FINAL-REPORT.md`
- `docs/A49/BASELINE.md`
- `docs/s10plus-autonomous-boot-repair/DISPLAY-BRINGUP.md`

The Type-C diagnostic is read-only and currently has verdicts such as `DP_ALT_MODE_ACTIVE`, `TYPEC_DP_NEGOTIATED`, `TYPEC_ENUMERATED_NO_DP`, `DRM_CONNECTOR_PRESENT` and `NO_TYPEC_NO_DRM`. It enumerates Type-C altmode directories and DRM connector `status` values. It does not yet prove EDID validity, active CRTC/plane scanout, a real frame update, or a visible picture on the TV. Improve its evidence quality and schema.

A previous A49 deployment receipt recorded that Type-C existed but no DP altmode or DRM connector was exposed at that earlier point in time. The owner now reports seeing an external-display-connected state, so **do not assume the older state is still current**. Capture current live evidence and identify what changed.

The A49 external-display owner test expressly warns to distinguish:

- DisplayPort Alternate Mode through a USB-C-to-HDMI protocol adapter;
- DisplayLink USB graphics adapters;
- passive or active HDMI conversion accessories.

These technologies have different driver and pipeline requirements. Do not treat them as interchangeable.

### 1.5 Current graphics path is a major architectural clue

`tools/s10plus/a33/nuxel-wl-fb.c` documents that the supplied S10+ image previously had:

- `CONFIG_DRM` disabled in the running 4.14 kernel;
- no `/dev/dri` and an empty `/sys/class/drm` at the time of that capture;
- Phoc/wlroots running a headless output with the pixman renderer;
- a custom `nuxel-wl-fb` bridge using `zwlr_screencopy_manager_v1` shared-memory frames and `/dev/fb0` to drive the internal AMOLED.

The bridge was designed for the internal panel, not as a multi-output DRM/KMS backend. Its presence alone cannot provide a second physical external display. If current code or the live kernel has moved beyond this design, establish that with live evidence.

The older `docs/s10plus-autonomous-boot-repair/DISPLAY-BRINGUP.md` contains DECON/DSIM panel and framebuffer findings. It describes the internal Samsung DECON/DSI path. Do not assume that the internal DSI connector automatically provides DP Alt Mode output. Identify the actual external video controller/PHY/mux path in kernel source, device tree, vendor driver sources and hardware documentation.

### 1.6 Existing casting diagnostics are not a casting product

Files:

- `tools/s10plus/a33/nuxel-cast-diag.sh`
- `tools/s10plus/a33/tests/hw-subsystems/test-a49-typec-cast.py`
- `docs/A49/OWNER-TEST-CAST.md`

The existing probe checks for Wi-Fi P2P hints, screencopy/capture tools, GStreamer encoder element names and some network interfaces. Its verdicts are candidates, not working screen streaming. The comments correctly say a Miracast button must not appear unless a real capture/transport/encoder pipeline functions.

Important baseline test nuance: in the supplied tree, directly running the pytest file as a plain Python script does not execute the test functions. Run it with pytest:

```sh
pytest -q tools/s10plus/a33/tests/hw-subsystems/test-a49-typec-cast.py
```

This passed seven tests in the audit. However, `nuxel-typec-diag.sh selftest` and `nuxel-cast-diag.sh selftest` both reported zero fixtures. Repair these inconsistent test surfaces: selftest must run real fixtures/tests or report that pytest is the authoritative test command. Never silently return success with zero tests.

---

## 2. REQUIRED FIRST ACTION — REPOSITORY AND DEVICE BASELINE

Before editing:

1. `git status --short --branch`, `git rev-parse HEAD`, `git diff --stat`, `git diff --`, `git submodule status` if applicable. Record owner changes; do not overwrite them.
2. Identify active device target using the repository's device-selection mechanisms. Confirm this mission is for `s10plus`/`beyond2lte`.
3. Read the complete files named in §1, plus all referenced source files and package/image installers.
4. Map every build, image, package, systemd, udev, app registry, PWA cache and release path that affects the S10+ image.
5. Establish whether the current kernel source/build is the same as the live phone's running kernel. Capture the exact kernel release, config, DTB identity, relevant modules, firmware and boot ID from existing safe diagnostics if available.
6. If an existing live SSH/USB console is already available, gather read-only captures. Do not initiate a USB role swap, DP mux change, display mode write or service restart merely to gather evidence.
7. Save a timestamped baseline under `docs/pwnage-69000/evidence/baseline/` (or the repository's current mission-evidence convention).
8. Run the focused offline tests listed in §12 before changes. Capture exact stdout, stderr and exit codes.

Baseline commands to consider, adapting to the actual installed command names and root environment:

```sh
nuxelctl headphone status --json
nuxelctl headphone jack
nuxelctl headphone usbc
nuxelctl headphone usb-role
nuxelctl typec status --json       # add this alias if missing; existing direct command is below
nuxel-typec-diag.sh status --json
nuxel-cast-diag.sh status --json
nuxelctl audio pipeline
wpctl status
aplay -l
arecord -l
cat /proc/asound/cards
lsusb -t
lsusb
ls -l /dev/dri /dev/fb* 2>/dev/null
find /sys/class/drm -maxdepth 3 -type f -print 2>/dev/null
find /sys/class/typec -maxdepth 5 -type f -print 2>/dev/null
systemctl --no-pager --type=service --state=running
journalctl -b --no-pager -k | grep -Ei 'typec|max77705|dp|displayport|dptx|decon|drm|hdmi|usb|snd|audio|codec|pipewire|wireplumber'
```

Run only commands that are read-only and available. Record missing commands as missing rather than installing or changing the live phone during baseline.

---

## 3. MISSION A — MAKE USB-C HEADPHONES AND DAC ADAPTERS ACTUALLY WORK

### 3.1 Build a truthful accessory identity model

The existing code has broad heuristics. Improve them into a structured, inspectable state model. At minimum distinguish:

- `ABSENT`
- `USB_DEVICE_DETECTED_UNCLASSIFIED`
- `USB_AUDIO_UAC1`
- `USB_AUDIO_UAC2`
- `USB_AUDIO_UAC_UNKNOWN_VERSION`
- `TYPEC_AUDIO_ACCESSORY_ANALOG` only if the CCIC/Type-C controller exposes positive, model-correct evidence for it
- `JACK_HEADPHONES`
- `JACK_HEADSET_WITH_MIC`
- `USB_ROLE_BLOCKED_BY_GADGET`
- `USB_ENUMERATION_FAILED`
- `AUDIO_CARD_PRESENT_NO_OUTPUT_NODE`
- `OUTPUT_NODE_READY`
- `PLAYBACK_TEST_PENDING_OWNER`

Do not classify every device connected to USB-C as headphones. Use the real Type-C partner/altmode/accessory state, USB descriptors, VID/PID, interface class/subclass/protocol, ALSA card creation, `snd-usb-audio` binding, PipeWire/WirePlumber node state and udev events. Treat missing evidence as unknown.

For each attached device, capture safe identifiers (vendor/product IDs, product string, interface descriptors and ALSA card/node names). Do not collect unrelated device serial numbers unless needed and explicitly documented; redact them from ordinary logs where possible.

The Samsung USB-C earphones must be identified by their actual model/USB descriptors during owner testing. Do not hard-code a Samsung VID/PID guessed from the product family. The Beyerdynamic 3.5 mm headphones themselves are passive analog headphones; the USB-C dongle decides the actual transport. Determine if the dongle enumerates as a USB Audio Class DAC. A USB-C-to-3.5 mm cable without a DAC may be a passive audio accessory and may not be supported by this phone's current port path.

### 3.2 Solve the one-port role conflict safely

This is a gating engineering issue, not a documentation footnote.

Investigate:

- MAX77705 CCIC/PDIC/MUIC event handling and current Type-C data/power roles;
- DWC3 controller role-switch wiring and its actual host/device support;
- whether an xHCI host controller is registered and enabled in this kernel/DT;
- whether role switching is exposed through a supported kernel API, sysfs role-switch class or vendor notifier (do not assume a writable `data_role` sysfs file exists);
- how the live CDC-ACM gadget is bound, whether it is the only active console, and whether the USB gadget can be safely detached and rebound;
- whether a composite gadget can preserve CDC-ACM and add CDC-ECM/NCM networking, and whether the controller's endpoint budget and driver support that configuration;
- whether the accessory's own current/voltage needs are safe and within the port's power limits;
- whether the HDMI adapter requires DP Alt Mode in a source/DFP configuration or can negotiate in the current topology.

Design a reversible, owner-consented role transition only if the hardware and driver API support it. Preconditions:

1. A second management path is already proven alive (for example Wi-Fi SSH from a known host, or a verified Ethernet route). “Wi-Fi appears connected” is insufficient; execute a real SSH round trip first.
2. Capture the current Type-C roles, UDC/gadget state, host reconnect command, USB serial identity and recovery route.
3. Provide a bounded watchdog/rollback action that attempts to restore the original gadget role if the test fails. The watchdog must be independent of the USB console being switched.
4. The transition must be explicit and owner-triggered, never automatic on accessory insertion.
5. If a safe management path or supported role-switch API is unavailable, leave role changes disabled and report the exact hardware blocker. Do not strand the phone.

Do not change USB roles in offline tests. Do not unbind the only console gadget automatically. Do not reboot or enter recovery to recover from a role test unless the owner separately approves a specific procedure.

### 3.3 Complete USB Audio Class support end to end

For any real UAC accessory:

- verify USB host enumeration and power;
- verify `snd-usb-audio` binds without errors;
- parse card and device descriptors rather than assuming the first card index;
- detect UAC1/UAC2, playback/capture streams, sample rates, bit depths, channel maps, clock feedback/async endpoints and quirks;
- ensure ALSA PCM nodes appear;
- ensure PipeWire enumerates a device, profile, sink and optionally source;
- ensure WirePlumber selects a stable profile and correct route;
- configure safe default routing without hardcoding transient ALSA card numbers;
- handle hotplug, duplicate events, device reset and unplug while playing;
- gracefully return to internal speakers when unplugged, and avoid leaving the default sink pointing to a vanished node;
- preserve microphone input if the accessory exposes one, and do not claim mic support unless tested;
- keep the speaker amplifier muted only while the correct wired route is actually active; restore it on unplug/error.

Investigate UCM2 support. UAC devices frequently expose their own ALSA card and should not be routed using the internal `beyond-madera` UCM profile. Do not blindly run `alsaucm -c beyond-madera` for a USB sound card. Use PipeWire/WirePlumber device profiles and node priorities for USB audio.

Implement an event-driven hotplug monitor using udev/libudev, PipeWire metadata/events or an equivalent robust mechanism. Avoid one-second permanent polling. Debounce connect/disconnect sequences, handle races, and make transitions idempotent.

### 3.4 Samsung wired USB-C earphones test

Create an owner test procedure specifically for the direct Samsung USB-C earphones:

1. Record earphone model/markings and phone software build.
2. Confirm second management channel before disconnecting USB CDC console.
3. Use the explicit, bounded USB host-mode procedure only after its prerequisites are proven.
4. Capture `lsusb -v` (or focused descriptor output), `dmesg`, Type-C roles, ALSA cards, PipeWire nodes and the NuXtream/Nuxel audio state.
5. Confirm exact UAC version, product identity and playback stream support.
6. Apply a safe volume cap (start at or below the existing 50% default; ensure no automatic jump to 100%).
7. Play a short bounded 440/500/800 Hz test signal and a known spoken audio clip at a conservative level.
8. Owner confirms sound is heard through both sides, no speaker leakage occurs, volume control works and playback stops/returns correctly on unplug.
9. Test microphone only if the earphones have one and the hardware exposes a capture stream. Use a short local recording and keep it private.
10. Restore the original USB gadget role or close the temporary host session and verify the USB console can reconnect.

### 3.5 Beyerdynamic 3.5 mm headphones through USB-C adapter test

First inspect the USB-C adapter separately from the headphones:

- Is it a UAC DAC with USB descriptors and a `snd-usb-audio` ALSA card?
- Is it a passive analog accessory using Type-C audio accessory mode?
- Is it a proprietary/unsupported adapter?

For a UAC DAC, follow §3.3 and the same safe host-mode process. Test stereo output with the Beyerdynamic headphones at low volume; verify L/R channels, no distortion, no speaker leakage, and unplug fallback. If the adapter is passive analog and this phone/kernel/CCIC path does not support it, report `NOT_SUPPORTED_ON_DEVICE` accurately. Recommend a standards-compliant active USB Audio Class DAC; do not patch an unsafe analog route to make a generic accessory appear detected.

### 3.6 Audio route correctness and safety

- Keep existing working built-in speaker audio intact.
- Keep the existing MADERA 3.5 mm analog jack handling intact where that physical 3.5 mm jack is used directly.
- Add a separate USB UAC route model; do not conflate internal codec UCM with UAC card routing.
- Use stable object paths/device IDs, not ALSA card numbers alone.
- Respect current Nuxel audio volume ceiling and 50% default.
- Add an emergency “return to Phone speaker” action that never raises volume.
- On service failure, restore a safe internal speaker route or report no valid sink; never route to an absent device.
- Add telemetry: accessory identity, state transitions, route decisions, PipeWire node IDs, errors and timestamps. Redact user data.

---

## 4. MISSION B — GET USB-C DISPLAYPORT/HDMI OUTPUT TO SHOW REAL PIXELS

### 4.1 Discriminate the link type before making code changes

The owner reports seeing an external-display-connected indication but a blank TV. Establish which exact signal caused the indication. Possibilities include:

- Type-C partner attach only;
- charger/PD attach;
- DP Alt Mode VDM discovery but no successful configuration;
- DP Alt Mode entered/configured but PHY/mux/HPD is wrong;
- HDMI adapter's own USB Billboard/error interface;
- external connector status changed but no active display pipeline;
- DisplayLink or other USB graphics device, not DP Alt Mode;
- a stale UI/status value from a previous connection.

Never infer successful DisplayPort from “USB-C attached” or from a `connected` string alone.

### 4.2 Trace the exact S10+ video path

Inspect the exact 4.14.253 vendor kernel source and the phone's matching device tree, not only upstream Linux documentation. Find:

- MAX77705 CCIC/PDIC firmware and DP Alt Mode VDM handling;
- Type-C port, partner, SVID/mode discovery, DP pin assignment, status/configuration and HPD events;
- Type-C mux and orientation switch implementation;
- SBU routing, DP AUX handling, lane polarity/orientation and redriver/retimer if present;
- Exynos 9820 display output/DP transmitter/PHY blocks and their register/clock/reset/power-domain wiring;
- display controller (DECON or other) external output driver and DRM bridge/encoder/connector support;
- EDID/DDC/AUX reads, hotplug event propagation and mode enumeration;
- external connector resources in DTS/DTBO and regulator/clock/GPIO references;
- actual kernel config options and driver registration for each of these nodes.

Search all vendor kernel source, build scripts, proprietary vendor references and known working Samsung S10/DeX sources that are legally accessible. Record commit/source provenance and license. Do not copy proprietary blobs or code without a compatible license. Do not guess register addresses, GPIO numbers, regulator names, PHY parameters or lane maps.

The external HDMI dongle is a protocol adapter: DP Alt Mode commonly feeds a USB-C-to-HDMI converter. HDMI Alt Mode is a distinct standard and should not be assumed. See official VESA DP-over-USB-C information and the USB-C-to-HDMI adapter explanation: `https://www.displayport.org/displayport-over-usb-c/` and `https://www.displayport.org/faq/`. Treat any adapter-specific EDID or HDCP constraints as separate from generic DP support.

### 4.3 Improve the Type-C/DP diagnostic to prove each stage

Expand `nuxel-typec-diag.sh status --json` into a documented versioned schema containing, where observable:

- port name, role, power role, port type, operation mode, partner identity;
- SVIDs/modes and discovered DP Alt Mode path;
- DP mode entry/configuration status, pin assignment, HPD high/low and orientation/mux state if available;
- USB Billboard descriptor/error state if present;
- DRM device, driver, card, connector, connector type, connector status;
- EDID availability, checksum/parse result, manufacturer/product, supported modes and preferred mode;
- encoder/CRTC/plane binding and active mode if DRM/KMS exists;
- fbdev outputs and current internal display output backend;
- display-controller/PHY driver binding and relevant kernel messages;
- whether `wlr-randr` sees an output and what modes it exposes;
- whether a compositor output has been created;
- whether the external output has received a successful frame commit;
- explicit `visible_output_verified=false` until owner confirms TV pixels.

Add distinct, unambiguous verdict stages, e.g.:

`NO_TYPEC_PARTNER`, `PARTNER_ATTACHED`, `DP_SVID_DISCOVERED`, `DP_MODE_ENTERED`, `DP_LINK_CONFIGURED`, `HPD_ASSERTED`, `EDID_VALID`, `KERNEL_CONNECTOR_CONNECTED`, `MODE_AVAILABLE`, `CRTC_ACTIVE`, `COMPOSITOR_OUTPUT_CREATED`, `FRAME_COMMITTED`, `VISIBLE_OUTPUT_NEEDS_OWNER_CONFIRMATION`, `DISPLAYLINK_DEVICE_DETECTED`, `UNSUPPORTED_ADAPTER`, `UNKNOWN`.

A higher-stage verdict requires evidence from all prior stages. Keep raw observations in JSON for auditability. Do not reduce all these states to a single “connected” boolean.

Fix current diagnostic gaps:

- handle absent and symlinked sysfs class nodes correctly;
- handle Type-C class implementations that expose altmodes in more than one directory shape;
- do not treat any path containing `displayport` as proof that mode entry succeeded;
- read attributes such as `svid`, `mode`, `active`, `status`, `vdo` or equivalent only if they actually exist;
- inspect DRM `modes`, `edid`, `enabled`, `dpms`, `status`, `uevent` where present;
- use read-only `modetest`/DRM inspection only when `/dev/dri` and a suitable driver are present;
- do not open a display control device or trigger modesetting from the default diagnostic;
- return nonzero/explicit `NO_FIXTURES` when a selftest has no cases.

### 4.4 Explain and repair the current blank-TV condition

The current internal display bridge is not a substitute for an external output driver. It uses a headless Phoc output and a shared-memory-to-fbdev bridge for the internal AMOLED. Determine whether the correct architecture is:

1. Add/enable the real external display DRM/KMS path and expose the DP connector to wlroots/Phoc; or
2. Implement a supported vendor DECON external output/DP path and bridge it to the existing display stack; or
3. Identify that the current kernel/board configuration lacks essential hardware support and prepare a targeted, source-backed kernel/DT/firmware implementation plan.

Prefer a standard DRM/KMS output path where the actual driver and silicon support it, because it allows compositor-level output management. Do not add a fake `HDMI-1`/`DP-1` connector in userspace unless it is backed by real modeset/scanout hardware.

If the current image has no DRM, document the exact reason and the minimal safe migration plan. Do not destabilize the internal AMOLED path. The existing framebuffer bridge must continue to work until a tested replacement for both internal and external outputs is available.

### 4.5 Build a staged external-display validation path

Stage 0 — inventory only: no role changes, no modesetting, no panel/mux writes. Gather evidence.  
Stage 1 — Type-C/PD/Alt Mode detection. Confirm the partner and mode negotiation.  
Stage 2 — HPD/AUX/EDID. Verify EDID and supported modes.  
Stage 3 — kernel connector and mode list.  
Stage 4 — compositor output creation and one conservative mode (start at 1280x720@60 or a lower supported mode; do not assume it is available).  
Stage 5 — visible test pattern/frame. Use a known Nuxel test pattern and verify output on the TV.  
Stage 6 — UI mirroring and extension.  
Stage 7 — unplug/replug, orientation, hotplug, suspend/resume, audio and long-duration testing.

Use conservative link rates, resolutions and refresh modes initially. Select modes only from EDID/kernel-advertised modes. Never force 4K, high refresh, unusual lane mappings or undocumented PHY values.

### 4.6 Mirror versus extend — define them truthfully

- **Mirror/clone:** the same desktop content is presented on the external output. The compositor or output hardware must actually clone/duplicate the source buffer or render a second output.
- **Extend:** the compositor sees an independent second output, with its own geometry, mode, scale, transform, arrangement and possibly primary-output role. This is not the same as streaming a copy of the existing screen.
- If there is only one compositor output and the hardware offers no second connector, the UI must say the output is not available. Do not emulate “extend” as a cropped or scaled mirror and label it extend.
- Keep the internal AMOLED active by default. Allow an explicit external-only mode only after safe output switching and a recovery shortcut are proven.
- When the external display is removed, restore the internal panel and its original geometry automatically.
- Preserve the correct touch mapping for the phone panel; the external monitor is not necessarily touch-enabled.

---

## 5. MISSION C — DESIGN AND IMPLEMENT NUXTREAM AS A FIRST-PARTY APPLICATION

### 5.1 Product architecture

Create **NuXtream** as a user-facing Nuxel application, with a native system backend. It must be a real app in the repository's app registry and image build, following existing Nuxel PWA conventions and shared shell components. Do not create a standalone HTML mock that is not launchable through Nuxel Home/NuXtore.

Expected layers:

1. **NuXtream PWA/app** — `pwa/nuxel-apps/nuxtream/` (or the repository's correct canonical app path after checking conventions).
2. **`nuxtreamd` system/user service** — device discovery, session state, capabilities, permissions, stream lifecycle and hardware arbitration.
3. **Typed RPC/API contract** — integrate with the existing Nuxel bridge/D-Bus/HTTP RPC architecture. The app must not shell out directly or gain root.
4. **Display backend** — query and operate through the actual compositor output-management protocol or a narrow privileged helper with strict allowlisted operations.
5. **Cast backend** — capture, encode, transport, receiver negotiation, pairing and lifecycle.
6. **Receiver application/reference** — browser receiver and documented native receiver SDK/protocol so third-party devices can implement compatibility.
7. **Packaging** — systemd, permissions, dependencies, icons, app registry, NuXtore metadata and tests included in the correct S10+ image.

Before creating files, inspect at least three existing PWA apps, the app registry schemas, bridge RPC conventions, app launcher metadata, NuXtore discovery and image build manifests. Follow those real conventions.

### 5.2 NuXtream information architecture

Build a polished Nuxel-style UI consistent with current design tokens, phone navigation, small displays and the external monitor use case. Required screens/tabs:

**Overview**
- Internal display and external display cards.
- USB-C connection state with the actual current stage (partner/Alt Mode/EDID/connector/output/pixels).
- Audio accessory card (USB-C earphones/DAC identity, profile and active sink).
- Active cast sessions, receiver name, transport, resolution, frame rate and latency where measured.
- Clear disabled/unsupported states with actionable explanations.

**Displays**
- Mirror / Extend / Internal only / External only where supported.
- Connected output list with connector name, make/model from EDID, supported modes and active mode.
- Resolution, refresh rate, scale and orientation controls using only advertised values.
- Display arrangement canvas for real independent outputs.
- “Make primary” only where compositor supports it.
- Test pattern button and restore button.
- Auto-revert timer/confirmation for risky external-only changes.

**Cast**
- Discover compatible receivers on Wi-Fi and wired LAN.
- Show USB network receiver when USB Ethernet gadget/host link is truly configured.
- Pair with QR code or short-lived numeric confirmation.
- Mirror Nuxel screen / share a selected window if compositor security permits / send selected media as a separate feature.
- Choose transport: automatic, Wi-Fi, wired LAN, USB network. Do not show unavailable transports as selectable.
- Quality controls: adaptive, 720p, 1080p and frame-rate ceilings only when encoder/capture capability supports them.
- Audio share toggle, default OFF until permissions and loopback capture work.
- Stop casting, revoke receiver, forget paired device.

**Receivers and Pairing**
- Paired receivers, trust expiration, remove device, revoke all.
- Receiver compatibility/capabilities and version.
- Generate one-time pairing code, rotate/revoke key.
- No account/cloud requirement for local casting.

**Diagnostics**
- Copy/share a redacted diagnostic bundle.
- Display and audio test wizards.
- Show exact failure stage and logs.
- Export JSON and human-readable report.

### 5.3 NuXtream must be capability-driven

The UI must consume real `nuxtreamd` capabilities, not hardcoded marketing booleans. Define an API such as:

- `capabilities.get`
- `display.outputs.list`
- `display.output.get`
- `display.output.set_mode`
- `display.mirror.set`
- `display.extend.set`
- `display.layout.set`
- `display.test_pattern.start|stop`
- `audio.accessories.list`
- `audio.route.select`
- `cast.receivers.discover`
- `cast.pair.begin|confirm|revoke`
- `cast.session.start|status|stop`
- `cast.settings.get|set`
- `diagnostics.collect`

Names can be adjusted to existing Nuxel RPC style, but document one typed contract with schema versioning. Every mutating call needs permission validation, bounds checking, audit logging, idempotency and explicit error responses. The PWA must not write arbitrary sysfs paths, invoke `modetest` or execute shell strings.

### 5.4 Integration details

- Add app metadata and manifest, service worker/cache bump, icon/asset, registry record and app navigation.
- Add to NuXtore/app inventory and S10+ package/image file manifest.
- Add all daemon, protocol schemas, policy files, udev/systemd rules and optional binaries to the installer.
- Verify the actual clean S10+ image has all runtime dependencies, not merely the source tree.
- If app registry supports device availability, NuXtream should appear on S10+ and show capability-specific UI on other targets rather than exposing unsupported controls.
- Do not claim cross-device display hardware support until a device backend exists.
- Ensure service restarts and upgrades preserve pairings securely and do not silently erase user settings.

---

## 6. MISSION D — BUILD AN OPEN NUXEL CAST ALTERNATIVE (NO GOOGLE VENDOR LOCK-IN)

### 6.1 Product promise and compatibility boundaries

The product goal is an open, interoperable way to mirror or stream from Nuxel to devices the user controls. There is no universal protocol accepted by every smart TV, streaming stick, tablet and desktop. A receiver needs to support at least one protocol or install a NuXtream receiver app/web page.

Do not promise “casts to absolutely any device”. Implement:

- a documented open sender protocol;
- a browser-based receiver that works on modern standards-capable browsers;
- a reference Linux receiver;
- a documented native receiver API/SDK so future Windows/macOS/Linux/Android/iOS/TV clients can interoperate;
- optional Miracast/Wi-Fi Display support only if the S10+ Wi-Fi P2P stack and receiver interoperability are actually demonstrated.

No mandatory Google account, Google Cast SDK, Google cloud service, proprietary Google discovery or Chromecast private protocol. Do not use the brand “Chromecast” for the product. NuXtream is the product name.

### 6.2 Separate the three different user experiences

1. **Physical external display (USB-C DP Alt Mode):** direct display pipeline. The monitor is an output of the compositor. Mirror and Extend are display-output modes.
2. **Network/USB screen mirror:** send captured desktop frames/audio to a receiver. This is a streaming session, not a compositor output.
3. **Network/USB media cast:** send a media URL or a local media stream for the receiver to play independently. This is not the same as screen mirroring and may offer better battery/quality.

NuXtream must label these correctly. It must not describe a WebRTC video stream as a second local display.

### 6.3 Open protocol proposal

Prefer well-supported, open standards over inventing a new codec or transport:

**Primary protocol: WebRTC**
- Use WebRTC media transport for low-latency screen/audio streams.
- Use DTLS-SRTP for authenticated encrypted media.
- Use ICE with local host candidates for LAN/WLAN/USB-IP paths.
- Do not require STUN/TURN for same-link local streaming; allow optional user-configured/self-hosted STUN/TURN for routed/NAT scenarios.
- Use an authenticated signaling channel (HTTPS/WebSocket or another documented secure transport).
- Use an open, documented JSON/CBOR session schema with explicit version negotiation and capability negotiation.
- Prefer existing maintained WebRTC libraries rather than writing an RTP congestion-control, DTLS or SRTP implementation from scratch.

**Optional interoperability: Miracast/Wi-Fi Display**
- Investigate 802.11 Wi-Fi Direct/P2P capability, wpa_supplicant/NetworkManager support, RTSP negotiation and the relevant media profile.
- Implement only when hardware/driver and a real receiver pass end-to-end tests.
- Keep this optional. NuXtream must still support LAN and USB-IP streaming if Wi-Fi Direct is unavailable.
- Don't call a WebRTC LAN session “Miracast”.

**Codec policy**
- Negotiate codecs and profiles supported by both endpoints.
- H.264 baseline/main is a sensible initial interoperability target; VP8 is another open browser-friendly baseline. Evaluate AV1 only if both ends and actual S10+ encoder performance support it.
- Do not claim Exynos MFC hardware encoding/decoding without an independent hardware proof. The previous MFC mission did not prove the video engine.
- Start with bounded 720p/30 or lower and adaptive frame pacing; raise quality based on receiver and encoder capability.
- Never assume the GPU's Mali GLES acceleration implies hardware video encoding.

### 6.4 All requested transports

NuXtream must support the same secure session model over several transports:

**A. Wi-Fi LAN**
- Same subnet local discovery via mDNS/DNS-SD or a user-visible manual IP/QR pairing fallback.
- Unicast session after pairing; no unauthenticated broadcast frames.
- Don't assume P2P support merely because Wi-Fi is present.

**B. Wired LAN/Ethernet**
- Discover/select Ethernet interfaces and local receiver addresses.
- Support USB-C dock Ethernet or another Ethernet interface only when Linux enumerates a working network interface.
- Prioritize wired link when requested/available. Do not make Wi-Fi mandatory.

**C. USB network transport**
- Investigate USB CDC-ECM/NCM/RNDIS gadget capability on the S10+ DWC3 UDC and the endpoint resources available alongside the existing CDC-ACM console.
- Determine whether a composite gadget can safely retain CDC-ACM console and expose ECM/NCM networking simultaneously. Verify actual target driver and host OS compatibility.
- If composite mode is not currently viable, provide an explicit owner-approved alternative path (for example switch the gadget profile only after a second recovery connection is verified). Do not silently remove the console.
- Support a network session over the resulting point-to-point USB IP link using the same WebRTC/signaling stack.
- USB host-mode Ethernet adapters are a separate case and have the same role/host constraints as USB audio devices.

**D. Wi-Fi Direct**
- Optional, only when P2P mode has been verified on the actual firmware/driver. Handle group owner/client negotiation, discovery, channel selection, RTSP if Miracast is implemented, disconnect and cleanup.

**Transport independence**
- The signalling/session layer should not know whether the IP route is Wi-Fi, Ethernet or USB. Use a single authenticated stream protocol with route discovery and transport scoring.
- Explicitly display which interface carries the session.
- Don't use Google services or public cloud relay by default.

### 6.5 Receiver implementation and “cast to any device” reality

Build a receiver that can be used from a standards-capable browser:

- A local NuXtream receiver page/service served by the phone for a connected receiver client, or a separately installed receiver app on the target device.
- On the receiver, a clear “Pair with NuXtream” flow, QR/token input, accept/deny prompt and end-session control.
- A receiver can be hosted by a laptop, desktop, tablet or smart TV browser where WebRTC and the required video APIs are available.
- Document limitations by browser/device; browsers on some smart TVs may be outdated or lack required WebRTC/H.264/VP8 support.
- Design native reference receiver clients later, using the same public protocol.
- Support manual receiver URL/IP and QR pairing when mDNS is blocked.

A device without a compatible browser/app/protocol cannot be forced to accept a stream. Document this honestly and provide receiver code/source so users can add compatibility without vendor licensing.

### 6.6 Screen capture, privacy and performance

- Do not use `grim` screenshots polled in a loop as the production real-time capture mechanism.
- Integrate an approved Wayland capture path supported by the actual Phoc/wlroots build (PipeWire portal if the compositor/portal supports it; wlr-screencopy or a maintained capture integration only with correct lifetime/format handling).
- The current diagnostic only checks for the presence of `grim`, `wf-recorder`, protocol XML or PipeWire. Presence is not proof of a real frame stream. Implement a capture self-test that obtains frames and records timestamps/checksums/format/size without exposing screen contents in logs.
- Use buffer pools and backpressure; don't queue unbounded frames.
- Use hardware video encoder only if it is proven and available; otherwise use CPU encoder with strict quality/FPS caps and adaptive degradation.
- Avoid blocking the compositor/main UI thread.
- Handle resize/orientation changes, output removal, screen lock, unlock, receiver disconnect and network route changes.
- On screen lock, pause/stop video capture before the lockscreen is shown. Never stream lockscreen contents, notifications or secure prompts. Resume only after explicit policy approval/unlock.
- Add a privacy indicator while capture is active and a persistent Stop action.
- Default microphone/system audio sharing OFF. Capture system audio only through a permissioned PipeWire loopback and never open the microphone without explicit consent.
- No screen capture before pairing/acceptance. No anonymous receiver.
- Rate-limit connection attempts and validate signaling payload sizes/types.

### 6.7 Extend-over-network: advanced, don't mislabel

A video mirror to another device is not a true extended desktop. True network extend requires a second logical output/virtual monitor presented to the compositor plus a receiver that renders it, and optional reverse input forwarding.

Implement mirroring first. Then investigate a virtual output backend (for example a supported headless/wlr virtual output or a purpose-built compositor output plugin) that creates a distinct display geometry, routes windows independently and streams that output to a receiver. Only then expose “Extend over network”.

Remote input forwarding must be opt-in, authenticated, focus-scoped, and revocable. Never silently forward receiver keyboard/mouse input into a locked phone or secure dialog.

---

## 7. SECURITY, TRUST AND PRIVACY REQUIREMENTS

1. No open LAN endpoint that exposes continuous screen frames without pairing/authentication.
2. Pairing tokens are cryptographically random, short-lived, single-use where practical, and revoked on session stop.
3. Use standard TLS/WebRTC DTLS-SRTP. Do not invent cryptography.
4. Store receiver identities/keys in the system keyring/credential store where available; never plaintext localStorage.
5. The display helper must expose only allowlisted output actions; no arbitrary sysfs writes from the PWA.
6. Hardware role switch is privileged, explicit, audited and owner-approved.
7. Screen capture is disabled by default and shown via a visible indicator.
8. Lock immediately suspends screen capture and audio loopback; lockscreen is never sent to receivers.
9. Stop/revoke cleans listeners, sockets, media pipelines, capture objects, file descriptors and temporary credentials.
10. No mandatory cloud registration, telemetry or account.
11. Default network visibility is local-link only. Never bind to `0.0.0.0` for an unauthenticated receiver endpoint.
12. Add threat-model coverage for hostile receivers, rogue LAN peers, mDNS spoofing, malformed SDP, oversized signalling messages, session replay, stale pairing tokens and cross-network leakage.
13. Never log actual screen frames, audio samples, microphone data, auth tokens or secret pairing keys.

---

## 8. PACKAGE, SERVICE, BUILD AND IMAGE INTEGRATION

### 8.1 Service boundaries

Implement a clean separation, adapting names to repo conventions:

- `nuxel-audio-accessoryd` or an extension to the existing audio-route daemon for hotplug state and UAC profiles;
- `nuxel-displayd` for physical display output state/capability management;
- `nuxtreamd` for cast sessions, receiver pairing, discovery and capture/stream lifecycle;
- existing Nuxel bridge/HTTP RPC for app calls.

Do not create three duplicate background polling services if the existing audio or bridge service can be extended cleanly. Prefer one authoritative service per responsibility. Document dependencies and startup ordering.

### 8.2 Installer integration

Trace and update the actual S10+ build manifests/installer. At minimum inspect:

- `images/s10plus/packages-manifest.json`
- `tools/s10plus/a33/verify-packages.py`
- `tools/beta/live/deploy-manifest.json`
- current beta image/deploy manifests and service lists;
- app registry `pwa/nuxel-common/app-registry.json` and schema/config;
- NuXtore discovery and app metadata;
- udev rules and WirePlumber configuration;
- systemd services/sockets/tmpfiles/permissions.

Ensure clean image install and runtime upgrade both install required components. Do not assume host-side build dependencies are present on the phone. Do not accidentally enable a dangerous plugin or broad USB permission rule.

### 8.3 Versioned schemas and API

Use documented JSON schemas for accessory state, external display status, cast capabilities, pairing and sessions. Validate at every boundary. Reject unknown versions or fields safely. Add migration rules where needed.

### 8.4 Cache invalidation and launcher correctness

The PWA app uses a service worker. Bump cache version and verify fresh app files load from the generated image and live HTTP path. Add app registry tests so NuXtream appears once, launches once, has correct icon/title/permissions and is detected by NuXtore.

---

## 9. PERFORMANCE AND ROBUSTNESS TARGETS

- Normal Nuxel speaker audio and phone UI must remain unaffected when NuXtream is closed.
- No idle capture pipeline, continuous polling of high-cost diagnostics, encoder process or network listener when not needed.
- Audio hotplug should settle promptly without audible clicks, full-volume spikes or dropped default route. Measure event-to-route latency.
- Display output hotplug should be debounced and state transitions observable; no infinite retry loops.
- The external display test pattern should use a supported advertised mode and bounded frame rate.
- Casting should adapt resolution/FPS/bitrate to link quality and avoid excessive CPU on the Exynos 9820.
- Keep buffers bounded. Define a maximum queue and drop stale frames rather than accumulating latency.
- Track CPU %, RSS, encoder utilization if available, resolution, FPS, dropped frames, end-to-end latency and network throughput during a 10-minute test.
- Battery/thermal policy: reduce quality before thermal throttling. Stop gracefully on critical thermal or low-memory conditions.
- Cleanly survive receiver sleep/disconnect, Wi-Fi handover, USB link flap, external monitor unplug, orientation change and app close.

---

## 10. REQUIRED TEST MATRIX

### 10.1 Audio automated tests

Extend tests beyond the current seven fixtures:

- UAC1 playback device; UAC2 playback device; UAC playback+capture; multi-interface/multi-altsetting; unsupported class; device with no ALSA driver; ALSA card appears late; PipeWire node appears late; card index changes; duplicate udev add; unplug during stream; reconnect same device; disconnect while selected; default sink disappears; internal speaker fallback; low volume retained; jack plus UAC collision; unknown USB-C device; gadget mode conflict; role transition refused without alternate recovery; role transition accepted only with owner token and validated watchdog.

Verify no real hardware opens or role switches during offline tests.

### 10.2 Type-C/DP automated tests

Add fixtures for:

- no Type-C path;
- partner attached only;
- charger attached with no video;
- DP SVID discovered but mode not entered;
- mode entered but no HPD;
- HPD asserted but no EDID;
- invalid EDID checksum;
- valid EDID but no kernel connector;
- connector connected with no modes;
- modes but no active CRTC;
- active CRTC and frame commit pending owner-visible proof;
- DisplayLink USB device rather than DP Alt Mode;
- Billboard error descriptor;
- unplug during modeset;
- mode list changes after reconnect;
- internal DSI only.

Test JSON versioning and monotonic verdict progression. No fixture may be counted as a live display proof.

### 10.3 NuXtream UI/API tests

- registry discovery and launch;
- capabilities drive enabled/disabled state;
- no output means mirror/extend controls disabled with useful explanation;
- connected but no EDID / no active mode states;
- mirror enabled then disabled;
- extend appears only with two real outputs;
- mode list limited to EDID-advertised modes;
- restore timer and cancellation;
- receiver discovery and pairing;
- pairing expiry/revocation;
- session lifecycle;
- lock pauses capture and hides secure content;
- no microphone/system audio without explicit consent;
- transport selection accurately reflects active path;
- USB transport unavailable while gadget role cannot safely expose network;
- service restart and app cache update.

### 10.4 Casting protocol tests

- WebRTC handshake and capability mismatch;
- unpaired receiver rejected;
- expired token rejected;
- token replay rejected;
- bad signature/auth rejected;
- oversized/malformed signaling rejected;
- LAN/WLAN and USB IP transport tests;
- no internet/cloud access required for local session;
- network interruption/recovery;
- receiver stop/revoke;
- lock event stops capture;
- screen orientation/resize;
- FPS adaptation and bounded buffers;
- receiver browser interoperability tests.

### 10.5 Physical owner test matrix

The following require the owner and actual hardware. Prepare a clean wizard and record exact adapter/device models:

| Test | Accessory/path | Required proof |
|---|---|---|
| A1 | Samsung USB-C earphones direct | USB descriptors, UAC ALSA card, PipeWire sink, audible L/R output, speaker silent, unplug fallback |
| A2 | Beyerdynamic 3.5 mm headphones + USB-C adapter | Identify adapter as UAC DAC/passive; if UAC, same proof as A1; if passive unsupported, accurately record it |
| A3 | Direct 3.5 mm jack if applicable | Jack detection, headphones route, audibility, speaker muted, restore on unplug |
| D1 | USB-C HDMI adapter to TV | Actual DP state, EDID, modes, active compositor output and visible Nuxel pixels |
| D2 | Mirroring | Same live desktop visible internally and on TV, no tearing, stable 10 min |
| D3 | Extension | Independent output exists, windows move, touch remains on internal screen, TV shows separate desktop |
| C1 | NuXtream receiver over Wi-Fi | Authenticated pairing and moving stream visible in browser/native receiver |
| C2 | NuXtream receiver over wired LAN | Same session on Ethernet, explicitly reports Ethernet route |
| C3 | NuXtream receiver over USB network | CDC-ECM/NCM or supported USB network path, separate from DP Alt Mode, actual stream works |
| C4 | Lock/privacy | Lock stops capture before lockscreen could be sent; unlock does not silently restart unless policy permits |

---

## 11. OWNER TEST WIZARDS AND RECOVERY

Produce three concise physical test guides:

1. `docs/pwnage-69000/OWNER-TEST-USB-AUDIO.md`
2. `docs/pwnage-69000/OWNER-TEST-USB-C-HDMI.md`
3. `docs/pwnage-69000/OWNER-TEST-NUXTREAM-CAST.md`

Each guide must state:

- prerequisites and known current connection;
- exact command to start capture;
- expected event/state transitions;
- what to observe/hear on actual hardware;
- how to stop the test;
- how to restore internal speaker route / internal panel;
- how to reconnect USB console;
- fallback if the port role change loses the USB session;
- what files to attach to the finding;
- what constitutes PASS, FAIL, UNKNOWN and NOT_SUPPORTED.

Do not start the actual USB role change from the NuXtream app until the owner has completed and explicitly approved the separate recovery preflight. Display mode changes also need an automatic restore timer and a safe cancel route.

---

## 12. REQUIRED COMMANDS AND VALIDATION GATES

Run the relevant focused tests. Add the new tests to the appropriate project test runner/CI. At minimum rerun:

```sh
bash tools/s10plus/a33/nuxel-headphone-diag.sh selftest
python3 tools/s10plus/a33/tests/test-headphone-route.py
pytest -q tools/s10plus/a33/tests/hw-subsystems/test-a49-typec-cast.py
```

Also run the existing S10+ A33 test suite and package/app registry validation that can be run in the host environment. Confirm all generated artifacts and new app files are installed by the S10+ image builder. If an existing Type-C/Cast selftest returns `0 fixtures checked`, repair it; never treat zero checks as PASS.

Add type checking/linting and schema validation for the daemon and PWA code. Use mocked sysfs/proc/dev roots for all offline hardware tests. Any command that could write a live sysfs role/altmode node, change a mixer/route, start display modesetting, power a PHY, or open a potentially hanging hardware device must be owner-gated and excluded from ordinary CI.

### Completion evidence ladder

Track each capability using distinct states:

`DISCOVERED → IDENTIFIED → DRIVER_BOUND → ENUMERATED → USERSpace_NODE_READY → ROUTED → SIGNAL_PIPELINE_RUNNING → PHYSICALLY_OBSERVED → SUSTAINED_TESTED`

For direct external display:

`TYPEC_PARTNER → DP_ALT_MODE_ENTERED → DP_LINK_CONFIGURED → HPD → EDID_VALID → KERNEL_CONNECTOR → MODE_AVAILABLE → CRTC/SCANOUT_ACTIVE → COMPOSITOR_OUTPUT → FRAME_COMMITTED → VISIBLE_TV_PIXELS → SUSTAINED_HOTPLUG_TEST`

For casting:

`CAPTURE_PERMISSION → REAL_FRAME_SOURCE → ENCODER_READY → RECEIVER_PAIRED → TRANSPORT_UP → STREAM_NEGOTIATED → FRAMES_RENDERED → AUDIO_PROVEN_IF_ENABLED → PRIVACY_TESTED → SUSTAINED_SESSION`

Do not skip states. A built helper, detected accessory, successful service activation or test fixture is not physical proof.

---

## 13. PRIORITIZED IMPLEMENTATION ORDER

Work in this order, but continue safe independent work while a hardware task is blocked:

### Phase 1 — establish evidence and fix diagnostics

- Baseline audio/device/Type-C/DRM/compositor state.
- Improve read-only diagnostic reports and JSON schemas.
- Fix zero-fixture selftest behavior.
- Fix wrong/missing package manifest integration found during the audit.
- Confirm exact output of every existing command and ensure status doesn't lie.

### Phase 2 — USB audio completion

- Correct accessory identification.
- Build UAC event detection and WirePlumber/PipeWire routing.
- Preserve the USB console safety boundary.
- Add owner-supervised role preflight and recovery design.
- Add low-volume test wizard and offline tests.
- Only owner tests prove audible success.

### Phase 3 — DP Alt Mode / HDMI root cause

- Identify exact Samsung CCIC/DP and Exynos output driver chain.
- Reconcile current “external display connected” signal with real kernel state.
- Determine why TV remains blank (no mode entry, no HPD, no EDID, no output driver, no KMS/compositor backend, no frame commit, etc.).
- Implement only source-backed, tested kernel/DT/userspace fixes.
- Keep internal AMOLED safe. No speculative pin/mux/PHY writes.

### Phase 4 — direct display output and NuXtream Displays UI

- Produce real external connector and mode enumeration.
- Integrate a genuine secondary output into the compositor.
- Implement mirror first, extend only when a real independent output exists.
- Add test pattern, fallback, disconnect handling and visible-output proof.

### Phase 5 — NuXtream open casting MVP

- Implement local authenticated WebRTC signaling/session protocol.
- Implement a working browser receiver and sender capture pipeline.
- Support WLAN and wired LAN.
- Add USB networking only when composite gadget/USB network topology can preserve recovery.
- Add transport discovery, QR pairing, session stop/revoke and security/privacy.

### Phase 6 — advanced interoperability and performance

- Investigate optional Miracast/Wi-Fi Direct.
- Add receiver SDK/reference client docs.
- Implement advanced remote virtual output/extend only after mirror is proven.
- Add adaptive quality, sustained tests and thermal/performance telemetry.

### Phase 7 — final integration and release evidence

- Build clean S10+ image.
- Verify NuXtream is launchable and its daemon active only where appropriate.
- Run all regression tests.
- Produce artifact hashes and deploy manifest.
- Deliver owner procedures. Do not flash or reboot the phone as part of this mission unless explicitly separately authorized.

---

## 14. HARD SAFETY BOUNDARIES

Unless the owner separately authorizes a specific, bounded hardware procedure, do NOT:

- flash, erase, repartition or write BOOT, DTB, recovery, modem, EFS, param or other protected partitions;
- use TWRP, Odin, Heimdall, fastboot, Download Mode or bootloader commands;
- change bootloader/OEM/FRP state or factory reset;
- reboot or power-cycle the phone;
- change Type-C data/power roles, unbind the only USB gadget console, or switch USB gadget functions;
- write arbitrary Type-C/DP altmode, mux, SBU, retimer, PHY, regulator, GPIO or DECON sysfs/debugfs/register paths;
- force unsupported display modes or write to physical memory addresses;
- start screen capture or transmit frames without pairing and user consent;
- expose screen capture, audio, microphone or receiver signaling to unauthenticated LAN peers;
- install/activate unverified kernel modules or proprietary firmware;
- modify the internal AMOLED bridge until an alternate safe path exists and regression tests pass.

You may inspect source, search vendor tree references, build kernel/userspace artifacts in the host environment, add offline tests, and create safe read-only diagnostic tools.

Never destroy owner changes using `git reset --hard`, `git clean -fdx`, broad recursive deletes or forced checkout. Never push or publish a release.

---

## 15. REQUIRED DELIVERABLES

Create or update the following (adapt exact names to repository conventions, but all equivalent information is mandatory):

1. `docs/pwnage-69000/BASELINE.md` — exact repository/image/live-state baseline.
2. `docs/pwnage-69000/FINDINGS.md` — all findings with severity, confidence, evidence, owner action, remediation and status.
3. `docs/pwnage-69000/USB-AUDIO-IMPLEMENTATION.md` — Samsung UAC and Beyerdynamic adapter paths, role conflict, routing and test results.
4. `docs/pwnage-69000/DP-ALT-MODE-ROOT-CAUSE.md` — exact reason external monitor is detected but blank, supported chain and remaining hardware blockers.
5. `docs/pwnage-69000/NUXTREAM-ARCHITECTURE.md` — architecture, services, APIs, display and cast distinctions, transport details, receiver protocol and threat model.
6. `docs/pwnage-69000/TEST-MATRIX.md` — automated, image, integration and physical owner tests, with evidence states.
7. `docs/pwnage-69000/OWNER-TEST-USB-AUDIO.md`.
8. `docs/pwnage-69000/OWNER-TEST-USB-C-HDMI.md`.
9. `docs/pwnage-69000/OWNER-TEST-NUXTREAM-CAST.md`.
10. A final machine-readable capability/status manifest with honest values.
11. Full changed-file list and `git diff --check` output.
12. Build/test logs, test totals, hashes of deployment artifacts and a clean S10+ image/package parity result.
13. A precise list of things that remain impossible without owner hardware action, a proprietary/licensed dependency, a matching kernel driver or a compatible receiver.

---

## 16. DEFINITION OF DONE

Repository-side work is done only when:

- Current source and live evidence are reconciled.
- USB audio classification and routing have robust event-driven implementation and comprehensive offline tests.
- Samsung USB-C earphones and the Beyerdynamic adapter have separate test paths and truthful transport identification.
- The one-port gadget/host role conflict has a verified safe design or remains explicitly blocked; no blind switch exists.
- HDMI diagnostics identify the true negotiation/output/scanout stage, and the root cause of the blank TV is documented with source evidence.
- Any external output implementation is backed by a real kernel/DT/compositor path; no fake connector or simulated output exists.
- NuXtream is a real registered, packaged, launchable Nuxel app with a working daemon/API and capability-driven controls.
- The app's direct display Mirror/Extend controls are distinct from network/USB screen casting.
- A working open casting MVP is implemented with a real capture pipeline, authenticated WebRTC transport, receiver and session lifecycle. Support is stated per receiver and per transport actually tested.
- WLAN and wired LAN are supported as implemented IP transports. USB streaming is supported only after real USB networking is implemented and verified without destroying the console. If a safe USB network topology is blocked, report that exact blocker and provide an explicit future plan.
- Lock/privacy behavior is tested, with no lockscreen capture.
- All offline tests and image integration tests pass, including no-zero-tests safeguards.
- The internal display and speaker paths remain intact.
- Physical-only tests remain `NEEDS_OWNER_TEST` until the owner observes actual audible output or visible moving pixels.

---

## 17. FINAL INSTRUCTIONS TO THE AGENT

Start now. Capture baseline. Read and trace all referenced source files. Build a source-of-truth map. Run current tests. Create a prioritized findings register. Implement all safe, confirmed fixes. Add tests before closing issues. Build the S10+ artifacts and verify package integration. Repeat the audit against your own diff. Produce the deliverables.

Do not ask the owner to re-explain details already included here. Do not stop because the mission is large. Split work into bounded phases and keep a persistent progress ledger. Continue all safe repository tasks while marking genuinely hardware-gated steps for owner testing.

**Never claim success without the correct proof:** UAC audio must be heard through the attached headphones; external display must show actual Nuxel pixels on the TV; casting must show moving frames on a compatible receiver over the stated transport. A status label is not proof.
