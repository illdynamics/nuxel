# PWNAGE-30000 — NUXEL APPLICATION APOCALYPSE
## Full implementation, integration, regression-repair and verification specification

PROJECT
Repository: /x/nuxel
Platform: Nuxel, custom Fedora-based Linux phone OS
Current baseline: v0.7.0-beta
Latest reported merge: PR #13, commit 3d7be7abb759dc62281a3783b1982a5f2d6fd24e
Current milestone: PWNAGE-30000, following the PWNAGE-25000–29000 work

TARGET
The current development/test phone is a Samsung Galaxy S10+ SM-G975F
(beyond2lte, Exynos 9820), running Nuxel's existing Linux userspace.
The project also has a live USB/recovery workflow.

These details are the starting point, not a substitute for inspecting the
actual checkout, connected device, running services, kernel and configuration.

======================================================================
0. MISSION AND DEFINITION OF DONE
======================================================================

Turn the existing Nuxel app collection into a coherent, reliable,
persistent and genuinely usable mobile-Linux environment.

This milestone includes:
- repairing broken existing applications;
- implementing real application functionality;
- restoring working haptic feedback;
- implementing persistent desktop widgets;
- introducing a unified Nuxel visual theme;
- making Notes, Gallery, Recorder, Weather, Mail, Contacts, Files,
  Calendar and Clock usable;
- improving truthful error reporting and hardware diagnostics;
- updating tests, deployment packaging, hashes and verification evidence.

Do not merely redesign screenshots or make controls appear clickable.
Do not substitute hardcoded demo results for real operations.
Do not claim functionality because a button responds or a service starts.

A feature is complete only when its real operation works, its state is
persisted appropriately, errors are handled, and tests cover its behavior.

If a hardware capability cannot be completed in this milestone, implement
the correct diagnostics and truthful user-facing status. Clearly separate
software completion from physical hardware verification.

Do not stop after analysis or a plan. Inspect, implement, test, integrate,
package and verify as much of the full scope as the actual environment allows.

======================================================================
1. SAFETY, REPOSITORY DISCIPLINE AND WORKFLOW
======================================================================

Before editing:

1. Enter /x/nuxel and inspect:
   - git status and current branch;
   - recent commits and current HEAD;
   - existing uncommitted changes;
   - the merged PWNAGE-25000–29000 implementation;
   - application entry points and routing;
   - UI framework, compositor, desktop shell and shared components;
   - storage/database and settings architecture;
   - keyboard, haptics, audio, microphone and permissions services;
   - existing widget, desktop and multi-desktop support;
   - current test suites, packaging scripts, live-deploy manifests and CI.

2. Run relevant baseline tests before editing. Save the actual output.

3. Preserve existing user changes. Never use git reset --hard, destructive
   clean operations, blanket overwrites or force pushes to simplify work.

4. Follow the repository's existing branching and contribution conventions.
   Use a dedicated work branch if appropriate and safe. Do not create a
   release tag, publish a release or merge a PR unless requested.

5. Read existing code before introducing new abstractions. Reuse the
   architecture wherever reasonable. Do not assume React, GTK, Qt, X11,
   Wayland, wlroots, WebKit or any particular library until verified.

HARDWARE AND RECOVERY SAFETY:

- Do not flash firmware or a kernel.
- Do not replace the running kernel.
- Do not change bootloader configuration.
- Do not write to partitions or alter partition tables.
- Do not modify recovery partitions.
- Do not destroy or disconnect the working serial/live-console recovery path.
- Do not restart critical services blindly on the live device.
- Do not perform ambiguous root-level writes.
- Do not deploy to a target until its identity is verified.
- Use the existing approved userspace deployment mechanism only.
- Back up every persistent configuration or data file before modifying it.
- Verify backup integrity and provide rollback commands.
- If the target is ambiguous, deployment is unsafe or recovery is uncertain,
  stop before making the risky change and report exactly why.

Use simulated or mock hardware backends for automated tests, but never
present a simulated test as proof that the physical microphone, speaker,
vibration motor, Bluetooth controller or other hardware works.

======================================================================
2. COMMON ENGINEERING REQUIREMENTS
======================================================================

A. Real application behavior

Every interactive control must do one of the following:
- perform the advertised action;
- be clearly disabled with an understandable reason; or
- display an honest "not implemented yet" state.

No decorative Save buttons that discard data.
No silent failures.
No fake connection indicators.
No mock contacts, weather, emails, files or recordings presented as live data.
No hidden exceptions that leave users believing an operation succeeded.

B. Persistent state

Use the project's established persistence layer where possible.
Choose storage appropriate to the data and architecture.

