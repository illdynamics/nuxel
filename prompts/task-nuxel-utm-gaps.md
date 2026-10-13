You are completing the remaining gaps in the Nuxel phone OS project so it matches the lead design document at `/workspace/Nuxel Linux Phone OS Design Notes.md` (if it exists) or the principles below.

## CURRENT STATE
The project has 168 files. Architecture is: immutable OS, GTK4/Phosh shell, 5-layer sandbox (namespaces+seccomp+Landlock+AppArmor+nftables), portal daemon, hardened allocator, PWA runtime, 4 native GTK4 apps, build/flash/sign tooling. All mustang-targeted.

## WHAT THE DESIGN DOC REQUIRES (NOT YET BUILT)

### 1. UTM VM Development Profile
Create `vm/` directory with everything needed to run Nuxel in a UTM VM on Apple Silicon (MacBook M1):

**`vm/utm-setup-guide.md`** — Complete step-by-step guide:
- Install UTM on MacBook M1
- Create ARM64 Linux VM with specific settings
- Guest: Fedora ARM64 or Debian ARM64
- Shell: Phosh on Wayland
- Phone-shaped resolutions: 390x844, 414x896, 720x1280 portrait
- RAM: 4-8GB, CPU: 4 cores, Disk: 40-80GB
- Networking: shared NAT
- Shared folders: disabled for security testing
- Clipboard sync: disabled for security testing

**`vm/nuxel-vm-bootstrap.sh`** — Script that:
- Creates UTM-compatible disk image
- Sets up Phosh session on Wayland
- Configures phone-shaped resolution
- Installs Nuxel core services (bridge, portal, notifications)
- Sets up hardened configs (AppArmor, nftables, hardened_malloc)
- Creates nuxel user
- Enables services

**`vm/phosh-phone-resolution.sh`** — Script to set phone-shaped display:
- 390x844 (compact phone)
- 414x896 (standard phone)  
- 720x1280 (HD phone portrait)
- Forces Wayland-only session
- Configures Phosh for mobile UX

### 2. App Permissions Management UI
Create `shell/nuxel-shell/nuxel-permissions/` — a GTK4/libadwaita app that shows and manages all app permissions:

**Files:**
- `main.c` — GTK4 application listing all installed apps with their permission states
- Shows per-app: app name, icon, list of granted/denied capabilities
- Allows: grant, deny, revoke permissions per app
- Shows risk level (low/medium/high) for each capability
- Shows last-used timestamp for each permission
- Allows "Revoke All" per app
- Integrates with nuxel-bridge D-Bus to query/update permission state
- Reads from `/var/lib/nuxel/permissions/*.json`
- Clean libadwaita mobile UI with AdwPreferencesPage

### 3. Additional Portal Types
Extend `services/nuxel-portal/src/portal.py` with these missing portal types:

- **Calendar portal** — `RequestCalendarAccess(app_id)` — shows dialog "Allow this app to access your calendar?"
- **Bluetooth portal** — `RequestBluetoothAccess(app_id)` — "Allow this app to use Bluetooth?"
- **USB portal** — `RequestUsbAccess(app_id)` — "Allow this app to access USB devices?"
- **Clipboard portal** — `RequestClipboardAccess(app_id, direction)` — "Allow this app to read/write the clipboard?"
- **Background portal** — `RequestBackgroundExecution(app_id)` — "Allow this app to run in the background?"

Add these portal types to the consent dialog system. Each should show a GTK4 dialog with [Deny] [Allow Once] [Allow Always].

### 4. PWA Uninstall with Full Data Wipe
Create `shell/nuxel-shell/nuxel-uninstall-helper.sh` — script that:
- Takes app_id as argument
- Removes Flatpak installation: `flatpak uninstall --delete-data <app-id>`
- Removes app data directory: `rm -rf /var/app/<app-id>/`
- Removes permission grants: `rm -f /var/lib/nuxel/permissions/<safe-id>.json`
- Removes .desktop entry and icon caches
- Removes cgroup if exists
- Removes nftables rules
- Logs uninstall action
- Returns 0 on success

### 5. App Distribution Model Document
Create `docs/app-store.md` — Documents the Nuxel app distribution philosophy:
- F-Droid principles + Flathub mechanics + Graphene paranoia
- Signed packages with permission manifests
- Source links and reproducible build metadata
- Update history and maintainer identity
- Vulnerability status tracking
- No account required for free apps
- Privacy-respecting paid app path (future)
- Permissions shown before install
- Permission diff shown on update
- Easy uninstall with data wipe

### 6. Milestone Tracking Document
Create `docs/milestones.md` — Tracks progress against the design document's milestone list:

**Milestone A: VM bootstrap** — UTM ARM64 VM with Phosh
**Milestone B: Shell and system app prototype** — Phosh + GTK4 settings + PWA launcher
**Milestone C: PWA runtime prototype** — Per-app isolated browser profiles + offline + permissions
**Milestone D: Native sandbox prototype** — Sandboxed GTK app with portals
**Milestone E: Update prototype** — Immutable base image + signed updates + rollback
**Milestone F: Pixel hardware research** — Mustang bootloader, kernel, device-tree status tracking

For each milestone, track: status (not started / in progress / done), what's been built, what remains.

### 7. Calendar PWA Portal Integration
Update `pwa/nuxel-apps/calendar/js/calendar.js` to:
- Request calendar portal permission on first launch
- Show permission status in calendar UI
- Handle permission denied gracefully (local-only mode)

### 8. VM Snapshot Helper
Create `vm/nuxel-vm-snapshot.sh` — script that:
- Creates UTM snapshot with name and description
- Lists existing snapshots
- Restores to a snapshot
- Deletes a snapshot
- Useful for testing updates and rollbacks safely

## RULES
1. All new code must be GTK4/libadwaita/Phosh compatible
2. Reference the design document's principles throughout
3. Keep mustang hardware references where relevant
4. VM scripts must work on macOS (UTM on Apple Silicon)
5. Portal extensions must maintain the existing GTK4 dialog pattern
6. Continue until all 8 items are created with real content
