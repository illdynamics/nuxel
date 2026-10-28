# PWNAGE-31000 — NUXEL PRELOAD CINEMA
## Full implementation and verification specification

PROJECT
Repository: /x/nuxel
Operating system: Nuxel, custom Fedora-based Linux phone OS
Target: Existing Nuxel userspace and live USB deployment workflow
Milestone: PWNAGE-31000
Video asset: ./assets/nuxel-preloading-screen.mp4

OBJECTIVE
Introduce a cinematic pre-lockscreen video that runs while Nuxel completes
the relevant startup work. Make the transition into the actual lockscreen
intentional, smooth and reliable.

The feature must improve perceived startup quality without compromising
startup dependencies, memory, security, input handling or recovery.

The video is a presentation layer over real startup activity. It is not a
replacement for service management, a fabricated progress indicator or a
reason to postpone starting services.

======================================================================
1. BASELINE INSPECTION — DO THIS BEFORE EDITING
======================================================================

Inspect the actual checkout, Git state and current boot architecture.

Identify:
- the current branch, HEAD and uncommitted changes;
- existing boot-screen and boot-warning behavior;
- the current lockscreen implementation and unlock lifecycle;
- how the launcher and desktop become visible;
- the current display/compositor and graphics initialization sequence;
- the service manager and existing startup dependencies;
- which services already start automatically;
- which services are lazy-started by applications;
- the existing media decoder/player libraries and supported codecs;
- the current asset-loading and live-userspace packaging mechanisms;
- existing startup logs, tests and recovery procedures.

Inspect the actual asset:

    ./assets/nuxel-preloading-screen.mp4

Determine:
- whether the file exists and is readable;
- its actual duration, rather than assuming six seconds;
- dimensions and aspect ratio;
- frame rate and codec;
- pixel format and color characteristics;
- whether it contains an audio track;
- file size and expected memory/decode cost;
- whether the current target's installed media stack can decode it.

Use existing inspection tools such as ffprobe where available. Do not install
large new dependencies merely to inspect the file if equivalent tools already
exist.

Do not re-encode, replace or modify the supplied asset unless necessary.
If conversion is required, preserve the original, document the reason and
verify the converted output.

Record the initial boot behavior and relevant test results before changing
the boot flow.

======================================================================
2. REQUIRED BOOT EXPERIENCE
======================================================================

Implement this conceptual sequence:

    Kernel and existing boot handoff
                |
                v
    Existing Nuxel boot / warning screens
                |
                v
    Display and playback path ready
                |
                v
    PRE-LOCKSCREEN CINEMATIC VIDEO
      + startup services initialize concurrently
      + lockscreen assets and input become ready
                |
                v
    Real Nuxel lockscreen
                |
                v
    Existing authenticated/unlock flow
                |
                v
    Existing desktop and applications

Adapt this sequence to the actual code and service dependencies. Do not
introduce a second competing boot manager or lockscreen.

The preloading video must not:
- run before the display stack can safely render it;
- hide an existing mandatory security/warning screen;
- run after the user has reached the unlocked desktop;
- replace the real lockscreen with a static video frame;
- bypass authentication or unlock logic;
- interfere with the existing Back/Home/Recents behavior after unlock;
- remove the existing live console or recovery escape path.

Use a dedicated, clearly scoped boot-animation controller or equivalent
existing architectural component. Avoid duplicating the animation logic in
the launcher, lockscreen and multiple system services.

======================================================================
3. STARTUP CONCURRENCY AND READINESS GATES
======================================================================

CRITICAL REQUIREMENT:
The video must not become a prerequisite for starting services that can
already start independently.

Start the video and eligible startup tasks concurrently as soon as their
actual dependencies permit.

First classify services into two categories.

A. LOCKSCREEN-CRITICAL READINESS

Only include services genuinely required for the lockscreen to appear and
function safely. Determine the list from the actual implementation.

Potential examples to investigate:
- display/compositor readiness;
- the lockscreen renderer and its assets;
- working touch/input dispatch;
- access to required user/session settings;
- any essential lock/unlock state service.

Do not assume every example is required. Verify the actual dependencies.