Requirements:
- settings survive app and device restarts;
- saved content survives app restarts;
- migrations preserve existing user data;
- writes are atomic where appropriate;
- corrupted data produces recoverable errors;
- user data is not overwritten by test fixtures;
- background jobs and notifications handle process restarts;
- no test cleanup silently deletes real user data.

C. Permissions and privacy

Implement or reuse proper permission checks for:
- microphone recording;
- current location;
- file access;
- network access;
- notification/alarm behavior, where applicable.

Ask only when needed. Explain why access is needed. Allow users to disable
optional location lookup and other optional background activity.

Never log passwords, OAuth refresh tokens, access tokens, email bodies,
private keys or other secrets. Do not disable TLS certificate validation.

D. UX consistency

All apps must:
- use the shared Nuxel design tokens and theme system;
- have a consistent title bar, navigation, buttons, forms and dialogs;
- handle loading, empty, success and failure states;
- support the phone's actual viewport and touch interactions;
- avoid overlapping modal windows and invisible layers;
- maintain keyboard focus and usable text entry;
- avoid blocking the main UI during I/O;
- support scrolling without accidental action triggers;
- retain content and selections when navigating where appropriate.

E. Diagnostics

Errors should identify the failed operation, useful cause and next action.
Capture useful technical details in development diagnostics without exposing
private user data. Do not show raw stack traces to ordinary users.

======================================================================
3. SHARED HAPTICS AND KEYBOARD FEEDBACK
======================================================================

Priority: HIGH. Restore this before implementing app-specific haptic behavior.

CURRENT PROBLEM
System vibration/haptic feedback worked previously but has regressed.
Keyboard keypress haptics are also required.

TASKS

1. Inspect Git history and recent changes to identify the regression.
2. Inspect the actual vibration device, kernel interface, permissions,
   service, event path and configuration.
3. Determine whether haptic requests are being dropped, disabled, sent to
   the wrong endpoint, blocked, or incorrectly rate-limited.
4. Restore the existing working implementation if possible rather than
   creating a competing haptics system.
5. Centralize haptic requests through the established system abstraction.
6. Add a setting to enable/disable haptics and, if supported, adjust strength
   or duration using values valid for the real device.
7. Preserve sensible defaults and persist the user's choices.
8. Ensure feedback is asynchronous and never blocks typing or UI interaction.
9. Avoid overlapping or excessively repeated vibration requests.
10. Do not write guessed hardware registers or invent a vibrator endpoint.

KEYBOARD
- Add configurable keypress haptics.
- Use the shared haptics service.
- Trigger only for genuine keypresses, not every redraw or text refresh.
- Avoid repeating vibration for a single key event.
- Keep typing responsive if the motor/service is unavailable.
- Do not introduce a second keyboard implementation just to add haptics.
- Ensure the setting takes effect immediately.

TESTS
- unit tests for enable/disable, dispatch, rate limiting and unavailable
  hardware;
- integration tests verifying key events reach the shared service;
- real-device test confirming physical vibration.

Report separately whether the software path passes and the motor was
physically verified.

======================================================================
4. CALENDAR APP
======================================================================

CURRENT PROBLEMS
- Creating an event does not work.
- Pressing Save appears to do nothing.
- Entering event time invokes an obsolete keyboard.
- Text fields use the correct current keyboard.

REQUIREMENTS

1. Trace the complete event-creation path from the UI through validation,
   persistence and calendar refresh.
2. Fix the actual Save failure. Inspect exceptions, validation state,
   event model requirements, asynchronous writes and database errors.
3. Make Save perform a real persistent write.
4. Provide visible validation for missing/invalid required fields.
5. Disable duplicate submission while a write is in progress.
6. On success, close or reset the editor appropriately and show the saved
   event in the calendar without requiring an app restart.
7. On failure, keep the entered information and show a useful error.
8. Persist events across app restart and reboot.
9. Implement or repair title, date, start time, end time, all-day status,
   location, description and reminder fields where supported by the current
   architecture. Preserve existing functionality rather than removing fields.
10. Validate end time and date relationships, including all-day events.
11. Use the system's local time zone correctly and avoid accidental UTC/local
    conversion errors.
12. Ensure editing and deleting existing events also work if already exposed.

KEYBOARD FIX
- Identify the obsolete time-entry keyboard and the route/component that
  invokes it.
- Remove its obsolete integration, not merely hide it with CSS.
- Time and date entry must use a proper picker or the same supported current
  keyboard used by the rest of Nuxel, as appropriate for the field.
- Text fields must continue using the current keyboard.
- No second legacy keyboard may appear from calendar time fields.
- Check all calendar forms for the same obsolete integration.
- Do not break numeric entry, focus, dismissal or keyboard visibility.

TESTS
- create/save/reopen event;
- invalid event validation;
- persistence after application restart;
- save failure with retained form data;
- time/date field interaction without the legacy keyboard;
- editing and deletion;
- duplicate-save prevention.

