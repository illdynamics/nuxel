# FULL-PWNAGE-93000
# NUXEL — LAUNCHER ICON DEDUPLICATION, SOUND-MODE STATUS ICONS, COMPLETE NOTIFICATION SYSTEM & HOME INPUT-OVERLAY REPAIR

## Maximum-detail source analysis, implementation, integration, performance optimization, regression testing and physical S10+ validation

**Mission ID:** PWNAGE-93000  
**Target OS:** Nuxel — custom Fedora-based ARM64 mobile Linux  
**Primary device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**Primary UI:** Nuxel Home PWA, Settings PWA, native Wayland components and integrated application windows  
**Bridge:** `services/nuxel-bridge`  
**Session/runtime:** Existing Nuxel session services, Wayland compositor, PWA host and native application management  
**Mission type:** Source-level analysis, implementation, integration, performance optimization, testing and safe deployment

---

# 0. MISSION OBJECTIVE

Nuxel is already a substantial mobile Linux system. This mission is an integration and quality pass over four areas where the current experience is incomplete or inconsistent.

The agent must inspect the complete current repository and establish the actual runtime architecture before making changes.

The mission has four major deliverables.

### A. Remove duplicate launcher icons for GTK and Flatpak applications

GTK and Flatpak applications currently appear to have two icons:

- Their original application icon, which we want to preserve.
- An additional Nuxel custom-style icon, which we want removed for these applications.

The desired result is that GTK and Flatpak applications display their original upstream/application-provided icon without Nuxel adding a second decorative icon or duplicate representation.

Native Nuxel applications must retain their intended Nuxel icon artwork.

This is also a performance optimization: reduce unnecessary icon rendering, image decoding, DOM elements, asset lookups and redundant launcher work.

### B. Replace the sound-mode status icon

The existing sound-mode icon currently looks like a block and is not sufficiently recognizable.

Replace it with a speaker icon of the same visual footprint and status-bar size.

It must distinguish three modes clearly:

1. Normal: speaker icon.
2. Vibrate: speaker icon with a red forbidden line and visible vibration-wave stripes.
3. Silent: speaker icon with a red forbidden line and a red cross.

The visual state must correspond to the actual authoritative sound-mode state, not an independently maintained UI guess.

### C. Implement the complete notification system

The current notification bell displays a count of seven notifications, but no corresponding notifications are visible to the user.

This must be fixed as a complete end-to-end system.

The desired experience:

- A notification indicator remains in the top bar.
- Its number reflects the actual notification count according to the agreed count policy.
- Swiping down twice opens expanded Quick Settings.
- Below all Quick Settings buttons and system-status information, display a proper notification list.
- Notifications must be readable and actionable.
- Swipe left to archive a notification.
- Swipe right to mark a notification as read.
- Marking a notification read must NOT immediately remove it from the list.
- Read notifications remain visible as reminders until archived or otherwise removed through the defined retention policy.

The notification system must not be a decorative mockup. It must receive, persist, display, update and manage real notifications.

### D. Fix the invisible Home/input overlay after leaving applications

There is an intermittent issue:

1. An application is open.
2. The user presses the Back arrow once using the triple-button navigation dock.
3. The user returns to the desktop.
4. The desktop looks normal.
5. However, an invisible screen, overlay or input surface sometimes remains active over the desktop.
6. The user can no longer open the application drawer using the normal swipe gesture.
7. Holding Back to kill the foreground application makes the desktop responsive again.

This strongly suggests that the single-Back path is leaving stale foreground/window/input state behind.

The actual cause must be found.

Potential areas to investigate include:

- stale Wayland surfaces;
- orphaned layer-shell surfaces;
- stale WebKit overlays;
- invisible modal backdrops;
- input regions that remain active after a window is hidden;
- incorrect pointer/touch event routing;
- stale gesture arbitration state;
- incorrect focus ownership;
- application lifecycle transitions;
- incomplete window unmapping;
- stale PWA host state;
- navigation dock IPC state;
- compositor activation/deactivation;
- hidden surfaces that remain above Home;
- incorrect Home visibility/interactive state;
- a difference between normal Back and long-Back termination.

Do not assume any one of these is the cause. Prove the root cause from source and runtime evidence.

---

# 1. NON-NEGOTIABLE IMPLEMENTATION RULES

## 1.1 Deep-analysis requirement

Before modifying code, inspect the complete repository to the maximum useful detail.

Do not begin by immediately editing the four visible UI elements.

Inspect:

