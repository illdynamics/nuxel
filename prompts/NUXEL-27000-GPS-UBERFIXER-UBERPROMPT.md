# 🐧 PWNAGE 27000 — GPS UBERFIXER
## REAL GNSS • WORKING MAPS • OPENSTREETMAP TILES • LOCATION PROVIDER REPAIR

**Target device:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820  
**Operating system:** Nuxel, custom Fedora-based ARM64 Linux phone OS  
**Mission:** Diagnose and repair the complete location stack, from GNSS hardware and kernel support through the Nuxel location provider, bridge, Quick Settings and Maps application. Replace the coordinate-grid-only map with a properly configured, usable map while preserving genuine GPS state reporting.

---

## 0. MISSION RULES — READ FIRST

You are working on a real Linux phone port with valuable working functionality. Do not treat this as a UI-only task.

1. Inspect the repository, current branch, Git diff, architecture, existing services, location providers, Maps application, Quick Settings and Settings implementation before changing anything.
2. Check for active agents, deployment processes, serial-console ownership and existing transactions. If PWNAGE 25000 or another deployment is still active, perform read-only investigation until it is safe to modify or deploy.
3. Preserve the existing serial Live Console and recovery mechanism. Never allow two agents or processes to write to the physical serial transport concurrently.
4. Preserve working Wi-Fi, internet connectivity, DNS/TLS, browser, shell navigation, lockscreen, charging indicator and existing applications.
5. Do not flash a kernel, boot image, modem, firmware or partition. Do not wipe user data. Keep the existing Samsung-derived Linux 4.14 baseline.
6. Never fabricate GPS coordinates, satellite readings, provider availability or a successful fix.
7. Never confuse a manually entered coordinate, geocoding result, saved pin or last-known position with a fresh GNSS fix.
8. Do not hard-code Eindhoven or another location as a substitute for working GPS.
9. Use existing Nuxel architecture and dependencies wherever possible. Do not create a second competing location provider.
10. Distinguish repository tests, simulated tests, service-level tests and physical-device tests. Never claim that hardware was verified unless it was actually tested.
11. Make small, reviewable changes and document rollback instructions.

## 1. OBSERVED FAILURES

The physical-device screenshots show the following:

### GPS / Location

The Location Quick Setting has reported a “No fix” state. Determine whether this means:

- The GNSS hardware is not detected.
- The relevant kernel driver or firmware is missing.
- A location service/provider is missing or unavailable.
- The provider is running but cannot acquire satellites.
- The provider has a stale fix.
- The Quick Setting is reading the wrong state or a stale cache.
- The Nuxel bridge/API is not connected to the underlying provider.

Do not guess which explanation is correct. Gather evidence.

### Maps

The Maps screen displays:

`no tile source configured`

The application shows a coordinate grid and location pins instead of map tiles. It also shows an Eindhoven search result/pin.

The UI text indicates that tiles, when present, are OpenStreetMap-derived and currently limited to an offline cache. The application provides latitude/longitude fields, a Go action, an Add Pin action and a geocoding Search action.

Investigate and fix the real map-tile configuration, loading pipeline, network handling and attribution.

### Provider / bridge integration

Previous Nuxel work has encountered errors indicating that no service/provider supplies a Nuxel bridge operation. Verify whether the same architectural problem affects Location.

Do not fix a missing provider by merely changing an error message.

---

## 2. PHASE ZERO — REPOSITORY AND DEVICE AUDIT

Before editing:

- Record `git status --short`, the current branch and relevant diffs.
- Identify the Maps application entry point and its rendering technology.
- Find the source of the “no tile source configured” message.
- Find the code that renders the coordinate grid and pins.
- Identify the tile-source configuration schema and current defaults.
- Trace geocoding, pin storage, current-location state and location-provider requests.
- Trace the Location Quick Setting from UI action to provider/service and back.
- Identify the Nuxel bridge/API and any provider-registration or D-Bus errors.
- Inspect existing tests and available development/test commands.
- Check for active agents and deployments before any physical-device action.

Create a short findings table:

| Symptom | Evidence | Root cause | Proposed fix | Verification |
|---|---|---|---|---|
| GPS says No fix | Actual provider and logs | To establish | To establish | Real fix/state test |
| Maps has no tiles | Config and network trace | To establish | To establish | Actual tiles render |
| Location provider unavailable | Bridge/service logs | To establish | To establish | Real API response |
| Duplicate map pins | State/rendering path | To establish | To establish | Regression test |

Do not proceed on unsupported assumptions.

