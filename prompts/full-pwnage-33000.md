# PWNAGE-33000 — NUXEL APP RESURRECTION & SYSTEM INTEGRATION

**Project:** Nuxel Linux phone OS  
**Target device:** Samsung Galaxy S10+ SM-G975F, Exynos 9820, `beyond2lte`  
**Environment:** Existing Fedora-based ARM64 Nuxel userspace. Inspect the actual running kernel and environment before acting.  
**Mission type:** Native application registration repair, functional mobile apps, shell/navigation integration, filesystem usability, console configuration and regression testing.

# 0. GLOBAL RULES

## Required outcomes

Fix the following:

- Contacts: `/usr/bin/nuxel-contacts` missing or incorrectly registered.
- Camera: backend intentionally deferred; restore visible top bar and Back/Home/Recents.
- Browser: restore visible top bar and Back/Home/Recents.
- Console banner: install `./banner` as `/etc/banner` and configure relevant consoles to display it.
- Files: actual directory listing, visible path and working file operations; remove Upload.
- Mail: usable settings/configuration and compact folder/message UI.
- Messages: repair `/usr/bin/nuxel-messages` registration.
- Nuxtore: preserve the correct empty-store state.
- Phone: repair `/usr/bin/nuxel-dialer` registration.
- Photos: rename the visible application to Gallery and provide photo/video browsing and playback.
- Icons: unify desktop icons with the corresponding app-drawer icons.
- Recorder: make Start Recording work and save to a real user-owned location.
- Home directory: establish a consistent home layout with Desktop, Gallery, Config and useful standard folders.

## Safety and quality rules

1. Inspect the real codebase and running environment before making changes.
2. Preserve unrelated working-tree changes and user data.
3. Do not replace the kernel, flash firmware, write partitions, change the bootloader or perform destructive resets.
4. Preserve the working lockscreen and independent USB/serial recovery route.
5. Do not invent native executables, pretend unsupported hardware works or fabricate files and messages.
6. Do not ship buttons that silently do nothing. Implement them, disable them with a clear reason, or remove them if explicitly required.
7. Use the existing framework, design system and application architecture wherever practical.
8. Test shared components across apps. A fix for one application must not break another.
9. Make changes reversible and document any configuration migration.
10. Do not mark a feature verified unless the relevant behaviour was actually tested.

# 1. FORENSIC AUDIT

Before editing:

- Inspect `git status`, current branch, HEAD, recent commits and relevant diffs.
- Locate the app registry, application manifests, launcher definitions, packaging rules, executable installation paths and icon mapping.
- Identify the current home-directory and user-account configuration.
- Inspect the shell layout, top bar, navigation buttons, app containers, fullscreen handling and stacking/layering rules.
- Locate file explorer operations, mail configuration/storage, audio recording and Gallery/media playback code.
- Inspect console/getty/SSH login configuration and the contents of `./banner`.
- Inspect existing tests, service logs and runtime errors.
- Identify whether each failure originates in the launcher, executable, package, service, permissions, UI, or unavailable hardware.

Create:

`docs/beta-finalization/live/evidence/pwnage-33000/`

Save sanitized diagnostic output, test results and evidence there.

Do not assume the visible error message describes the actual root cause. Trace the complete launch and execution path.

# 2. CONTACTS, MESSAGES AND PHONE — REPAIR NATIVE REGISTRATION

## 2.1 Contacts

The Contacts app reports that the registered native program `/usr/bin/nuxel-contacts` is not installed.

Investigate:

- The canonical app registry and launch metadata.
- The actual Contacts source code and intended entry point.
- Build targets and package manifests.
- Executable installation destinations and permissions.
- Runtime dependencies and startup errors.
- Whether the launcher points to an obsolete executable name.

Implement the correct solution:

- If a Contacts implementation exists, build and install it at the intended location or update the registry to the actual canonical entry point.
- If the app exists under another valid executable name, correct the authoritative registration rather than adding a misleading placeholder.
- If the implementation is incomplete, finish the basic usable Contacts UI and storage integration that the existing architecture supports.

Verify that the app launches, displays a sensible empty state when there are no contacts, and does not crash when its data store is empty or missing.

Where the current project supports contact creation and editing, verify those operations and persistence.

Do not show “program not installed” merely because a registry entry and the installed binary disagree.