- repository structure;
- source history where relevant;
- project documentation;
- architecture documentation;
- active runtime configuration;
- build scripts;
- image/rootfs construction;
- package manifests;
- application registry;
- icon assets and icon mapping;
- launcher rendering;
- native application launch and lifecycle;
- GTK integration;
- Flatpak integration;
- desktop-entry discovery;
- status-bar rendering;
- sound-mode backend;
- Quick Settings implementation;
- notification-related services;
- D-Bus integration;
- Wayland layer-shell integration;
- PWA host;
- input handling;
- gesture recognition;
- application focus and activation;
- Back/Home/Tabs navigation;
- systemd units;
- test suites;
- deployment scripts.

Inspect all relevant files and trace the active execution path.

The source tree may contain multiple generations of implementations. The newest-looking directory is not automatically the deployed implementation.

## 1.2 Preserve existing functionality

Do not regress:

- Home desktop and launcher;
- app drawer;
- lockscreen;
- lock/unlock gestures;
- Back/Home/Tabs navigation;
- app launch;
- app minimization;
- native GTK windows;
- Flatpak windows;
- Quick Settings;
- Wi-Fi and Bluetooth indicators;
- USB and Tri-Link indicators;
- charging and battery indicators;
- sound playback;
- alarms and timers;
- haptics;
- notification delivery from existing applications;
- screen wake behavior;
- touch input;
- display rendering.

## 1.3 No fake implementations

A button, icon or counter must never claim that an operation succeeded when the backend did not complete it.

Do not create:

- hardcoded notification counts;
- static notification examples presented as real;
- fake sound-mode states;
- fake archive/read operations;
- decorative swipe animations without persistence;
- dummy GTK/Flatpak icon metadata;
- UI-only focus fixes that leave native surfaces active.

## 1.4 No unnecessary graphics-stack changes

Preserve the established display architecture.

Do not:

- introduce another `/dev/fb0` writer;
- force software rendering to fix icon issues;
- disable GPU acceleration;
- change global resolution or DPI;
- replace the compositor;
- change the framebuffer bridge;
- introduce expensive continuous animations.

Any graphics or rendering changes must be measured against the actual deployed presentation path.

---

# 2. PHASE ZERO — BASELINE, SOURCE IDENTITY AND RECOVERY

Before implementation:

1. Record repository root, branch, commit SHA and dirty-tree state.
2. Record uncommitted user changes.
3. Identify remotes and current deployment target.
4. Identify the exact S10+ build currently running.
5. Identify the active Home shell and PWA host.
6. Identify the active compositor and native navigation dock.
7. Identify the systemd services involved in application lifecycle, status bar, sound and notifications.
8. Capture existing test results.
9. Preserve current configuration and any files that will be modified.
10. Establish a rollback path.

Never use destructive Git operations to make the working tree clean.

Do not reset, force-checkout, force-push or delete unrelated user work.

For remote-device work:

- discover the current SSH endpoint instead of trusting an old address;
- verify the host identity;
- verify the target model and running Nuxel build;
- verify the effective user before privileged operations;
- preserve SSH host-key checking;
- do not place credentials in scripts or logs;
- do not flash boot, recovery, kernel, modem or firmware partitions for this userspace mission.

If the phone cannot be reached safely, complete local implementation and report the deployment blocker.

---

# 3. PHASE A — GTK/FLATPAK ICON DEDUPLICATION

## 3.1 Establish the current icon pipeline

Inspect the actual launcher implementation and identify:

- where installed applications are discovered;
- how `.desktop` entries are parsed;
- how application IDs are normalized;
- how Flatpak exports are discovered;
- how native GTK applications are identified;
- how icons are resolved;
- how Nuxel custom icons are assigned;
- whether the launcher adds an overlay or fallback icon;
- whether multiple application records are being created;
- whether duplicate entries arise from app-registry reconciliation;
- whether icons are rendered by CSS, HTML, SVG, native GTK or another layer.

Inspect the current application registry and icon assets.

Likely areas include, but are not limited to:

```text
pwa/nuxel-home/
pwa/nuxel-common/
pwa/nuxel-apps/
services/nuxel-bridge/
assets/nuxel-applications-icon-pack/
```

Find the actual active implementation rather than assuming these paths are exhaustive.

## 3.2 Required icon policy

Implement one explicit icon-origin policy.

| Application type | Required icon |
|---|---|
| Native Nuxel-built application | Nuxel custom icon |
| GTK application | Original application icon |
| Flatpak application | Original application icon |
| Browser/PWA application | Existing intended application icon policy |
| Unknown application | Existing safe fallback |

GTK and Flatpak applications must not receive the additional Nuxel custom-style icon.

Do not remove or replace their original icons.

Do not disable icon rendering globally.

Do not alter the visual identity of Nuxel's own applications.

## 3.3 Correct the underlying mapping

Investigate whether the duplication comes from:

- app registry entries;
- multiple desktop-file records;
- icon overlay rendering;
- custom icon fallback logic;
- app source classification;
- duplicate launch identifiers;
- mismatched desktop-file IDs;
- Flatpak export discovery;
- duplicate native/Flatpak package registrations.