======================================================================
5. CLOCK APP — TIMER, STOPWATCH AND ALARM
======================================================================

CURRENT PROBLEM
Timer, Stopwatch and Alarm tabs are unclickable or do not switch to working
screens.

Make all tabs reliably interactive and implement their real functionality.

TIMER
- Set duration using a touch-friendly input.
- Start, pause, resume, reset and cancel.
- Show remaining time and a clear running state.
- Notify at zero using configured sound/haptics where available.
- Handle app backgrounding and UI recreation correctly.
- Avoid relying solely on a UI interval that stops when the app is suspended.
- Persist enough state to reconstruct a running timer after app restart.

STOPWATCH
- Start, pause, resume and reset.
- Implement laps if the existing design supports or can reasonably expose them.
- Use monotonic timing rather than incrementing a counter once per UI tick.
- Preserve correct elapsed time after UI redraws or app suspension.
- Prevent multiple simultaneous timer loops.

ALARM
- Create, edit, enable/disable and delete alarms.
- Set time, label, repeat days and sound.
- Provide snooze and dismiss actions.
- Persist alarms across application restarts.
- Handle device time changes, time-zone changes and daylight-saving transitions.
- Re-register scheduled alarms after reboot if the OS supports persistent
  alarm scheduling.
- Use the strongest reliable scheduler supported by the existing OS.
- Do not claim reliable reboot-surviving alarms if no persistent scheduler
  exists; identify and implement the missing service if safe.
- Avoid duplicate firing after a service restart.
- Define behavior when an alarm time has already passed.
- Provide a clear visible ringing state and accessible dismissal.

ALARM VIBRATION
- Add an explicit configurable vibration setting per alarm or a sensible
  global default with per-alarm override if the architecture permits.
- Include vibration-only, sound-only and combined behavior where supported.
- Honor global haptics disablement and explain any conflict in settings.
- Ensure vibration stops on dismissal and does not continue indefinitely.
- Handle a missing or failed vibrator without crashing the clock app.

TESTS
- tab switching and touch interaction;
- timer lifecycle and expiry;
- stopwatch accuracy and laps;
- alarm create/edit/delete/enable/disable;
- repeat schedules and duplicate prevention;
- persistence across process restart;
- scheduler recovery;
- vibration enabled/disabled behavior;
- real-device short test alarm, including physical sound/vibration where
  the hardware supports it.

Do not report an alarm as reliable based only on a rendered countdown.

======================================================================
6. CONTACTS APP
======================================================================

CURRENT PROBLEM
The app reports "Could not open contacts."

Investigate the actual failure before replacing the app or data store.

REQUIREMENTS
- Fix app launch and initial data loading.
- Handle an empty contacts database as a valid empty state.
- Display existing contacts without data loss.
- Implement create, view, edit, delete with confirmation, search and sorting.
- Persist changes across restarts.
- Validate names and optional contact details.
- Provide phone numbers, email addresses and other fields supported by the
  existing contact model.
- Avoid duplicating contacts on repeated saves.
- Support vCard import/export if the current architecture makes it practical.
- Report backend/database failures honestly and preserve user input.
- Use realistic test fixtures only in isolated test data.

Do not create fake contacts to conceal an unavailable backend.

TESTS
- fresh empty database;
- existing data migration;
- CRUD and search;
- persistence;
- malformed or unavailable storage;
- launch without a generic "could not open contacts" failure.

======================================================================
7. FILES APP — FULL FILE MANAGER
======================================================================

CURRENT PROBLEMS
- A giant upload field dominates the screen.
- A create-folder dialog/window appears behind it.
- The actual directory listing is not visible or usable.

FIRST: FIX THE UI LIFECYCLE
- Inspect modal stacking, overlay state, z-index/layering, mount/unmount
  behavior, route state and event propagation.
- Remove the unintended overlapping dialogs.
- Make the file browser the primary interface, not a giant upload control.
- Ensure all overlays close predictably and no invisible layer intercepts
  touch input.

FILE EXPLORER
Implement a usable directory browser with:
- current path and navigation breadcrumbs;
- parent/back navigation;
- folders and files, appropriate icons and metadata;
- sorting by name, type, size and modified time where supported;
- refresh and useful empty/error/loading states;
- opening supported files through their correct handlers;
- a clear upload action only where uploads make sense;
- an optional hidden-files toggle if compatible with the current design.

FILE OPERATIONS
Implement:
- create folder;
- rename file/folder;
- delete with explicit confirmation;
- multi-select;
- select all;
- select none;
- copy;
- cut/move;
- paste;
- cancel or recover from failed operations;
- progress/status for long-running operations;
- sensible collision handling if the destination name already exists.