---

## 3. REAL GNSS HARDWARE AND DRIVER DIAGNOSIS

Investigate the actual GNSS path on the Galaxy S10+ running the current Nuxel kernel.

Use available, safe diagnostics. Adapt to the tools actually installed; do not assume every utility is present.

Inspect:

- Running kernel version and device configuration.
- Kernel logs for GNSS, GPS, UART, serial, firmware, regulator, clock, IIO and relevant driver probe errors.
- Available `/dev` device nodes and relevant `/sys` entries.
- Relevant device-tree configuration and driver bindings where available.
- Existing location services, daemons, D-Bus APIs and Nuxel provider code.
- Permissions, service dependencies and configuration.
- Whether GNSS requires a vendor-specific service or hardware initialization sequence.
- Whether the current Fedora-based userspace has the required service and permissions.

Do not indiscriminately read or write serial devices. The serial Live Console must remain protected. Do not send undocumented commands to suspected GNSS hardware.

Do not assume GNSS is a generic USB device or that the existence of a location UI proves the hardware is supported.

Determine which of the following is true:

1. Hardware is detected and the provider works.
2. Hardware is detected but the driver/service is missing or broken.
3. The provider works but no satellite fix is available.
4. The provider is inaccessible because of permissions or bridge integration.
5. Hardware support is missing from the current kernel/device configuration.
6. The available evidence is insufficient to distinguish the above.

Fix the actual root cause where it can be addressed safely in userspace. If kernel or board support is missing, document the precise limitation and propose a separate follow-up. Do not flash a new kernel in this task.

---

## 4. CANONICAL LOCATION PROVIDER

Establish one authoritative source for location state.

Trace the complete path:

`GNSS hardware → kernel/driver → location service/provider → Nuxel bridge/API → Quick Settings + Maps + Settings`

Repair missing provider registration, service activation, permissions, D-Bus calls, API mismatches or stale state at the correct layer.

The provider should expose, where supported:

- Provider availability.
- Enabled/disabled state.
- Acquisition/searching state.
- Fix validity.
- Last-fix timestamp.
- Latitude and longitude.
- Accuracy estimate.
- Satellite or signal information if genuinely available.
- Last error and diagnostics.
- Whether data is live or stale.

Do not invent satellite counts, accuracy, timestamps or provider names.

### Required state distinctions

Implement or preserve clear distinctions between:

- `UNAVAILABLE`: provider or required hardware path is unavailable.
- `DISABLED`: location is disabled by the supported control mechanism.
- `SEARCHING`: provider is actively trying to obtain a fix.
- `NO_FIX`: provider is running but has no valid current fix.
- `STALE`: a previous location exists but is no longer considered fresh.
- `FIXED`: a valid, fresh location fix is available.
- `ERROR`: the provider failed and has a meaningful error.

Use the project's existing naming conventions if equivalent states already exist. Avoid unnecessary duplicate state models.

The UI must not report `FIXED` merely because a coordinate exists.

Define freshness using actual provider timestamps and a documented policy. Do not refresh the timestamp simply because the UI polled the provider.

---

## 5. FIX THE LOCATION QUICK SETTING

Trace the Location tile from click handler through the actual system/provider operation.

Requirements:

- The tile must control the real supported location-enable/disable mechanism.
- The tile must display authoritative state, not a locally toggled boolean.
- The tile must distinguish disabled, unavailable, searching, no fix, stale and fresh fix.
- Pending operations must have bounded timeouts.
- Failures must produce actionable feedback and allow retry.
- Provider disappearance and service restart must update the tile.
- Avoid excessive polling and UI-thread blocking.
- If GNSS cannot be independently powered off through the current hardware stack, state that accurately instead of pretending the hardware was switched off.
- Do not expose coordinates in the Quick Setting unless the existing UI design calls for them and privacy rules allow it.

A geocoding search or manual pin addition must never turn the Location tile into a successful GPS fix.

---

## 6. REPAIR MAPS TILE-SOURCE CONFIGURATION

The Maps screen currently shows:

`no tile source configured`

Find the exact configuration and rendering path responsible.

Implement a real, configurable tile source using an appropriate OpenStreetMap tile endpoint or an existing supported tile provider.

### Requirements