Fix the authoritative source of duplication.

Do not solve this by hiding arbitrary elements with a broad CSS selector if the actual cause is incorrect application classification or duplicate registry entries.

Where the same app is discovered through multiple sources, reconcile it into one canonical application record.

Preserve the correct launch target and package provenance.

## 3.4 Icon loading and performance

Measure before and after:

- number of icon DOM elements per launcher view;
- number of image requests;
- duplicate image decoding;
- icon asset lookup count;
- launcher render duration;
- application registry reconciliation time;
- memory usage attributable to icon assets where measurable.

Avoid introducing unnecessary image conversions or repeated filesystem scans.

Reuse decoded assets and existing cache infrastructure where appropriate.

Do not add a cache that can permanently serve stale application icons after package updates.

## 3.5 Tests

Add tests for:

- native Nuxel app receives Nuxel icon;
- GTK app receives original icon;
- Flatpak app receives original icon;
- unknown app receives valid fallback;
- duplicate desktop entries resolve to one application record;
- missing original icon is handled safely;
- package update changing an icon refreshes the appropriate cache;
- launcher does not add a Nuxel overlay to GTK/Flatpak applications.

Test both registry output and actual rendered launcher output.

---

# 4. PHASE B — SOUND-MODE STATUS ICON REDESIGN

## 4.1 Inspect the actual state authority

Trace the existing sound-mode state from hardware/backend to status bar.

Determine the authoritative states and their exact meanings.

At minimum, distinguish:

- Normal;
- Vibrate;
- Silent.

Investigate whether the backend has additional states such as DND or a temporary mute.

Do not silently conflate DND with Silent.

Do not change the actual audio policy as part of a visual icon task.

The status bar must reflect the real current mode.

## 4.2 Visual requirements

Replace the current block-shaped icon with a speaker.

Maintain the same existing status-bar footprint, approximate size, alignment and spacing.

Use a consistent vector drawing style matching the other Nuxel status icons.

Prefer inline SVG or an existing suitable local vector asset.

Avoid emoji and font-dependent symbols.

### Normal mode

<escape> </escape>
- Speaker body and cone.
- No red line.
- No cross.
- No vibration stripes.
- Clearly recognizable as sound enabled.

### Vibrate mode

- Same speaker silhouette.
- Red forbidden/mute line over the speaker.
- Visible vibration-wave stripes around the speaker.
- Vibration waves must remain visible and recognizable despite the forbidden line.
- The user should immediately recognize that the device is vibrating rather than fully silent.

### Silent mode

- Same speaker silhouette.
- Red forbidden/mute line.
- Red cross/X mark.
- No vibration-wave stripes.
- Must be visually distinguishable from Vibrate at a glance.

## 4.3 Rendering constraints

- Keep the existing status-cell dimensions.
- Do not enlarge the status bar.
- Do not shift the Wi-Fi, battery, cellular or other indicators.
- Respect existing safe zones.
- Do not introduce overlap.
- Do not continuously animate the speaker.
- Ensure the icon is crisp at the actual phone resolution.
- Maintain sufficient contrast in the current Nuxel theme.

If the icon is generated in CSS, consider moving to a single SVG renderer if that simplifies the implementation and reduces duplicate rendering.

Do not render both CSS pseudo-elements and an SVG version simultaneously.

## 4.4 Accessibility

Provide meaningful accessible labels:

- `Sound normal`
- `Vibrate mode`
- `Silent mode`

The icon must not be the only source of state information.

## 4.5 Tests

Test every authoritative sound-mode transition.

Verify:

- Normal → Vibrate;
- Vibrate → Silent;
- Silent → Normal;
- changes initiated from Quick Settings;
- changes initiated through hardware buttons;
- state refresh after screen wake;
- state refresh after Home reload;
- state refresh after sound service restart.

The icon must never remain in a stale state after the backend changes.

---

# 5. PHASE C — COMPLETE NOTIFICATION SYSTEM

This is a major feature, not a small icon fix.

## 5.1 Establish the current notification architecture

Deep-inspect:

- notification bell and badge;
- current notification counter;
- any notification list or drawer;
- Quick Settings expanded mode;
- notification APIs in the Bridge;
- D-Bus notification integration;
- application notification permissions;
- desktop notification server/provider;
- existing persistence mechanisms;
- notification event sources;
- notification actions;
- service lifecycle;
- application IDs and icon resolution.

Search the entire repository for:

```text
notification
notifications
org.freedesktop.Notifications
Notify
CloseNotification
GetCapabilities
GetServerInformation
notification-count
notification-badge
status-notification
```

Use the exact architecture found in the repository.

Do not introduce a second competing notification daemon if an existing authoritative provider is already present.

## 5.2 Define one canonical notification model

Create or repair a single canonical notification model.