CLIPBOARD
- Maintain a clear clipboard state for selected files.
- Distinguish copy from move/cut.
- Clear move state only after a successful move.
- Never silently claim a copy or move succeeded when it failed.
- Prevent copying a directory into itself or one of its descendants.
- Preserve file contents and report partial failures.

ARCHIVE SUPPORT
Implement real archive operations using available trusted system libraries
or existing tools, discovered from the actual environment:
- extract all;
- extract here;
- extract to a selected folder;
- compress selected files/folders into ZIP;
- provide a filename and destination;
- show progress/errors where appropriate;
- handle unsupported or corrupt archives clearly.

SECURITY
- Canonicalize paths and prevent traversal outside the permitted root.
- Protect against archive path traversal and symlink escape.
- Avoid unsafe extraction paths and overwriting without confirmation.
- Handle permission errors and read-only filesystems.
- Do not run extracted content.
- Do not execute filenames as shell commands.
- Avoid shell interpolation; use safe APIs or argument arrays.
- Do not delete user files during testing.

TESTS
- directory listing and navigation;
- modal/overlay lifecycle;
- CRUD;
- multi-select and clipboard;
- collision and permission failures;
- archives and corrupt archives;
- path traversal and symlink cases;
- large directory responsiveness;
- persistence and recovery after failed operations.

======================================================================
8. MAIL APP — REAL NUXEL EMAIL CLIENT
======================================================================

CURRENT PROBLEM
Mail is not yet usable.

Build a genuine account-based email client using the repository's existing
UI and service architecture. Do not create a static inbox mockup and call it
an email client.

ACCOUNT MANAGEMENT
- Add, edit, reconnect, disable and remove accounts.
- Support multiple accounts and account switching.
- Store per-account display name, email address, incoming server settings
  and outgoing server settings.
- Allow manual host, port, TLS/security and authentication configuration.
- Support IMAP and POP3 for incoming mail where appropriate.
- Support SMTP for outgoing mail.
- Clearly distinguish IMAP synchronization from POP3 download behavior.
- Support secure connections and validate server certificates.
- Provide a connection-test workflow that reports the failing stage.

AUTODISCOVERY
Implement discovery for common Gmail and Microsoft 365/Office 365 accounts,
including the supported Exchange/Autodiscover paths available to the
chosen client architecture.

- Prefer official provider discovery and authentication mechanisms.
- Support OAuth2 for modern Gmail and Microsoft accounts wherever the
  required provider endpoints and client registration permit it.
- Allow manual IMAP/POP3/SMTP configuration as a fallback.
- Do not assume a consumer email address is always a valid server hostname.
- Do not assume every Exchange server exposes identical protocols.
- Clearly report unsupported authentication/protocol configurations.
- Never bypass modern authentication requirements by asking users to
  disable security controls.

EMAIL OPERATIONS
Implement:
- inbox and supported folders;
- fetching and refreshing messages;
- unread/read state;
- message list and message detail;
- compose;
- reply and reply-all;
- forward;
- recipient validation;
- subject and body;
- attachments, with safe size and type handling;
- send progress and delivery/submission errors;
- drafts with persistence;
- deletion/archive behavior appropriate to the protocol;
- search where supported;
- account synchronization status;
- clear offline, authentication-expired and server-error states.

Use MIME parsing and standards-compliant message construction through a
maintained library appropriate to the existing stack. Avoid hand-rolling
complex MIME, TLS or OAuth implementations if suitable libraries exist.

SECURITY AND CREDENTIALS
- Never store passwords or tokens in source files or ordinary logs.
- Use the OS keyring/secret service if available.
- If unavailable, inspect the platform's established secure credential
  mechanism and implement an appropriate protected storage path.
- Do not invent a cryptographic scheme or claim encryption without evidence.
- Support token refresh and revocation/error recovery where applicable.
- Validate certificates; no insecure TLS fallback.
- Treat message bodies and attachments as untrusted content.
- Do not execute attachments or automatically load unsafe active content.
- Do not leak email content to diagnostics.

TESTING
Use mock IMAP/POP3/SMTP servers or controlled fixtures for automated tests.
Test discovery, authentication failures, account switching, sync, compose,
attachments, send failures, persistence and credential redaction.

Then, only with explicit owner-supplied credentials and permission, verify a
real account. Never ask the user to paste passwords or OAuth tokens into logs
or commit them to the repository.

A test server passing does not prove Gmail or Microsoft account setup works.
Report provider-specific physical/live tests separately.

======================================================================
9. MESSAGES AND PHONE — HONEST FUTURE-INTEGRATION SHELLS
======================================================================

CURRENT PROBLEM
Messages and Phone report generic "could not open" errors.