B. NONCRITICAL BACKGROUND INITIALIZATION

Allow services not needed to display or interact with the lockscreen to
continue initializing in the background.

Examples may include:
- optional network connections;
- Bluetooth;
- GNSS/location;
- audio enhancements;
- optional application services;
- other background functionality that is not required to safely show the
  lockscreen.

Use the real service graph rather than this illustrative list.

IMPORTANT:
Do not wait for every system service or application to finish starting.
An unavailable Bluetooth controller, missing GNSS firmware, disconnected
network or unrelated app error must not indefinitely prevent the lockscreen
from appearing.

Do not eagerly launch every application just to claim it has loaded.
Consider the device's available memory and startup resource constraints.
Start services through their existing service manager and dependencies;
never launch duplicate instances to create an appearance of progress.

Do not report that all services are ready unless the actual readiness
checks establish that condition.

======================================================================
4. VIDEO TIMING AND TRANSITION POLICY
======================================================================

Inspect the real video duration and use that as the basis for timing.

Implement the following behavior:

1. Begin playback when the video playback path and display are ready.
2. Allow eligible startup services to initialize at the same time.
3. If the video finishes before the lockscreen-critical services are ready,
   remain on a safe final frame or existing loading presentation.
4. If a critical service takes longer than expected, continue waiting safely
   without exposing an incomplete desktop.
5. If the critical services become ready before the video ends, complete the
   clip as the intended boot-animation sequence, provided the animation is
   within a reasonable, bounded duration.
6. Transition immediately after the animation is complete and the critical
   readiness conditions are satisfied.
7. Do not add an arbitrary second delay after both conditions are satisfied.
8. Do not loop indefinitely without a clear reason.
9. If a critical service never becomes ready, report useful diagnostic
   evidence through the existing logging/recovery path rather than freezing
   the device permanently.

The purpose is to make the animation useful during actual startup, not to
introduce an unbounded boot delay.

Keep timing based on the real media timeline and service readiness. Avoid
brittle fixed sleeps and guessed startup durations.

If the current architecture has no trustworthy readiness signals, implement
the smallest maintainable readiness interface needed. Do not equate process
existence with service readiness.

======================================================================
5. VIDEO PLAYBACK IMPLEMENTATION
======================================================================

Inspect the existing graphics and media architecture and reuse it where
possible.

Choose a playback mechanism that works with the actual target environment.
Do not assume mpv, GStreamer, FFmpeg, WebKit, X11, Wayland or wlroots is
installed or appropriate without verifying.

Requirements:
- fullscreen presentation;
- no normal player controls or accidental playback UI;
- correct aspect ratio and sensible scaling;
- no stretched or distorted imagery;
- no desktop or application-window flash during transition;
- minimal memory overhead;
- no unnecessary application launch or heavy desktop session;
- no blocking of the main UI/input thread;
- graceful handling of decoder initialization failure;
- graceful handling of a missing, corrupt or unsupported MP4;
- clean playback shutdown and resource release;
- no stale playback process remaining after the lockscreen appears.

If hardware decoding is supported and practical, use it where appropriate.
If only software decoding is available, measure performance on the actual
target and choose a safe configuration.

Do not add a heavyweight dependency if an existing lightweight decoder can
perform the task.

If the device cannot decode the supplied file reliably, document the exact
codec/format limitation and implement a tested fallback. Preserve the
original asset.

A playback failure must never prevent the real lockscreen from appearing.

======================================================================
6. VIDEO AUDIO POLICY
======================================================================

Inspect whether the MP4 contains an audio track and determine the existing
Nuxel boot-audio behavior.

Do not unexpectedly blast audio during boot or override the system's mute
state.

If the video contains audio:
- establish whether it is intentional boot audio;
- honor system mute and volume policy;
- use a conservative, safe default;
- ensure a missing or failed audio device does not block video playback;
- prevent duplicated audio when playback restarts or the screen changes;
- stop playback audio cleanly before entering the lockscreen.

If the video is silent, do not invent an audio requirement.

If an optional boot-animation sound setting is appropriate for the existing
Settings architecture, implement it using persistent settings. Do not add
an unnecessary settings page if the project's existing design does not
justify one.