At minimum, every notification should support:

- stable unique ID;
- application ID;
- application display name;
- title;
- body;
- timestamp;
- received time;
- read/unread state;
- archived state;
- icon or application identity;
- urgency;
- optional actions;
- optional expiration metadata;
- source/provider identity.

Keep notification content separate from transient display state.

The model must support notification updates and replacement according to the existing notification protocol where applicable.

Do not create duplicate notification records when an application updates an existing notification.

## 5.3 Notification lifecycle

Implement a clear lifecycle.

Suggested logical states:

```text
RECEIVED
  |
  v
ACTIVE_UNREAD
  |
  +---- swipe right ----> READ
  |                       |
  |                       +---- remains visible as reminder
  |
  +---- swipe left -----> ARCHIVED
                          |
                          +---- hidden from active reminder list
```

The implementation may use separate `read_at` and `archived_at` timestamps instead of a single enum.

That is preferable if it avoids losing history or makes synchronization clearer.

Important:

**Marking a notification read must not archive it.**

A read notification remains visible in the reminder list.

Archiving removes it from the active reminder list without deleting its durable record immediately.

## 5.4 Notification count semantics

The current bell displays seven notifications despite no visible notifications.

Find out where that number originates.

It could be:

- a hardcoded count;
- stale in-memory state;
- a backend count with no corresponding records;
- an unread counter disconnected from persistence;
- a failed notification-list query;
- a badge that never resets;
- a provider reporting active notifications while the UI has no access to them.

Fix the root cause.

Define the badge semantics explicitly.

Recommended default:

- The badge represents the number of unarchived unread notifications.
- Read notifications remain visible in the list but no longer increase the unread badge.
- Archived notifications are not counted.
- If there are no unread notifications, hide the number or show the existing zero-state design.
- Never show a nonzero count without corresponding persisted notification records.

If existing Nuxel product conventions require a different count definition, document it and implement it consistently.

## 5.5 Persistent storage

Notifications must survive:

- Home PWA reload;
- notification UI component reload;
- Bridge service restart;
- system session restart where the chosen retention policy permits;
- device reboot.

Inspect existing storage architecture first.

Use the current database/state mechanism if suitable.

If new storage is necessary:

- use a transactional approach;
- version the schema;
- add migrations;
- avoid storing unbounded notification history;
- implement a documented retention policy;
- preserve notifications across ordinary service restarts;
- handle corrupt or partially written records safely;
- ensure multiple consumers cannot overwrite newer state with stale snapshots.

Do not store secrets or authentication tokens inside notification records.

## 5.6 D-Bus notification integration

If Nuxel already implements `org.freedesktop.Notifications`, audit its completeness.

Check:

- `Notify`;
- `CloseNotification`;
- `GetCapabilities`;
- `GetServerInformation`;
- replacement notification IDs;
- application identity;
- urgency;
- hints;
- action registration;
- expiration behavior;
- D-Bus owner lifecycle.

If the implementation is incomplete, finish the supported protocol behavior.

If another service currently owns the notification bus name, identify it before replacing or modifying anything.

Do not create a bus-name conflict.

Do not silently swallow application notifications.

Make failures visible in logs and diagnostics.

## 5.7 Quick Settings expanded notification layout

The user-visible requirement is specific:

1. First downward swipe retains the existing Quick Settings behavior.
2. Second downward swipe opens the expanded mode.
3. Expanded mode displays all existing buttons and system statuses first.
4. Below those controls and statuses, display the notification list.

The notification list must not replace or cover the Quick Settings buttons.

The layout must be usable in portrait and landscape.

It must respect:

- screen insets;
- top status-bar area;
- bottom navigation dock;
- scroll boundaries;
- safe touch targets;
- keyboard state;
- device rotation;
- current lock/session state.

If the expanded panel cannot fit all notifications, it must scroll naturally.

Do not make the entire screen scroll in a way that breaks the existing Quick Settings interaction.

Prefer a clearly bounded notification-list region within the expanded panel.

## 5.8 Notification card design

Each notification should present:

- application icon;
- application name;
- title;
- body;
- relative or formatted timestamp;
- read/unread appearance;
- urgency where relevant;
- action buttons when genuinely supported.

Do not invent application icons.

Reuse the correct existing application icon resolution policy.

The read state should be visually apparent without making the text unreadable.

The archived state should remove the item from the active list with a restrained transition.

Do not introduce large glowing effects or expensive blur/transparency.

Use Nuxel's established visual language.

## 5.9 Swipe left — archive

A left swipe archives the notification.

Requirements:

- detect a deliberate horizontal gesture;
- distinguish horizontal swipe from vertical list scrolling;
- provide a restrained visual preview;
- commit only after a defined threshold;
- animate the item out;
- persist the archive operation;
- update the badge immediately from authoritative state;
- prevent accidental archive during ordinary scrolling;
- provide a safe way to recover archived notifications if the existing design supports an archive/history view.