The mobile network and telephony implementation is explicitly deferred to
a later milestone. Do not fake calls, SMS, SIM status or network service.

Implement the appropriate app shell so:
- the app opens without a generic crash/error;
- the visual style matches the rest of Nuxel;
- users see a clear explanation that the telephony backend is not yet
  implemented or available;
- status is driven by actual backend detection, not a hardcoded success;
- unavailable actions are disabled or clearly marked;
- the architecture has a documented integration point for the later
  modem, SIM, voice-call and SMS implementation;
- launch failures still surface genuine errors instead of being hidden.

Do not attempt to implement the mobile network stack as part of this task.
Do not claim the apps can call or send SMS until real services exist and
have been verified.

======================================================================
10. NOTES APP — PERSISTENT NUXEL NOTES
======================================================================

CURRENT PROBLEM
Notes cannot save notes.

Implement a real Notes application with:
- create, open, edit, save and delete;
- title and body;
- autosave with appropriate debounce;
- an explicit Save action that actually persists;
- dirty/saved/error state;
- recovery of unsaved content where feasible;
- note list, selection and search;
- sorting by modified time;
- readable editor layout and keyboard handling;
- persistence across app and device restarts;
- useful empty states;
- data migration that preserves existing notes.

Do not show "Saved" until the storage operation succeeds.
If saving fails, retain the content and explain the error.

Use the existing data layer if appropriate. Otherwise choose a small,
maintainable local persistence implementation and document it.

Add tests for creation, edits, autosave, explicit save, restart persistence,
deletion, corruption and storage failures.

======================================================================
11. DESKTOP WIDGET FRAMEWORK AND NOTES WIDGET
======================================================================

Implement a genuine widget framework integrated into the existing Nuxel
desktop, Home Settings and multi-desktop system.

Do not create a fake widget overlay disconnected from desktop state.

WIDGET FRAMEWORK
- Add an enable/disable widgets option in Home Settings.
- Provide an Add Widget flow.
- Register widget types through a maintainable registry.
- Implement placement, position, size, stacking and persistence using the
  existing desktop coordinate/layout model.
- Allow widgets to be moved and resized where appropriate.
- Allow removal and configuration.
- Store placement per desktop.
- Restore widgets after launcher restart and reboot.
- Respect theme changes.
- Keep widgets in the correct visual layer: below active application windows
  and above the wallpaper, without covering navigation controls.
- Prevent widgets from intercepting unrelated system navigation gestures.
- Avoid excessive periodic refreshes or rendering work.

FIRST WIDGET: NOTES
- Allow adding a Notes widget from the desktop/widget picker.
- Select an existing note or create a note from the widget.
- Display readable sticky-note content on the desktop.
- Provide a clear path to open the full Notes editor.
- Reflect edits in the widget without requiring a reboot.
- Define a sensible refresh/update mechanism.
- Keep widget content synchronized with the Notes persistence layer.
- Make widget colors and typography follow the active theme.
- Provide reasonable defaults for widget size and text wrapping.

SECONDARY DESKTOP VERIFICATION
The Nuxel project has a multi-desktop requirement. Inspect and use the
existing multi-desktop implementation; do not build a separate incompatible
desktop manager.

On the actual test device/profile, create a clearly labelled test note and
place its Notes widget on desktop 2. Use the label:

"PWNAGE-30000 Notes Widget Test"

Verify:
- it is visible on desktop 2;
- it opens the correct note;
- editing the note updates the widget;
- it remains on desktop 2 after app and launcher restart;
- it does not unexpectedly appear on desktop 1;
- desktop switching still works.

Do not seed this test note on every fresh installation. Keep test setup
isolated, and do not delete it automatically from the user's live profile.

If the live target is unavailable, implement an automated integration test
and clearly state that physical desktop-2 verification remains outstanding.

======================================================================
12. NUXTORE — VISUAL REDESIGN
======================================================================

Nuxtore's underlying store functionality is deferred.

For this milestone, make the app visually polished and consistent with the
new default Nuxel theme and the quality of Snekbyte.

Requirements:
- strong app header and branding;
- coherent spacing and typography;
- attractive featured/collection areas;
- well-designed cards, icons, loading and empty states;
- polished responsive mobile layout;
- coherent navigation and buttons;
- proper contrast and touch targets;
- use the shared theme system rather than hardcoded green values.

Any unfinished store actions must be clearly marked "Coming soon" or
disabled. Do not invent real products, purchases, downloads, installation
success or an operational store backend.

The app must still launch and navigate correctly.

======================================================================
13. UNIFIED NUXEL VISUAL THEME SYSTEM
======================================================================

Create a coherent theme system across all Nuxel apps, inspired by the
green colors, visual language and polish of the existing Snekbyte app.