Audio failure must never block startup.

======================================================================
7. LOCKSCREEN HANDOFF AND SECURITY
======================================================================

The final frame of the video is not the lockscreen.

At handoff:
- stop and release the video decoder/player;
- ensure no player surface covers the lockscreen;
- display the actual existing lockscreen component;
- preserve the existing lockscreen background and draggable lockhead assets;
- preserve the current unlock gesture and input routing;
- keep the phone locked until the normal unlock operation succeeds;
- ensure touch input is delivered to the correct surface;
- ensure no startup transition bypasses lockscreen authentication/state;
- avoid a black frame, desktop flash or abandoned video window;
- restore normal navigation only according to the existing lockscreen rules.

Do not remove or rewrite the lockscreen merely to simplify the video
transition.

Ensure that boot completion and lockscreen readiness cannot accidentally
cause the desktop to appear before the user unlocks the device.

Test repeated transitions, interrupted playback and lockscreen re-entry.

======================================================================
8. FAILURE RECOVERY AND FALLBACK
======================================================================

The existing boot process must remain recoverable if the video feature fails.

Handle at least these cases:

A. Asset missing
- Log a useful diagnostic.
- Skip video playback.
- Continue through the existing safe boot/loading flow.

B. Asset unreadable or corrupt
- Report the actual failure.
- Do not retry indefinitely.
- Continue to the real lockscreen when its readiness conditions are met.

C. Codec unsupported
- Use a verified fallback if available.
- Otherwise skip the animation without blocking startup.

D. Decoder or renderer crash
- Release resources where possible.
- Prevent restart loops.
- Continue the safe boot flow.

E. Startup service failure
- Distinguish critical from noncritical service failure.
- Do not block the lockscreen because of an unrelated optional service.
- Use the existing diagnostics/recovery behavior for a genuinely critical
  dependency that fails.

F. Slow service startup
- Remain in a safe loading presentation.
- Avoid an indefinite frozen animation.
- Expose diagnostic evidence through the existing log or console path.

G. Display/compositor failure
- Do not create an independent graphics path that fights the compositor.
- Preserve the existing console/recovery mechanism.

H. Reboot or shutdown during playback
- Release resources cleanly.
- Do not leave stale processes or persistent state that prevents the next
  boot from reaching the lockscreen.

The fallback must be simpler and more reliable than the feature it protects.

======================================================================
9. OPTIONAL STARTUP STATUS — TRUTHFUL ONLY
======================================================================

Inspect whether the existing boot UX benefits from a subtle status indicator
when startup takes longer than the video.

If useful, show a minimal, theme-consistent message such as "Preparing Nuxel"
only while relevant initialization is genuinely in progress.

Rules:
- Do not invent a percentage.
- Do not display "All services loaded" based on elapsed time.
- Do not imply network, Bluetooth, GPS or audio is ready unless verified.
- Do not cover important video content with excessive UI.
- Do not expose sensitive service information to ordinary users.
- Keep detailed diagnostics in the appropriate development log/console.

If there is no trustworthy aggregate progress source, use an honest
indeterminate status or simply hold the safe final frame.

Do not build a complex progress dashboard just for this feature.

======================================================================
10. ASSET PACKAGING AND LIVE DEPLOYMENT
======================================================================

Integrate:

    ./assets/nuxel-preloading-screen.mp4

into the actual asset loading and live-userspace packaging workflow.

Inspect the current packaging scripts and manifest. Do not invent a second
asset installation mechanism.

Verify:
- the source asset exists;
- the runtime destination is correct;
- file permissions allow playback;
- the file is included in the deployment payload;
- the package checksum/hash covers the actual file;
- the runtime path matches the configured playback path;
- missing-file fallback works;
- the existing boot image/warning assets remain available;
- rollback restores the previous boot flow.

Update the appropriate tests, manifests, hashes and CI coverage.

Use the repository's actual package and verification tools. Do not claim
the video is packaged merely because it exists in the development tree.

Do not delete or replace existing boot assets.