Do not delete the notification record immediately.

## 5.10 Swipe right — mark read

A right swipe marks the notification as read.

Requirements:

- distinguish it from a left swipe;
- use an accessible visual indication;
- persist the read state;
- update the unread badge;
- keep the notification visible;
- keep it in the reminder list;
- avoid making the item disappear;
- support repeated UI reloads without reverting its read state.

A read notification must not be silently archived.

## 5.11 Touch and gesture arbitration

The Quick Settings panel already has vertical gestures.

The notification list introduces horizontal gestures.

Implement gesture arbitration carefully:

- vertical movement belongs to scrolling;
- horizontal movement belongs to notification actions after the direction is established;
- small movements should not trigger an action;
- touch cancellation must reset gesture state;
- pointer/touch interruption must not leave a stuck gesture;
- gesture state must reset when the panel closes;
- gesture state must reset on screen rotation;
- accessibility alternatives must exist for users who cannot swipe.

Do not break the existing double-swipe-to-expand interaction.

## 5.12 Empty and error states

When no notifications exist, display a polished empty state.

Suggested text:

`You're all caught up.`

If notification retrieval fails:

- display a truthful error or unavailable state;
- do not display an old nonzero count as if it were current;
- retain persisted data where possible;
- log the failure;
- provide retry behavior.

## 5.13 Notification permissions and app integration

Inspect whether Nuxel already has an application notification permission model.

If permissions exist, use them.

If a permission manager is active, ensure notification permission requests pass through the canonical permission system.

Do not create a parallel per-app permission database.

Provide accurate app-level notification controls if the existing Settings architecture supports them.

Do not silently disable notifications for Flatpak applications because they use a sandbox.

Inspect the actual D-Bus portal and notification path for Flatpak.

## 5.14 Performance

Notification UI must be efficient.

Avoid:

- rerendering the complete Quick Settings tree for every notification;
- polling continuously at high frequency;
- repeatedly decoding the same application icons;
- loading the entire notification history into the UI;
- excessive DOM nodes;
- unnecessary CSS filters;
- continuous animation;
- duplicate notification event subscriptions.

Use bounded history queries and incremental updates.

Measure:

- notification insertion latency;
- notification list rendering time;
- Quick Settings expansion time;
- memory use with a representative notification list;
- CPU usage while the panel is open and closed.

## 5.15 Notification tests

Create tests for:

1. New notification received.
2. Notification displayed.
3. Notification persisted.
4. Badge increases correctly.
5. Notification replacement updates existing record.
6. Notification marked read.
7. Read notification remains visible.
8. Badge decreases after marking read.
9. Notification archived.
10. Archived notification disappears from active list.
11. Archived notification is not counted.
12. Home reload preserves notification.
13. Bridge restart preserves notification.
14. Invalid notification data is handled safely.
15. Duplicate events do not create duplicate records.
16. Notification list scrolls.
17. Left swipe archives.
18. Right swipe marks read.
19. Vertical scrolling does not trigger archive/read.
20. Screen rotation does not leave gestures stuck.
21. Empty state appears correctly.
22. Provider failure does not display fabricated notifications.
23. Flatpak-originated notifications reach Nuxel.
24. Native GTK notifications reach Nuxel.
25. Badge count always matches the documented policy.

Perform at least one physical notification test from an actual GTK application and one from an actual Flatpak application if both are installed.

---

# 6. PHASE D — FIX THE INVISIBLE HOME INPUT OVERLAY

This is a critical interaction defect.

## 6.1 Reproduce before changing code

Establish a repeatable test.

1. Boot or unlock Nuxel.
2. Open Home.
3. Open the app drawer.
4. Launch a native GTK application.
5. Press the Back arrow once.
6. Confirm the desktop is visible.
7. Attempt the normal swipe to open the app drawer.
8. Record whether the gesture works.
9. Repeat with a Flatpak application.
10. Repeat with a PWA application.
11. Repeat with applications that have internal navigation history.
12. Repeat with applications that do not have internal navigation history.
13. Repeat with an application that opens a modal/dialog.
14. Repeat with an application that has multiple windows.
15. Repeat after screen wake and rotation.

Record the result for each case.

Determine whether the failure is deterministic, intermittent or specific to one application type.

## 6.2 Compare short-Back and long-Back paths

The user reports that holding Back to kill the foreground app restores functionality.

Compare the exact code paths for:

- short Back;
- long Back;
- Home button;
- Tabs button;
- app close;
- app minimize;
- compositor unmap;
- app process termination.

Find what long-Back does that short-Back does not.

Do not simply make short-Back terminate the application.

Normal Back must preserve its intended navigation semantics.