DEFAULT THEME NAME
"Nuxel Grove"

Use this as the default Nuxel theme for fresh installations. Derive the
actual green palette from the existing Snekbyte styling where practical,
rather than inventing an unrelated palette.

SECOND THEME
"Test Theme"

Create a second selectable theme using orange as the primary accent.
It must be a genuinely switchable theme, not a separate app skin.

THEME SETTINGS PAGE
Add a theme section to the Settings application with:
- available theme names;
- preview swatches/cards;
- selected-theme indication;
- clear apply/select behavior;
- immediate theme switching;
- persisted selection;
- sensible fallback if a stored theme is missing or invalid;
- default Nuxel Grove selection on fresh install.

IMPLEMENTATION
- Define shared design tokens for primary/accent colors, backgrounds,
  surfaces, text, borders, focus, status, disabled controls and overlays.
- Use the existing styling system and architecture.
- Migrate app-specific hardcoded styling to shared tokens where feasible.
- Keep status/error colors meaningful and readable across themes.
- Preserve accessibility and text contrast.
- Ensure buttons, dialogs, keyboards, forms, lists, widgets, menus, empty
  states and app headers all follow the active theme.
- Avoid global CSS overrides that break layout or touch handling.
- Avoid duplicating separate theme implementations in every app.
- Apply the theme without requiring a launcher or device restart.
- Persist the choice across app restart and reboot.
- Test theme switching while applications and widgets are open.

All apps should look like members of the same Nuxel ecosystem. Do not
flatten every screen into an identical template; retain appropriate
application-specific identity and information hierarchy.

======================================================================
14. PHOTOS APP → GALLERY
======================================================================

Rename the user-facing Photos app to "Gallery" and make it a real,
basic photo/video gallery.

STORAGE
- Use the user's default Pictures/Photos directory under their home
  according to the conventions discovered in the current OS.
- Create the directory safely if it does not exist.
- Do not assume an arbitrary home path without inspecting the environment.
- Provide a clear indication of which directory is being browsed.
- Avoid duplicating large media files merely to create albums.

ALBUMS
- Treat subfolders as albums.
- Show album names and thumbnails.
- Show images and supported videos in a responsive grid.
- Generate/cache thumbnails using suitable existing tools/libraries.
- Invalidate thumbnails when the source file changes.
- Handle orientation metadata and unsupported formats gracefully.
- Avoid loading full-resolution images for every thumbnail.
- Include loading, empty and unreadable-file states.

MEDIA OPENING
- When a photo is selected, open it in the appropriate installed image/media
  viewer if one exists.
- When a video is selected, use the installed media player if supported.
- Use the platform's actual MIME/default-application association mechanism.
- Provide a useful fallback when no suitable player is installed.
- Never claim a media player exists unless it is detected.

TEST CONTENT
- Generate or copy a small test image into the default Pictures directory.
- Add several example penguin images using existing Nuxel/repository assets
  where available.
- If appropriate assets do not exist, create clearly identified sample
  images using tools available in the actual development environment.
- Never create a fake PNG by saving text with a PNG extension.
- Verify every generated/copied file can be opened and thumbnail generation
  succeeds.
- Keep sample content clearly named and separate from real personal photos.
- Do not overwrite or delete existing user media.

TESTS
- empty gallery;
- folder/album listing;
- image/video filtering;
- thumbnail generation/cache;
- unsupported and corrupt media;
- open-with integration;
- sample assets on the real test device if available.

======================================================================
15. RECORDER APP — VOICE NOTES
======================================================================

Turn Recorder into a straightforward, reliable voice recorder suitable for
everyday voice notes.

UX
- Prominent one-tap Record/Stop button.
- Clear recording state and elapsed time.
- Visible permission, microphone and storage errors.
- Pause/resume if supported by the backend.
- Playback or preview of completed recordings where a player is available.
- A list of previous recordings with date, duration and filename.
- Rename and delete with confirmation if supported by the current file UI.
- Save-location settings.
- Sensible filename defaults and no accidental overwrite.

FORMAT
- WAV/PCM is the default recording format.
- Use a valid supported sample rate/channel format based on the actual
  audio capture backend.
- Do not silently label another codec as WAV.
- Preserve complete valid WAV headers and finalize files after recording.
- Recover gracefully from an interrupted recording where feasible.

SAVE LOCATION
- Default to a sensible voice-recordings folder under the user's home.
- Allow the user to select/change the destination.
- Persist the selected destination.
- Validate that the destination is writable before starting.
- Show a useful error if recording or saving fails.
- Never discard a completed recording silently.

MICROPHONE DIAGNOSTICS
- Inspect the actual available capture devices and audio services.
- Check permissions, device availability, capture format and initialization.
- Use the correct audio stack already installed on Nuxel.
- Do not assume ALSA, PipeWire or PulseAudio is active until verified.
- Provide an explicit microphone test or input-level indicator where
  supported.