## 2.2 Messages

Repair the `/usr/bin/nuxel-messages` launch registration using the same forensic process.

The Messages app must open its intended UI. Do not accidentally route it through Contacts because of a copied registry entry or incorrect component name.

Implement available message-list, conversation and empty-state behaviour according to the existing architecture.

Cellular/SMS transmission may depend on modem and service work outside this mission. Do not fabricate sent messages or claim SMS support is operational if the modem/backend is unavailable.

Show a clear, accurate backend status while keeping the application itself usable.

## 2.3 Phone/Dialer

Repair `/usr/bin/nuxel-dialer` registration and ensure the Phone app opens the intended dialer UI.

Verify that the app is not incorrectly registered to Contacts or another application's executable.

Implement supported UI behaviour such as number entry, editing and clearing, where appropriate to the existing design.

If actual calling requires unavailable modem integration, show a clear status and prevent a misleading claim that a call has been placed. Do not fabricate call state or successful calls.

## 2.4 Shared registration architecture

For all three apps:

- Establish one authoritative source of app IDs, executable entry points, display names and icons.
- Avoid conflicting duplicate registrations.
- Verify the built executable exists at the expected path, is executable and has its dependencies.
- Ensure packaging/deployment installs the executable that the launcher references.
- Ensure error messages name the correct application.
- Add tests that catch missing or mismatched registered executables.
- Add launch smoke tests for Contacts, Messages and Phone.
- Test an empty data store and a backend-unavailable state.

Do not solve missing binaries by creating executable shell scripts that merely open a generic page or print success.

# 3. SHARED SHELL — TOP BAR AND BACK/HOME/RECENTS

## 3.1 Required behaviour

The Camera, Browser and Weather apps must have the system top bar and the three bottom navigation controls visible and usable:

- Back
- Home
- Recents/Tabs

The user must always be able to leave these applications.

Camera backend implementation is explicitly deferred. Do not spend this mission attempting to implement sensor capture, camera drivers or camera hardware support. Fix its surrounding shell integration only.

## 3.2 Investigate the cause

Inspect:

- Fullscreen and immersive-mode flags.
- Shared app container dimensions.
- Top-bar and bottom-navigation mounting.
- Safe-area and reserved-inset calculations.
- Stacking contexts, z-index and overlay layers.
- Application-specific CSS or view settings.
- Orientation and viewport resize handlers.
- Focus and input-event propagation.
- App restoration and navigation lifecycle.

Determine whether apps hide the shell, render outside the normal container or cover navigation with a full-screen surface.

## 3.3 Implement a shared solution

Use the existing shell architecture to enforce a consistent non-immersive application layout for Camera, Browser and Weather.

Requirements:

- Top bar remains visible and readable.
- Back/Home/Recents controls remain visible, clickable and correctly layered.
- Application content occupies the area between the shell bars.
- Content is resized or inset correctly instead of rendering underneath the controls.
- Controls remain visible after orientation changes, application switching and window resizing.
- Browser content remains usable and scrollable.
- Weather remains usable with manual locations.
- Camera can be exited even though camera functionality remains deferred.
- The app cannot override shell navigation merely by requesting fullscreen mode.

Do not duplicate top bars or navigation controls inside individual applications if the system shell already provides them.

Do not use arbitrary z-index values that break the lockscreen, dialogs, quick settings or Recents.

## 3.4 Test the shell

Test all three apps for:

- Initial launch.
- Scrolling and content resizing.
- Back, Home and Recents.
- Switching away and returning.
- Orientation/viewport changes where supported.
- Keyboard display and dismissal where relevant.
- Repeated navigation presses.
- No hidden controls, overlapping shell elements or trapped fullscreen state.

# 4. CONSOLE BANNER — `./banner` TO `/etc/banner`

## 4.1 Inspect the source

Read the repository file `./banner` as plain text. Preserve its intended contents and formatting.

Check for line-ending, encoding and whitespace problems. Do not execute the file as a shell script.

## 4.2 Install the canonical banner

Install the source banner at:

`/etc/banner`

Use the project's normal configuration/package mechanism where possible. Ensure the installed file has appropriate ownership and permissions and is not writable by ordinary users.

Avoid overwriting unrelated system configuration without a backup.