## 6.3 Trace the complete lifecycle

Follow the lifecycle across all relevant components.

Inspect:

- native button manager;
- button event routing;
- navigation dock;
- PWA host;
- application registry;
- application bridge;
- Wayland toplevel management;
- layer-shell surfaces;
- compositor focus and activation;
- window hide/minimize logic;
- Home visibility;
- gesture recognizer;
- touch event forwarding;
- pointer constraints;
- input regions;
- overlay/modal state;
- webview focus;
- native app focus;
- app termination and cleanup.

Identify the exact transition sequence after a single Back press.

Determine whether the app is:

- still mapped;
- unmapped but retaining an input region;
- minimized but still receiving touch;
- covered by a transparent layer;
- holding focus;
- holding a pointer/touch grab;
- leaving a stale modal;
- leaving a stale navigation state;
- blocking Home's gesture recognizer.

Do not assume that a visually invisible surface is actually absent.

## 6.4 Inspect Wayland surfaces and input regions

If a native surface is involved, inspect its actual Wayland lifecycle.

Verify:

- map/unmap events;
- surface destruction;
- layer-shell level;
- keyboard interactivity;
- pointer interactivity;
- input region;
- opaque region;
- activation state;
- focus state;
- surface stacking;
- buffer attachment;
- subsurface lifecycle.

A transparent surface can still intercept touch if its input region remains active.

A hidden window can still cause problems if it retains a grab or an incorrectly configured input region.

Do not treat `opacity: 0`, `visibility: hidden` or a large negative z-index as a complete native input cleanup strategy.

## 6.5 Inspect PWA and DOM overlays

If the remaining layer is inside the Home WebView, inspect:

- modal backdrop;
- drawer backdrop;
- application transition overlay;
- app-launch loading surface;
- keyboard overlay;
- gesture-capture layer;
- pointer-events state;
- touch-action settings;
- fixed-position elements;
- full-screen containers;
- stale CSS classes;
- event listener lifecycle;
- z-index and stacking contexts.

Check for invisible elements that remain with:

```text
pointer-events: auto
```

Check whether a hidden element still owns a gesture listener or touch sequence.

A hidden overlay must not intercept input.

## 6.6 Establish a single authoritative foreground state

There must be one authoritative application/session state that all relevant components consume.

At minimum, distinguish:

- HOME_ACTIVE;
- APP_ACTIVE;
- APP_MINIMIZED;
- APP_CLOSING;
- LOCKED;
- TRANSITIONING;
- UNKNOWN/ERROR.

Use the project's existing state machine if one exists and can be repaired.

Do not create a competing state authority.

State transitions must be explicit and observable.

## 6.7 Required short-Back lifecycle

The exact implementation must follow the existing intended Back contract, but the outcome must satisfy this sequence:

1. Receive a valid short-Back event.
2. Determine whether the foreground app has internal navigation history.
3. If internal navigation is available, perform the app's Back operation.
4. If the app is at its navigation root, perform the established return-to-Home behavior.
5. Deactivate or minimize the foreground application through the authoritative lifecycle.
6. Update compositor focus/activation.
7. Remove or deactivate temporary app overlays.
8. Release stale input grabs or gesture ownership.
9. Restore Home's interactivity.
10. Ensure the app drawer gesture recognizer is ready.
11. Confirm the desktop is visible and accepts input.

Do not send Back indiscriminately to all applications.

Do not broadcast keyboard events globally.

Do not weaken Flatpak sandboxing.

Do not kill the app when a normal Back operation should navigate within it.

## 6.8 Cleanup must be idempotent

Implement lifecycle cleanup so repeated cleanup requests are safe.

Examples:

- app already unmapped;
- overlay already removed;
- focus already returned to Home;
- application exits while Back is being processed;
- PWA host reloads during transition;
- app crashes during minimize;
- user presses Home during an app transition.

Do not leave stale state when operations race.

## 6.9 Timeouts and failure behavior

Avoid arbitrary sleeps as the primary fix.

Use explicit state confirmation, IPC acknowledgement or compositor lifecycle events where available.

If a surface fails to unmap:

- record its identity;
- report the failure;
- attempt the existing safe cleanup path;
- restore Home input only when it is safe;
- avoid terminating unrelated processes.

A timeout may be used as a bounded safety mechanism, but it must not conceal a failed transition.

## 6.10 Home gesture readiness

The Home app drawer must only depend on the real Home/input state.

After an application returns to Home:

- the drawer gesture must be registered;
- the Home desktop must receive touch events;
- no invisible surface may cover the gesture region;
- the first swipe must work;
- the user must not need to press long-Back;
- the user must not need to reopen Home;
- the user must not need to restart the PWA host.

## 6.11 Diagnostics

Add useful diagnostics for:

- foreground app identity;
- current lifecycle state;
- active Wayland toplevels;
- mapped/unmapped state;
- active overlays;
- focused surface;
- input region state where inspectable;
- pending transitions;
- last navigation event;
- cleanup result;
- Home gesture readiness.

Diagnostics must be bounded and avoid logging sensitive notification contents or user data.

## 6.12 Regression tests

Test:

- native GTK app → short Back → Home → drawer swipe;
- Flatpak app → short Back → Home → drawer swipe;
- PWA app → short Back → Home → drawer swipe;
- app with internal history → Back navigates internally;
- app at root → Back returns Home;
- long-Back retains existing close behavior;
- Home button returns Home;
- Tabs button retains its existing behavior;
- app with modal → Back handles modal correctly;
- app crash during transition;
- PWA host reload during transition;
- repeated Back presses;
- rapid Back/Home/Tabs sequences;
- display off/wake;
- screen rotation during transition;
- notification panel open/close followed by app launch;
- Quick Settings gestures still work after returning Home.

Run repeated cycles, not just one successful test.

Minimum physical-device validation: 20 app-exit cycles across native GTK, Flatpak and PWA applications, with no stuck input overlay.

---

# 7. PHASE E — CROSS-FEATURE INTEGRATION

The four deliverables must work together.

Test the following combinations:

1. Open a Flatpak application, verify its original icon in the launcher, return Home and open the drawer.
2. Open a GTK application, generate a notification, return Home and verify notification persistence.
3. Change Normal → Vibrate while Quick Settings is open.
4. Change Vibrate → Silent and verify the cross icon.
5. Receive a notification while the notification panel is closed.
6. Open expanded Quick Settings and verify the new notification appears below all controls.
7. Mark a notification read, close Quick Settings, reopen it and verify the notification remains.
8. Archive a notification, close Quick Settings, reopen it and verify it is no longer in the active reminder list.
9. Return from an application with one Back press while notifications exist.
10. Open the app drawer immediately after closing Quick Settings.
11. Open an application, receive a notification, return Home and verify no stale overlay blocks input.
12. Lock and unlock the device with notifications present.
13. Restart the Bridge and verify notification state.
14. Restart Home and verify icon and sound-mode state hydration.

No feature may break another feature's event handling.

---

# 8. PHASE F — PERFORMANCE MEASUREMENT AND OPTIMIZATION

The user explicitly wants the icon deduplication to potentially improve performance.

Measure actual results rather than inventing percentage improvements.

## 8.1 Baseline

Before changes, measure where practical:

- Home initial render;
- app drawer open latency;
- launcher scroll frame pacing;
- application icon element count;
- icon asset lookup count;
- duplicate icon/image count;
- Quick Settings expansion time;
- notification panel rendering;
- memory usage;
- CPU use while idle;
- application exit-to-Home latency;
- Home gesture readiness after app exit.

## 8.2 After changes

Repeat the same measurements under comparable conditions.

Record:

- baseline;
- after;
- absolute difference;
- percentage difference;
- test conditions;
- sample count;
- measurement method.

Do not report performance gains that were not measured.

Do not attribute an improvement to icon deduplication if other variables changed at the same time.

## 8.3 Rendering requirements

Keep the existing fbdev/Wayland presentation architecture.

Prefer:

- fewer DOM elements;
- fewer redundant icons;
- fewer repeated image decodes;
- incremental notification updates;
- bounded list rendering;
- state-change-driven icon updates;
- event-driven status refresh;
- simple vector artwork;
- restrained transitions.

Avoid:

- excessive blur;
- unnecessary transparency;
- continuous polling;
- continuous animation;
- duplicate event listeners;
- full UI rebuilds for small state changes.

---

# 9. PHASE G — TESTING AND QUALITY GATES

Run the project's established test suites.

Discover the current commands from the repository instead of assuming old commands remain valid.

Run:

- relevant unit tests;
- relevant integration tests;
- UI tests;
- launcher/app-registry tests;
- notification tests;
- sound-mode tests;
- gesture tests;
- native lifecycle tests;
- build checks;
- packaging checks;
- smoke tests;
- applicable golden tests.

Do not report tests as passed if they were skipped or never executed.

If a test cannot run because of missing hardware, unavailable service or missing dependency, label it BLOCKED and explain why.

## 9.1 Required test evidence

Include actual outputs or concise test summaries.

At minimum, prove:

- icon classification is correct;
- no duplicate GTK/Flatpak icon is rendered;
- native Nuxel icons remain;
- sound modes are visually distinct;
- notification badge matches persistent data;
- notification read/archive semantics work;
- notification persistence works;
- single-Back app exit restores Home input;
- app drawer gesture works immediately afterward.

---

# 10. PHASE H — SAFE BUILD AND S10+ DEPLOYMENT

Only deploy after local build and tests pass.