- Do not pretend that a microphone is working merely because a device node
  exists.

TESTING
- unit tests using a mock capture backend;
- recording start/stop and error paths;
- valid WAV structure and metadata;
- save-location changes and persistence;
- insufficient storage and permission failures;
- recovery after interrupted recording;
- physical recording, playback and microphone-level test on the device.

A mock recording is useful for automated tests but is not proof of real
microphone capture.

======================================================================
16. WEATHER APP — LIVE ONLINE WEATHER
======================================================================

CURRENT PROBLEM
Weather currently requires manual setting and does not provide a reliable
online lookup experience.

Implement real weather fetching with a sensible online provider, preferably
one that can provide current conditions and forecasts without requiring
unnecessary account setup. Evaluate Open-Meteo or another suitable provider
against the actual project constraints.

DEFAULT EXPERIENCE
- By default, offer to use the system's current location when the location
  provider and permission are available.
- Respect the user's location permission and automatic-location setting.
- If no usable location provider/fix exists, explain that and provide manual
  city search instead of inventing coordinates.
- Do not assume GPS works simply because the Weather app is running.

MANUAL LOOKUP
- Provide a city input field.
- Typing "Eindhoven" and pressing Check/Search must perform a real geocoding
  lookup and then fetch weather for the returned location.
- Show the selected place clearly to avoid ambiguous city matches.
- Manual lookup must continue to work when automatic current-location lookup
  is disabled.
- Provide loading, no-results, network-error, provider-error and offline
  states.
- Do not show hardcoded weather as a successful live lookup.

SETTINGS AND DISPLAY
- Add an explicit setting to enable/disable automatic current-location use.
- Persist the preference.
- Keep manual city lookup available independently of that preference.
- Display actual current conditions and available forecast information.
- Include location name, units and last-updated time.
- Support Celsius/Fahrenheit where practical.
- Cache the last successful result for offline viewing, clearly marked stale.
- Refresh sensibly without unnecessary background polling.
- Attribute the provider as required by its terms.
- Handle time zones and timestamps correctly.

NETWORK AND PRIVACY
- Use HTTPS where supported.
- Do not send precise coordinates unless needed for the selected provider
  and authorized by the user.
- Do not log sensitive location data unnecessarily.
- Respect cancellation, timeouts and network loss.

TESTS
- mock-provider success/failure;
- city geocoding and selection;
- manual Eindhoven lookup;
- automatic-location enabled/disabled;
- permission denial and missing GNSS/provider;
- stale-cache display;
- unit conversion and timestamps;
- malformed provider responses.

Perform a real online lookup if network access is available. Record whether
the real provider request succeeded; do not present a mocked result as proof.

======================================================================
17. SHARED APP SHELL AND LAUNCHER INTEGRATION
======================================================================

Inspect the actual launcher registry and app opening lifecycle.

- Ensure all affected apps launch from their home icons and app drawer.
- Remove stale routes or obsolete app registrations where appropriate.
- Ensure renamed Photos/Gallery has one correct user-facing name and icon.
- Ensure app back navigation returns to the correct prior screen.
- Avoid multiple overlapping instances caused by repeated taps.
- Ensure dialogs and keyboards are dismissed correctly when appropriate.
- Preserve app state during normal navigation.
- Ensure no stale overlay blocks the screen after an app closes.
- Preserve existing Home/Back/Recents behavior.
- Do not kill app processes just to simulate navigation.
- Do not break the existing desktop dock or bottom navigation layer.

Check that the common theme, widget system, haptics and persistence layer
are initialized safely even when an individual service is unavailable.

======================================================================
18. TESTING STRATEGY
======================================================================

Use the real test commands documented by the repository. At minimum, inspect
and run the current baseline commands where applicable:

    python3 -m pytest tests/ -q
    python3 -m pytest tools/beta/live/tests -q

Also run:
- targeted tests for every changed app;
- relevant UI/input regression suites;
- existing launcher, home, lockscreen and touch tests;
- storage and migration tests;
- packaging/hash verification;
- the actual live-deploy manifest validation/dry-run;
- relevant CI/local smoke checks documented by the repository.

Do not invent paths or assume the command above is the complete suite.
Discover the real scripts and their arguments before using them.

TEST COVERAGE MUST INCLUDE

Calendar:
- save, reopen, time picker, obsolete keyboard regression.

Clock:
- all tabs, timer, stopwatch, alarms, persistence and scheduler recovery.

Haptics:
- restored system path, keyboard press, disabled/unavailable motor.

Contacts:
- open, empty state, CRUD and persistence.