## 4.3 Configure relevant console entry points

Determine which local and remote login paths Nuxel supports, such as:

- Physical TTY/getty consoles.
- USB/serial console login, where applicable.
- SSH sessions.
- Other supported interactive console services.

Configure each applicable entry point to display the contents of `/etc/banner` at the appropriate time.

Important distinctions:

- For local login prompts, inspect the active getty/login configuration and supported issue-file mechanism.
- For SSH, inspect whether the intended banner is pre-authentication or post-authentication. Use the appropriate SSH configuration mechanism for the requested welcome-banner behaviour.
- If a service uses `/etc/issue`, `/etc/motd` or another file, make it reference or derive from the canonical `/etc/banner` source rather than allowing independent banners to drift.
- Do not assume every service automatically reads `/etc/banner`.
- Avoid displaying the same banner twice.
- Do not put shell commands or dynamic untrusted content into a banner configuration.

Validate the relevant configuration before reloading services. Do not terminate the active recovery session or lock the user out of SSH.

## 4.4 Tests

- Verify `/etc/banner` matches the intended source content.
- Verify every supported console path displays the banner exactly once.
- Verify login remains functional.
- Verify SSH configuration syntax before applying changes.
- Document any console path that cannot be tested in the current environment.

# 5. FILES APP — A REAL FILE EXPLORER

## 5.1 Current defect

The Files app shows action buttons such as New Folder, Upload, Rename, Delete, Copy, Cut, Paste, Zip and Extract, but no useful directory path or actual file/folder listing.

The Upload button is nonfunctional and should be removed. This is a local phone file explorer; the user does not need a misleading upload control.

## 5.2 Implement the actual directory view

The main Files screen must show:

- The current absolute or home-relative path.
- Breadcrumbs or an equivalent compact path-navigation control.
- Actual directory entries retrieved from the filesystem.
- File and folder icons appropriate to the content.
- Names, file/folder type and useful metadata such as size or modified date where available.
- Clear loading, empty-directory, permission-denied and error states.
- A way to navigate to the parent directory and home directory.
- Scrollable content that works on the phone screen.

The initial view should open in the current user's home directory, not an empty synthetic page.

Do not populate the interface with fake sample files. Display the actual contents of the selected directory.

## 5.3 Navigation and permissions

Use the actual logged-in user's home path and filesystem APIs.

- Respect file permissions.
- Show useful error messages for inaccessible paths.
- Do not require root access for ordinary user file operations.
- Prevent path traversal and unsafe operations outside permitted locations.
- Handle symlinks carefully and avoid destructive traversal.
- Never silently switch to a different directory when an operation fails.

## 5.4 Implement real file operations

Provide functional operations appropriate to the selected file/folder:

- New Folder.
- Rename.
- Delete with confirmation.
- Copy.
- Cut/move.
- Paste.
- Create ZIP archives.
- Extract supported archives.
- Selection and multi-selection where the existing UI architecture supports it.

Requirements:

- Copy and cut store a real clipboard selection.
- Paste validates destination permissions and handles name conflicts.
- Rename validates the target and handles existing names.
- Delete confirms destructive actions.
- ZIP creation reports success only after the archive exists and is valid.
- Extraction prevents path traversal, including malicious `../` archive entries.
- Errors preserve the original files and report what failed.
- Long operations do not freeze the UI thread.
- Show a clear operation result and refresh the directory listing after changes.

Remove the Upload button and all dead UI/handler references to it. Do not replace it with another misleading control.

## 5.5 File explorer tests

Create temporary test directories and files, then verify:

- Directory listing and navigation.
- Breadcrumb/path updates.
- New folder.
- Rename.
- Copy and paste.
- Cut and move.
- Delete confirmation.
- ZIP creation and extraction.
- Name conflicts.
- Permission failures.
- Empty directories.
- Malformed or unsafe archive entries.
- Correct refresh after each operation.

Never run destructive tests against real user directories.

# 6. HOME DIRECTORY AND STANDARD FOLDER LAYOUT

## 6.1 Establish the real home directory

Determine the actual configured home directory for the user running the Nuxel session. Do not hardcode `/home/user` or assume that the runtime user has a particular name.

Use the operating system's account/home-directory configuration and ensure the desktop shell and applications agree about the path.

## 6.2 Create the intended directory structure