Before deployment:

1. Verify target identity.
2. Verify current running Nuxel version/build.
3. Back up the relevant existing UI assets, configuration and services.
4. Build the correct ARM64 S10+ target.
5. Verify package manifests and changed files.
6. Deploy through the existing supported update mechanism.
7. Restart only the services that genuinely need restarting.
8. Avoid restarting critical services unnecessarily while the device is in use.
9. Do not flash boot, recovery, kernel or firmware.
10. Verify the system returns to a working Home screen.

If deployment fails, restore the previous known-good configuration and package.

Do not leave the phone with a broken launcher or unusable navigation.

## 10.1 Physical verification

On the actual S10+:

- inspect launcher icons;
- verify GTK and Flatpak icons;
- verify native Nuxel icons;
- test all three sound modes;
- generate a real notification;
- open expanded Quick Settings;
- swipe left to archive;
- swipe right to mark read;
- verify read notification remains;
- verify badge updates;
- restart the Home UI;
- restart the Bridge if safe;
- test persistence;
- exit applications using one Back press;
- immediately swipe to open the drawer;
- repeat across application types.

Do not mark a hardware test complete based only on a simulated UI test.

---

# 11. PHASE I — DOCUMENTATION AND FINAL REPORT

Update relevant documentation to reflect the real implemented architecture.

Document:

- application icon-origin rules;
- sound-mode icon state mapping;
- notification data model;
- notification persistence and retention;
- notification badge semantics;
- swipe action semantics;
- notification provider ownership;
- Back-to-Home lifecycle;
- overlay/input cleanup;
- diagnostic commands;
- known limitations.

Avoid duplicating documentation unnecessarily.

## Final report format

### 1. Mission summary

State whether each of the four requested features is complete.

### 2. Root causes

Explain the actual root cause of:

- duplicate GTK/Flatpak icons;
- block-shaped sound-mode icon;
- notification count without visible notifications;
- invisible input overlay after single Back.

Do not give hypothetical root causes as confirmed facts.

### 3. Implementation

List changed files and explain their responsibilities.

### 4. Notification architecture

Document the authoritative provider, data model, persistence, count semantics and gesture behavior.

### 5. Navigation architecture

Explain the fixed lifecycle and how Home regains input ownership.

### 6. Performance

Provide before/after measurements and calculated improvements where available.

### 7. Tests

List tests executed, pass/fail counts and blocked tests.

### 8. Physical-device verification

State precisely what was tested on the S10+.

### 9. Deployment identity

Report deployed build/version and commit SHA.

### 10. Remaining blockers

List anything incomplete, unverified or requiring future kernel/firmware/hardware work.

### 11. Rollback

Provide exact safe rollback steps.

---

# 12. DEFINITION OF DONE

<escape> </escape>
<escape> </escape>

<escape> </escape>

**PWNAGE-93000 is complete only when all of the following are true:**

- [ ] GTK applications display their original icons without Nuxel custom-style duplicates.
- [ ] Flatpak applications display their original icons without Nuxel custom-style duplicates.
- [ ] Native Nuxel applications retain their custom icons.
- [ ] Launcher registry does not contain duplicate application records caused by icon discovery.
- [ ] Icon rendering overhead is measured and unnecessary work is reduced.
- [ ] Normal sound mode displays a recognizable speaker.
- [ ] Vibrate displays the speaker, red forbidden line and vibration stripes.
- [ ] Silent displays the speaker, red forbidden line and red cross.
- [ ] All three states reflect the real backend state.
- [ ] The notification badge reflects actual persisted notification state.
- [ ] No phantom notification count remains.
- [ ] Real GTK and Flatpak notifications reach Nuxel where supported.
- [ ] Expanded Quick Settings lists notifications below all controls and statuses.
- [ ] Swipe left archives.
- [ ] Swipe right marks read.
- [ ] Read notifications remain visible as reminders.
- [ ] Notification state survives the relevant reloads and service restarts.
- [ ] Notification gestures do not break scrolling or Quick Settings gestures.
- [ ] A single Back press reliably returns to an interactive Home desktop.
- [ ] The app drawer opens immediately after returning from GTK applications.
- [ ] The app drawer opens immediately after returning from Flatpak applications.
- [ ] The app drawer opens immediately after returning from PWA applications.
- [ ] No invisible overlay or stale input grab blocks Home.
- [ ] Long-Back retains its intended behavior.
- [ ] Lock/unlock and Home/Tabs navigation remain functional.
- [ ] Regression tests pass.
- [ ] The actual S10+ deployment is verified, or deployment blockers are explicitly documented.
- [ ] Rollback instructions are available.

**Do not declare FULLY_DONE if any critical acceptance criterion remains unverified.**

The priority is a stable, responsive, predictable mobile Linux experience — not simply making the UI look correct.