Files:
- modal regression, directory listing, CRUD, clipboard, archives and safety.

Mail:
- account configuration, discovery, protocol/auth errors, send/receive
  using controlled test servers, credential redaction.

Messages/Phone:
- app opens, backend absence is handled truthfully, no fake functionality.

Notes:
- save, autosave, restart persistence and error handling.

Widgets:
- placement, resize, removal, theme, desktop isolation, restart persistence,
  Notes synchronization and secondary-desktop test.

Themes:
- default Nuxel Grove, orange Test Theme, immediate switching and persistence.

Gallery:
- albums, sample assets, thumbnails and open-with behavior.

Recorder:
- WAV correctness, error handling and physical microphone test where possible.

Weather:
- live provider path, manual city lookup, automatic-location preference,
  network errors and stale-cache behavior.

Use mocks for deterministic automated testing. Keep physical hardware tests
as separate, explicitly labelled acceptance tests.

Never reduce or disable an existing test merely to make the suite green.
When fixing a failing test, verify that the test still covers the intended
behavior.

======================================================================
19. LIVE-USERSPACE DEPLOYMENT AND PACKAGE INTEGRATION
======================================================================

The project already has a live-userspace deployment and packaging workflow.
Inspect its actual scripts and conventions rather than creating a parallel
deployment mechanism.

Required work:
- include every required changed/new file in the live-userspace package;
- update file manifests and checksums;
- ensure packaged paths match the actual runtime paths;
- check executable permissions and required dependencies;
- validate that app assets, styles, services and configuration are included;
- verify the package with the existing verifier;
- update CI tests and fixtures for the new payload;
- update or extend the deployment manifest using real supported steps;
- run the manifest's non-destructive validation/dry-run;
- document exact backup and rollback steps.

Do not claim the package contains all changed files until the manifest and
hash verifier prove it.

If the S10+ test device is connected and clearly identified, deploy only
through the existing approved live-userspace workflow, after backing up
affected files and verifying rollback. Do not flash or write partitions.

If the device is not connected or its identity is uncertain, finish all
offline implementation, tests and packaging, then report that live-device
verification remains pending. Do not fabricate a deployment result.

======================================================================
20. COMPLETION REPORT AND EVIDENCE
======================================================================

At the end, provide a concise but technically useful PWNAGE-30000 report.

For each component, report:
- STATUS: PASS, PARTIAL, BLOCKED or FAIL;
- root cause discovered;
- implementation changes;
- relevant files changed;
- tests run and actual pass/fail counts;
- real device tests performed;
- remaining hardware or service dependencies;
- exact next action for any blocker.

Provide:
1. Git branch and commit state.
2. A summary of the complete change set.
3. Actual test command outputs/results.
4. Live package file count and hash-verification result.
5. Deployment-manifest validation result.
6. Whether the live userspace was deployed and to which verified target.
7. Which hardware functions were physically tested.
8. Backup and rollback instructions.
9. Known limitations and prioritized next steps.

Do not claim "all done" if a requested component remains broken.
Do not describe mocked functionality as live functionality.
Do not conflate UI tests, service tests and physical hardware tests.

======================================================================
21. REQUIRED EXECUTION ORDER
======================================================================

Work in this order, adapting only when repository dependencies require it:

PHASE A — BASELINE
Inspect repository, identify regressions, run baseline tests and map the
actual architecture. Save evidence.

PHASE B — SHARED FOUNDATION
Repair haptics; inspect keyboard integration; establish shared theme tokens;
fix shared app/overlay lifecycle and persistent settings foundations.

PHASE C — CORE PRODUCTIVITY
Repair Calendar, Clock, Contacts, Files and Notes. Add regression tests.

PHASE D — DESKTOP WIDGETS
Implement the shared widget framework, Notes widget and desktop-2 test.

PHASE E — MEDIA AND HARDWARE-DEPENDENT APPS
Implement Gallery and Recorder. Diagnose microphone capture and test actual
recording where hardware is available.

PHASE F — NETWORK APPS
Implement real Mail configuration and protocol integration; finish online
Weather. Keep Phone/Messages honest about the deferred telephony backend.

PHASE G — VISUAL INTEGRATION
Apply Nuxel Grove and Test Theme consistently. Polish Nuxtore without faking
store functionality. Verify all app launches, navigation, input and layering.

PHASE H — REGRESSION, PACKAGE AND VERIFY
Run all applicable tests, fix regressions, update the live-userspace payload
and hashes, validate deployment manifests, deploy safely if possible, and
write the evidence-based completion report.

Continue through the phases. Do not stop after writing a plan or implementing
only the easiest visual changes.

BEGIN BY INSPECTING THE ACTUAL CHECKOUT, THEN IMPLEMENT PWNAGE-30000.