Provide a consistent home directory with at least:

- `~/Desktop`
- `~/Gallery`
- `~/Config`
- `~/Documents`
- `~/Downloads`
- `~/Music`
- `~/Pictures` if needed for compatibility, preferably integrated consistently with Gallery.
- `~/Videos` if needed for compatibility, preferably integrated consistently with Gallery.
- `~/VoiceRecordings`

Add other standard folders only when they serve a real purpose.

Keep system configuration such as `/etc` separate from the user's home configuration. `~/Config` is the user's configuration directory; it is not a replacement for `/etc`.

Use idempotent directory creation so repeated boots do not create duplicates or alter existing ownership unnecessarily.

## 6.3 Integrate apps with the directory structure

- Desktop shortcuts belong in `~/Desktop` if that matches the existing desktop architecture.
- Gallery indexes and browses the intended user media locations.
- Recorder saves to `~/VoiceRecordings` by default.
- Files opens in the home directory.
- User-level app configuration belongs in `~/Config` or the project's established per-app configuration locations, without breaking standard system paths.
- Do not silently relocate existing user files.
- If legacy directories exist, provide a safe migration or compatibility strategy.

## 6.4 Tests

Verify the home path for the actual session user, directory creation, ownership, permissions, persistence across restart and compatibility with all relevant apps.

# 7. MAIL APP — SETTINGS AND A MOBILE-FIRST MAIL INTERFACE

## 7.1 Add an actual Settings/Configuration control

Add a clearly discoverable settings button in the Mail app.

It must open a real settings view that supports the configuration required to connect an email account, including as applicable:

- Display name.
- Email address.
- Incoming protocol: IMAP or POP3.
- Incoming server hostname.
- Incoming server port.
- Incoming TLS/SSL mode.
- Incoming authentication and username.
- Outgoing SMTP server hostname.
- SMTP port.
- SMTP TLS/STARTTLS mode.
- SMTP authentication and username.
- Password or supported authentication method.
- Sender identity.
- Default account and send behaviour.
- Manual settings and account validation.
- Connection testing and actionable error reporting.

Use the project's available mail libraries and protocols. Support IMAP and POP3 for receiving where the current architecture permits, and SMTP for sending.

Do not assume every provider can be autodiscovered. Add safe autodiscovery only where it is supported, and allow manual configuration to remain authoritative.

## 7.2 Credentials and privacy

- Never store passwords in source code, logs or plaintext debug output.
- Use the platform's existing secure credential storage where available.
- If secure storage is not available, clearly document the limitation and use the safest supported local storage approach with restrictive permissions.
- Never log credentials or authentication tokens.
- Validate and sanitize settings input.
- Use secure transport defaults.
- Do not disable certificate verification to make a connection test pass.
- Do not transmit email or credentials to a third-party service except the configured mail provider.

## 7.3 Compact mail layout for a phone

Design a responsive mail interface that works on a narrow screen.

Provide:

- A compact folder/mailbox selector.
- Inbox, Sent, Drafts, Archive and Trash where supported.
- Other folders/labels discovered from the server where available.
- A message list showing sender, subject, date and read/unread state.
- A readable message detail view.
- A clear way to return from a message to the folder list.
- Compose, reply and forward flows where implemented.
- Refresh/sync status and clear empty/loading/error states.
- Appropriate long-message scrolling and keyboard handling.

Use a mobile-first navigation pattern. Avoid forcing a desktop three-column layout onto a phone. A folder drawer or compact folder selector and a single-column message view are preferred.

## 7.4 Real functionality and tests

- Persist configuration across app restarts.
- Verify required fields and valid port numbers.
- Test configuration save/edit/remove.
- Test connection errors and timeouts.
- Test account state when offline.
- Test empty folders and server errors.
- Test folder navigation and message scrolling.
- Test authentication failure without leaking credentials.
- If real mail-server credentials are unavailable, use mocked protocol tests and report that live delivery was not verified.

Never fabricate messages, server connectivity or successful mail delivery.

# 8. PHOTOS BECOMES GALLERY

## 8.1 Naming and registration

Rename the user-facing application from **Photos** to **Gallery**.

Update all relevant visible surfaces:

- App drawer.
- Desktop label.
- Window/app title.
- Settings and app metadata where user-facing.
- Search/launcher display name.
- Relevant user documentation and tests.