======================================================================
11. PERFORMANCE AND BOOT RELIABILITY
======================================================================

Measure the effect on actual startup.

Where practical, record:
- time to display the existing boot UI;
- time to start video playback;
- time until lockscreen-critical readiness;
- time until the video completes;
- time until the real lockscreen appears;
- time until touch interaction works;
- CPU and memory impact during playback;
- decoder initialization failures;
- services that continue in the background.

Compare baseline and updated behavior.

The animation may intentionally occupy a short bounded presentation interval,
but it must not make service initialization slower through unnecessary CPU,
memory or I/O contention.

Do not eagerly preload every app or consume excessive memory merely to hide
startup latency.

Optimize only after measuring actual behavior. Avoid arbitrary delays that
make the boot experience slower without providing a useful presentation
benefit.

If the video materially harms startup or makes the target unstable, reduce
playback cost, use a verified compatible format, or fall back safely.

======================================================================
12. AUTOMATED AND PHYSICAL VERIFICATION
======================================================================

Add tests for:

- successful video start and completion;
- lockscreen readiness arriving before video completion;
- video completion before readiness;
- slow critical startup;
- noncritical service failure;
- missing asset;
- corrupt or unsupported video;
- decoder initialization failure;
- playback cleanup;
- no desktop flash during handoff;
- lockscreen remains locked until normal unlock;
- no duplicate playback process;
- fallback behavior;
- asset packaging and hash verification;
- preservation of the existing boot/warning screen behavior.

Use mocks for deterministic automated tests. Do not treat mocks as physical
hardware proof.

If the live device is available and safely identifiable:
- verify the boot sequence on the actual S10+;
- verify playback quality and frame stability;
- verify that the lockscreen appears and responds to touch;
- verify that unlock still works normally;
- verify that missing/failed playback cannot strand the device;
- verify the live console/recovery path remains available.

If the live device is unavailable, finish offline tests and packaging, then
mark physical verification as BLOCKED/PENDING. Do not fabricate results.

======================================================================
13. REPOSITORY AND RECOVERY SAFETY
======================================================================

Before changing files, record the current Git state and preserve uncommitted
work. Never use destructive reset/clean operations to simplify the change.

No:
- kernel replacement;
- firmware flashing;
- bootloader modifications;
- partition writes;
- recovery-partition changes;
- destructive root-level deployment;
- unverified target selection.

Back up modified boot configuration and related persistent files. Verify
the backup and provide exact rollback steps.

Use the existing approved live-userspace deployment mechanism only, after
verifying the target and recovery path.

Do not create a release tag, publish a release, or merge a PR unless
explicitly requested.

======================================================================
14. COMPLETION REPORT
======================================================================

At completion, report:

1. Root cause or existing boot architecture discovered.
2. Playback implementation and why it fits the target.
3. Exact files changed.
4. Actual media duration/codec/audio findings.
5. Startup readiness conditions implemented.
6. Whether services initialize concurrently with playback.
7. Measured boot timing before and after where available.
8. Actual tests run and pass/fail counts.
9. Asset packaging and hash-verification results.
10. Whether the live-userspace package was deployed and to which verified
    target.
11. Physical-device results, if actually tested.
12. Remaining limitations.
13. Backup and rollback commands.

Use PASS, PARTIAL, BLOCKED or FAIL for each relevant verification category.

Do not claim that all services are loaded when only lockscreen-critical
services are ready. Do not claim a successful physical boot test unless it
actually happened.

======================================================================
15. EXECUTION ORDER
======================================================================

PHASE A — Inspect repository, current boot flow, video metadata and baseline.

PHASE B — Design the minimal playback controller and real readiness gates.

PHASE C — Integrate the video without delaying existing service startup.

PHASE D — Implement handoff, error handling and safe fallback.

PHASE E — Update asset packaging, hashes, manifests and tests.

PHASE F — Run tests, measure startup and verify recovery behavior.

PHASE G — Perform safe live-userspace deployment and physical verification
only if the target is available and recovery is preserved.

Do not stop after analysis or a written plan. Implement the feature, test it,
package it, and provide the evidence-based completion report.

BEGIN PWNAGE-31000.