1. Provide a valid default tile-source configuration appropriate for development and normal use.
2. Use the existing Maps rendering framework if possible.
3. Confirm the map renderer requests actual tiles and displays them at the correct coordinates and zoom levels.
4. Ensure pan and zoom update the visible map.
5. Support the existing map pin and coordinate-entry features.
6. Preserve offline-cache support where the current architecture provides it.
7. Handle network failure, HTTP errors, unavailable tiles and missing configuration gracefully.
8. Never leave the user staring at a blank grid without explaining what failed.
9. Do not treat a successful geocoding response as proof that tile loading works.
10. Do not treat a tile-cache hit as proof that online tile access works.
11. Keep requests bounded and avoid repeated requests for identical tiles where the renderer/cache can deduplicate them.
12. Do not bundle a huge offline map database or introduce an unrelated mapping framework without justification.

### OpenStreetMap attribution and usage

- Display visible, readable attribution to OpenStreetMap and its contributors whenever required by the selected data/tile source.
- Follow the selected tile provider's documented usage policy and request requirements.
- Do not scrape tiles or configure aggressive downloading/prefetching.
- Do not assume the public OpenStreetMap tile service is an unrestricted production CDN.
- Keep tile-source configuration separate from geocoding configuration.
- Use HTTPS where supported by the chosen endpoint.
- Respect caching headers and reasonable request behavior.
- If a different provider is used, display the attribution and follow its policy.
- Do not claim that an offline cache contains a map unless real cached tiles are available.

If the current renderer supports a tile URL template, configure it through the project's existing settings/schema rather than scattering URL strings through UI code.

Verify how zoom level and tile X/Y coordinates are generated. Ensure tile projection and latitude/longitude conversion are correct.

### Configuration and errors

Replace the generic “no tile source configured” message with accurate diagnostics:

- Configuration missing.
- Tile source invalid.
- Network unavailable.
- Tile request failed.
- Tile not cached while offline.
- Tiles loaded successfully.

Do not reveal secrets or tokens in user-facing errors or logs.

A missing source must be recoverable from Settings or a documented default configuration, not require the user to rebuild the whole OS.

---

## 7. FIX MAP POSITION, PINS AND SEARCH

The screenshot shows overlapping or duplicated Eindhoven labels/pins. Trace why.

Investigate:

- Whether every search result is inserted permanently as a pin.
- Whether duplicate results are appended after repeated searches.
- Whether the current-location marker is confused with a geocoding result.
- Whether pin state is duplicated between the app and bridge.
- Whether old asynchronous search results overwrite newer results.
- Whether the map viewport is updated independently of its stored center.
- Whether labels are being clipped by the map viewport or control overlay.

Implement predictable behavior:

- Search results should be distinguishable from saved pins and the current GPS location.
- Repeated identical searches should not produce uncontrolled duplicate pins.
- The user should be able to select a result and center the map on it.
- Adding a pin should use the coordinates currently selected on the map or explicitly entered.
- Manual coordinate navigation should work without claiming GPS is fixed.
- The live-location marker must only represent actual provider data.
- Do not destroy user-saved pins during cleanup.
- Keep pin labels readable and avoid clipping them at the edge of the map.
- Ensure map controls remain usable on the phone's narrow display.
- Prevent stale asynchronous results from corrupting the current map state.

Do not simply hide duplicate labels without fixing the underlying state/rendering behavior.

---

## 8. GEOCODING AND NETWORK BEHAVIOR

The Maps app indicates that search uses OpenStreetMap Nominatim, with one query per action.

Audit the actual geocoding implementation and keep it separate from tile loading and GNSS acquisition.

Requirements:

- Use the appropriate configured geocoding endpoint.
- Follow Nominatim's published usage policy.
- Use a meaningful application User-Agent or other required identification.
- Avoid automated request bursts and repeated identical queries.
- Use request timeouts and graceful error handling.
- Do not send a query on every keystroke if the current design only intends explicit Search actions.
- Keep network errors distinct from GPS/provider errors.
- Add a small, clear result state for empty results, unavailable network and service failure.
- Avoid logging precise coordinates unnecessarily.

A successful place search proves only that geocoding worked. It does not prove GNSS is working.

---

## 9. SETTINGS AND DIAGNOSTICS

If Nuxel already has a Settings application, integrate into its existing design rather than building a separate settings shell.

Add or improve a Location/GPS page showing:

- Provider and service name.
- Provider availability.
- Location enabled state where controllable.
- Current acquisition/fix state.
- Last genuine fix age.
- Accuracy and satellite information if actually available.
- Permissions/privacy controls.
- Last error and retry/refresh action.

Add a Maps configuration area or appropriate existing settings entry showing:

- Selected tile source.
- Tile-source status.
- Attribution.
- Cache status if available.
- Network/tile loading errors.
- A safe way to restore the default configuration.

Do not put sensitive location history into routine logs. Provide diagnostics useful enough to determine why a fix is unavailable without collecting unnecessary location data.

---

## 10. TEST PLAN

Add tests at the right levels.

### Unit tests

Cover:

- Missing location provider.
- Provider service stopped or unreachable.
- Provider errors.
- Disabled location.
- Searching with no fix.
- Fresh fix.
- Stale fix.
- Missing or invalid timestamp.
- Invalid coordinates.
- Search result not treated as a GNSS fix.
- Manual pin not treated as a GNSS fix.
- Missing tile-source configuration.
- Invalid tile URL/configuration.
- Tile request timeout and HTTP failure.
- Offline tile-cache hit and miss.
- Duplicate geocoding results.
- Repeated searches.
- Stale asynchronous results.
- Attribution visibility.
- Map viewport and pin updates.

Use mocks for unit tests, but do not mistake mock tests for hardware validation.

### Integration tests

Verify:

- Maps reads the canonical location provider.
- Quick Settings and Maps agree on provider availability and fix state.
- Provider restarts are handled.
- Tile-source configuration reaches the real map renderer.
- Actual tile requests can complete when a network is available.
- Geocoding failures do not corrupt GPS state.
- Repeated searches do not create uncontrolled duplicate pins.
- Existing saved pins remain intact.

### Physical-device tests

If the phone is accessible:

1. Verify the exact model and running kernel.
2. Capture safe diagnostics for the GNSS driver/provider.
3. Open Maps and confirm whether actual tiles render.
4. Confirm attribution is visible.
5. Search for a location and verify that the result is treated as a search result, not a live GPS fix.
6. Test the Location Quick Setting and verify the actual provider response.
7. Move outdoors with a reasonable sky view and allow an appropriate acquisition period.
8. Record whether a genuine fix was obtained, the elapsed time and the conditions.
9. Verify timestamp and accuracy are real provider values.
10. Check that stale/no-fix states are displayed honestly.
11. Verify existing Wi-Fi, browser, shell navigation, lockscreen and serial Live Console remain functional.

Do not claim physical-device success if the device could not be tested.

---

## 11. REGRESSION AND SAFETY REQUIREMENTS

Do not:

- Flash a kernel or firmware.
- Wipe data or change partitions.
- Replace the working Live Console.
- Disable working Wi-Fi or browser functionality.
- Fake a GPS fix to make Maps appear functional.
- Hard-code Eindhoven as the current location.
- Make the map depend on a successful GPS fix to render.
- Make GPS depend on successful geocoding.
- Add uncontrolled polling or tile-download loops.
- Expose diagnostic services publicly.
- Remove existing saved pins or unrelated data.
- Declare success based solely on a screenshot or a UI state.

Run the repository's relevant test suites and record the exact commands and results.

---

## 12. DELIVERABLES

At completion, report:

1. Root cause of the GPS “No fix” state.
2. Root cause of “no tile source configured.”
3. Root cause of any provider/bridge errors.
4. Explanation for duplicate pins or overlapping labels.
5. Files changed and why.
6. Tests run and actual pass/fail results.
7. Evidence of real tile requests and map rendering.
8. GNSS hardware/provider findings.
9. Whether a genuine GPS fix was obtained on the physical device.
10. Remaining kernel, driver, firmware or hardware limitations.
11. Rollback steps.
12. A concise operator test procedure.

Include a status table:

| Component | Code implemented | Automated tests | Physical-device test | Remaining issue |
|---|---|---|---|---|
| GNSS detection/provider | | | | |
| Location Quick Setting | | | | |
| Maps tile source | | | | |
| Map rendering/zoom | | | | |
| Search/geocoding | | | | |
| Pins/current-location marker | | | | |
| Attribution/cache/offline behavior | | | | |

## DEFINITION OF DONE

PWNAGE 27000 is complete only when:

- The actual cause of the location state is understood and addressed where safely possible.
- Maps has a valid tile source and renders real tiles when network access is available.
- OpenStreetMap attribution and provider usage requirements are respected.
- Search results, saved pins and genuine GPS fixes are distinct.
- Quick Settings reflects the real location provider state.
- Tests pass and physical tests are clearly identified as performed or pending.
- Existing Nuxel functionality and serial recovery remain intact.

**Start with Phase Zero. Audit first, preserve the known-good phone, fix the underlying causes, and prove each result. Never fake GPS or map functionality.**