Keep internal package identifiers and storage schemas stable unless a migration is genuinely required. Do not break existing shortcuts or user data merely to change the visible name.

## 8.2 Unified media experience

Gallery is intended for both photos and videos.

Implement:

- A responsive thumbnail grid.
- Media type indicators.
- Useful folder/album browsing.
- A detail/fullscreen media viewer with reliable exit navigation.
- Photo display with correct orientation where metadata support exists.
- Video playback using the project's existing supported media stack.
- Play/pause, seek and duration controls for video where supported.
- Clear unsupported/corrupt-media errors.
- Empty state when no media exists.
- Safe refresh when files are added, moved or deleted.

Browse real user media folders consistently, including `~/Gallery` and any compatibility locations that the existing design requires.

Do not generate fake photographs or pretend a video has played when decoding failed.

## 8.3 Tests

Verify:

- Visible name is Gallery everywhere intended.
- Existing media is discovered.
- Empty folders display correctly.
- Photos open and can be exited.
- Supported videos play and can be exited.
- Unsupported formats produce a useful message.
- Shell top bar and navigation remain visible.
- Existing media and shortcuts are preserved.

# 9. DESKTOP AND APP-DRAWER ICON CONSISTENCY

## 9.1 One canonical icon per app

Some apps use different icons on the desktop and in the app drawer. The desktop must use the same icon asset as the corresponding app-drawer entry.

Inspect the canonical app registry, launcher definitions, desktop shortcut generation and icon lookup code.

For each application:

1. Identify the canonical app ID.
2. Identify the icon used by the app drawer.
3. Find the desktop icon source.
4. Replace mismatched desktop references with the canonical app-drawer icon.
5. Keep the app's display name and internal identifier separate.
6. Preserve the existing artwork, theme and intended icon dimensions.

Do not invent replacement artwork or apply a new visual style.

Ensure icons remain correctly scaled and do not become distorted or pixelated due to incorrect asset selection.

## 9.2 Tests

Compare desktop and app-drawer icon references for every registered application. Add a consistency test that catches divergent icon assets for the same app unless an explicit, documented exception exists.

Verify Contacts, Messages, Phone, Browser, Camera, Files, Mail, Gallery, Recorder, Weather and Nuxtore.

# 10. RECORDER — MAKE START RECORDING WORK

## 10.1 Current failure

The Recorder app opens but Start Recording does not work. Its displayed save location is `/VoiceRecordings`, which incorrectly points to a directory at the filesystem root rather than the user's own recording folder.

## 10.2 Trace the recording pipeline

Inspect:

- Start/stop button callbacks.
- UI state transitions.
- Microphone permission and service ownership.
- Available capture devices and audio APIs.
- Supported audio formats.
- Audio session initialization and errors.
- File creation and write permissions.
- Recording lifecycle and resource cleanup.
- Whether the app is waiting indefinitely on an unavailable microphone or audio service.

Do not merely change the button colour or status label.

## 10.3 Implement real recording

Requirements:

- Start Recording begins an actual audio capture session.
- Show recording state and elapsed duration.
- Stop Recording finalizes the file correctly.
- Handle microphone permission denial clearly.
- Handle unavailable microphone hardware or capture services without crashing.
- Avoid blocking the UI during capture.
- Release audio resources when recording stops or the app closes.
- Prevent duplicate simultaneous recordings unless explicitly supported.
- Preserve recordings if the UI is interrupted where the architecture permits.
- Show actionable errors when initialization or writing fails.

## 10.4 Correct the recording directory

Use:

`~/VoiceRecordings`

Resolve this using the actual user's home-directory configuration, not a hardcoded username or `/VoiceRecordings`.

Create the directory if needed with appropriate user ownership and permissions.

Use safe, unique filenames and a real audio extension such as `.wav` when WAV output is actually produced. Do not create an empty file and call it a recording.

The app should display the resolved recording directory and the final saved file path.

## 10.5 Tests

- Start and stop using a mocked capture backend.
- Verify state transitions.
- Verify correct save path.
- Verify a finalized non-empty file in the supported test environment.
- Test permission denial and missing-device behaviour.
- Test storage failure.
- Test stopping and restarting recordings.
- Test that recording does not freeze navigation.

Perform a physical microphone test if the hardware and audio stack are available. If not, distinguish successful mocked tests from unverified physical recording.

# 11. NUXTORE — KEEP THE EMPTY STATE HONEST

Nuxtore currently shows no installed applications, which is correct for the present installation state.

Preserve this behaviour.

Requirements:

- Do not fabricate installed applications.
- Do not add placeholder apps to the installed-app list.
- Clearly distinguish an empty installed list from a loading failure.
- Preserve the existing planned store functionality.
- Keep app discovery/install features deferred if they are not yet implemented.
- Do not break app registration or installed-app detection while repairing other launchers.

Add tests for the genuinely empty state and for future detection of a real installed app.

# 12. SHARED TESTS AND REGRESSION MATRIX

Run all applicable existing tests and add new regression tests for:

### Native apps
- Contacts launches and handles an empty store.
- Messages launches and reports unavailable SMS backend honestly.
- Phone launches and reports unavailable calling backend honestly.
- Registered executable paths match packaged executables.
- App names and icons match their canonical registrations.

### Shell
- Camera top bar and Back/Home/Recents are visible.
- Browser top bar and Back/Home/Recents are visible.
- Weather top bar and Back/Home/Recents are visible.
- Navigation works after app switching and viewport changes.
- No app becomes trapped in fullscreen mode.

### Files and home directory
- Real path and directory entries are displayed.
- File operations work and handle errors safely.
- ZIP extraction rejects path traversal.
- Home directories are created idempotently.
- Existing user files remain intact.

### Mail
- Configuration persists.
- Credentials are not exposed in logs.
- Folder navigation and responsive message view work.
- Offline and authentication failure states are accurate.

### Gallery
- Name is correct throughout the UI.
- Real photos and supported videos open.
- Unsupported media fails clearly.
- Navigation remains available.

### Recorder
- Start and stop recording work in the supported test environment.
- Files are saved under `~/VoiceRecordings`.
- Failure states do not freeze the app.

### Banner
- `/etc/banner` matches `./banner`.
- Relevant console paths display it.
- Login and recovery remain available.

### Nuxtore
- Empty state remains correct when nothing is installed.

Do not delete, weaken or bypass existing tests to obtain a passing result.

# 13. DEPLOYMENT AND ROLLBACK

Before deployment:

- Inspect the final diff.
- Preserve unrelated user modifications.
- Back up modified live configuration.
- Validate executable permissions and package manifests.
- Validate SSH/getty configuration before applying it.
- Run unit tests, integration tests, linters and static checks as appropriate.
- Deploy safe userspace changes to the intended environment.
- Verify the actual deployed version.

Do not flash firmware or partitions, replace the kernel, modify the bootloader or perform destructive resets.

Do not reboot automatically if it would interrupt the active recovery session. Preserve the existing USB/serial recovery path.

Document rollback instructions for configuration, app registration, desktop shortcuts and installed userspace components.

# 14. REQUIRED FINAL REPORT

Store sanitized evidence in:

`docs/beta-finalization/live/evidence/pwnage-33000/`

Report each issue separately with:

- Root cause.
- Changed files.
- Implementation details.
- Tests run and actual results.
- Deployment status.
- Physical-device verification status.
- Remaining blockers and their evidence.
- Rollback instructions.

Specifically report:

1. Whether Contacts, Messages and Phone launch from their canonical registrations.
2. Whether Camera, Browser and Weather all retain visible system navigation.
3. Which console paths display `/etc/banner`.
4. Whether Files displays real entries and all implemented operations work.
5. Whether Mail settings persist and real protocol tests were performed.
6. Whether Gallery opens actual photos and supported videos.
7. Whether desktop and app-drawer icons match.
8. Whether Recorder creates a real recording at the resolved user path.
9. Whether Nuxtore remains honestly empty.
10. Whether the home-directory structure persists across restart.

Classify every item as `FIXED`, `PARTIALLY FIXED`, `BLOCKED` or `NOT REPRODUCED`.

Never mark an app fully functional solely because its window opens. Never claim real email delivery, SMS, calling, audio capture or video playback without evidence of the relevant functionality.

**Begin with forensic investigation. Implement the changes in the specified order, run the tests and verify the deployed system. Do not stop at a plan.**
