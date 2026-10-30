# FULL-PWNAGE-41000
# NUXEL — WIFI BOOT DEFAULT-ON & QUICK SETTINGS STATE REPAIR

## COMPLETE IMPLEMENTATION MISSION

**Mission:** PWNAGE-41000  
**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte  
**Operating system:** Nuxel, custom Fedora-based ARM64 Linux  
**Access:** Currently working Wi-Fi SSH  
**SSH identity:** `~wicked/.ssh/wicked_wqn_id_rsa`

---

# 0. MISSION OBJECTIVE

Fix one specific problem:

**Wi-Fi must be enabled by default after every normal boot, and the Nuxel Quick Settings Wi-Fi tile must accurately show that it is enabled.**

The current phone is reachable over Wi-Fi SSH, but the Quick Settings Wi-Fi tile still appears disabled after boot.

This suggests two separate problems that must both be addressed:

1. The persistent boot policy currently refuses to enable a disabled Wi-Fi radio.
2. The Quick Settings state initialization can incorrectly interpret a missing bridge status as Wi-Fi OFF.

This is a focused implementation mission.

Do not start changing unrelated Wi-Fi features.

Do not repair Bluetooth, audio, cellular, Wi-Fi scanning, browser connectivity, or unrelated Quick Settings tiles.

Do not rebuild the networking architecture.

The existing NetworkManager connection is working well enough to provide Wi-Fi SSH. Preserve that working connection.

---

# 1. CONFIRMED REPOSITORY FINDINGS

The following findings are from the supplied Nuxel repository archive dated 2026-10-30. Verify them against the current checkout and the live handset before modifying anything.

## 1.1 The boot helper deliberately refuses to enable Wi-Fi

Inspect:

`services/nuxel-s10/bin/nuxel-wifi-up.sh`

The current script begins with the policy:

> bring up an owner-chosen WLAN console without forcing the radio on by default.

It then reads:

`nmcli -t -f WIFI radio`

If the result is `disabled`, it logs:

`Wi-Fi radio disabled by owner; leaving it off`

and exits successfully.

This is a direct contradiction of the new owner requirement.

The new policy is:

**Wi-Fi must be enabled by default at every normal boot.**

The script must no longer preserve a disabled radio state from the previous session across reboot.

## 1.2 Existing tests enforce the wrong policy

Inspect:

`tests/pwnage37000/test_wifi_owner_controlled.py`

The tests currently assert:

- `rfkill unblock wifi` must not appear.
- `nmcli radio wifi on` must not appear.
- A disabled radio must be left OFF.
- The service description must contain `owner-controlled`.

These tests deliberately enforce the behaviour that is now unwanted.

Do not simply ignore or delete the tests.

Rewrite them to enforce the new desired policy.

The new tests must prove:

- Boot helper enables Wi-Fi.
- A soft rfkill block is cleared.
- NetworkManager confirms Wi-Fi ON.
- The helper does not create a competing network manager.
- The helper does not manually interrupt the active connection.
- Manual OFF remains possible after the boot helper has completed.
- Rebooting starts a new boot cycle and enables Wi-Fi again.

## 1.3 The installer retains old owner-controlled comments and behaviour

Inspect:

`services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh`

The `services()` function currently contains comments saying that the Wi-Fi service must not re-enable the radio.

It enables the `nuxel-wifi.service` unit and restarts it.

The `files_only()` function also installs:

`$STAGE/nuxel-s10/bin/nuxel-wifi-up.sh`

to:

`/usr/lib/nuxel/nuxel-wifi-up.sh`

The default stage root is:

`/usr/lib/nuxel/stage36000`

The installation path currently copies the staged helper without checking whether the deployed helper is newer.

This creates a second possible persistence problem:

**A corrected live helper can be overwritten by an old staged helper on the next boot.**

Update the actual source, stage/package copy, deployment path, tests, and comments consistently.

Do not fix only the live `/usr/lib/nuxel/nuxel-wifi-up.sh` file.

## 1.4 Quick Settings begins with a false Wi-Fi state

Inspect:

`pwa/nuxel-home/js/qs.js`

The constructor currently sets:

`wifi: false`

The `_init()` function calls `_syncState()` once.

`_syncState()` obtains phone status and runs logic equivalent to:

```javascript
const connectedState =
    net.wifi_state === 'connected' ||
    net.wifi_state === 'internet';

this.state.wifi =
    Boolean(net.wifi_enabled) ||
    Boolean(net.wifi_connected) ||
    connectedState;
```

This incorrectly treats missing status fields as false.

It also cannot distinguish:

- Actually disabled.
- Not yet initialized.
- Bridge unavailable.
- Status incomplete.
- Wi-Fi enabled but disconnected.

The initial state must be UNKNOWN, not OFF.

## 1.5 The bridge fallback can produce incomplete network data

Inspect:

`pwa/nuxel-home/js/bridge.js`

The `getPhoneStatus()` fallback returns an object with a network entry resembling:

```javascript
network: { connected: false }
```

There is no `wifi_enabled` property in this fallback.

`qs.js` sees that `status.network` exists and converts the missing Wi-Fi fields to false.

This is a plausible direct explanation for the false OFF indication when the radio is actually up.

Correct the handling.

Do not interpret incomplete status as an authoritative radio-off state.

## 1.6 The backend already exposes authoritative NetworkManager state

Inspect:

`services/nuxel-bridge/src/bridge.py`

The NetworkManager-backed `get_status()` reports:

- `wifi_enabled`
- `wifi_available`
- `wifi_connected`
- `wifi_state`
- `wifi_stage`
- `wifi_devices`

The backend obtains `WirelessEnabled` from NetworkManager.

The `set_wifi_enabled()` method writes the NetworkManager `WirelessEnabled` property and then reads it back.

Preserve this single backend ownership model.

Do not introduce a second Wi-Fi manager.

---

# 2. SCOPE BOUNDARIES

This mission is restricted to:

1. Boot-time Wi-Fi radio power policy.
2. Wi-Fi soft-rfkill state.
3. Boot service ordering and persistence.
4. Staged/deployed helper consistency.
5. Quick Settings Wi-Fi initialization.
6. Bridge status handling insofar as it directly affects the Wi-Fi tile.
7. Tests and evidence for the above.

Do not alter:

- Saved network credentials.
- WPA authentication.
- Wi-Fi scan implementation.
- AP selection logic.
- NetworkManager connection backend.
- DNS configuration.
- Browser.
- VPN.
- Cellular.
- Bluetooth.
- Audio.
- Other Quick Settings features.
- Unrelated status-bar styling.

A saved profile's autoconnect state is a separate concern from the Wi-Fi radio's power state.

Inspect it for evidence, but do not modify saved profiles unless the live diagnosis proves that it is necessary for the specific boot symptom.

Do not print profile secrets.

---

# 3. SSH ACCESS — PRESERVE THE CURRENT WORKING CONNECTION

The phone is currently reachable over Wi-Fi SSH.

Connect using:

`~wicked/.ssh/wicked_wqn_id_rsa`

Example:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa nuxel@PHONE_IP
```

Use the existing known phone IP and account.

Do not invent an IP address.

Do not expose the private key.

Do not disable host-key verification.

Do not change the SSH server configuration.

## 3.1 Identify the actual SSH transport

Before making changes, capture:

- `SSH_CLIENT` or `SSH_CONNECTION`.
- Client IP.
- Local phone address.
- `ip route get <SSH_CLIENT_IP>`.
- Interface used for the SSH reply path.
- Interface type.
- NetworkManager device state.
- RF-kill status.

This proves whether the current SSH connection is using WLAN or another transport.

Do not assume `wlan0` is the only or active interface.

The supplied repository has historical evidence of more than one NetworkManager Wi-Fi device, including `wlan0` and `wlan1`.

Inventory all real Wi-Fi devices.

## 3.2 Critical no-disconnect rule

During implementation:

- Never execute `nmcli radio wifi off`.
- Never execute `rfkill block wifi`.
- Never bring down the active Wi-Fi device.
- Never deactivate the active connection.
- Never restart NetworkManager merely to apply a small policy change.
- Never test a Wi-Fi OFF action over the only working Wi-Fi SSH path.

If a test would interrupt the only management connection, use an offline fixture or mock for that branch.

Keep the current SSH session working throughout deployment.

---

# 4. CREATE THE TODO AND BASELINE FIRST

Create:

`docs/beta-finalization/live/PWNAGE-41000-TODO.md`

Create:

`docs/beta-finalization/live/evidence/pwnage-41000/`

Before edits, record:

- Current git status.
- Current commit.
- Source helper hash.
- Deployed helper hash.
- Staged helper hash.
- Current service unit.
- Active/enabled state of `nuxel-wifi.service`.
- `systemctl cat nuxel-wifi.service`.
- `nmcli -t -f WIFI radio`.
- `nmcli -t -f RUNNING general`.
- `nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status`.
- `rfkill list`.
- `iw dev`.
- Current SSH route.
- Active connection status.
- Bridge-reported Wi-Fi status.
- Quick Settings source state.
- Any relevant boot journal messages.

Redact:

- SSIDs.
- BSSIDs.
- MAC addresses.
- Passwords.
- Other credentials.

Record the initial discrepancy:

- Does NetworkManager say Wi-Fi enabled?
- Does the active WLAN device show connected?
- Does the SSH route use WLAN?
- Does Quick Settings say OFF?
- Does the bridge status contain a valid `wifi_enabled` boolean?

Do not assume that the radio itself is OFF merely because the tile is OFF.

---

# 5. FIX THE BOOT POLICY — DEFAULT ENABLED

## 5.1 Desired policy

The new policy must be explicit:

**At each normal boot, Nuxel enables the Wi-Fi radio by default.**

During an active session, the user can still turn Wi-Fi OFF manually.

The behaviour is:

```text
NORMAL BOOT
    |
    v
NETWORKMANAGER READY
    |
    v
CLEAR WIFI SOFT BLOCK
    |
    v
SET NETWORKMANAGER WIFI RADIO ON
    |
    v
VERIFY RADIO ENABLED
    |
    v
ALLOW SAVED PROFILE AUTOCONNECT
    |
    v
NUXEL QUICK SETTINGS SHOWS ON
    |
    v
USER MAY MANUALLY TURN WIFI OFF
    |
    v
OFF REMAINS UNTIL NEXT NORMAL BOOT
    |
    v
NEXT NORMAL BOOT: WIFI ENABLED AGAIN
```

A hardware rfkill block or absent adapter must remain an honest hardware limitation.

Do not attempt to override a physical hardware kill switch.

## 5.2 Keep NetworkManager as the single owner

The existing NetworkManager instance is working.

Preserve it.

Do not:

- Launch another `wpa_supplicant`.
- Introduce iwd.
- Start a competing network service.
- Manually invoke driver-specific commands.
- Recreate the active network profile.
- Reconnect the current profile manually when NetworkManager is already handling autoconnect.

NetworkManager must remain responsible for:

- Radio power state.
- Device activation.
- Saved profile autoconnect.
- Association.
- DHCP.
- Connection state.

The boot helper's job is to ensure the radio is enabled, not to implement another connection manager.

## 5.3 Correct `nuxel-wifi-up.sh`

Modify:

`services/nuxel-s10/bin/nuxel-wifi-up.sh`

Remove the old rule that exits when `nmcli` reports Wi-Fi disabled.

The helper must:

1. Wait for NetworkManager D-Bus readiness using a bounded readiness check.
2. Inspect Wi-Fi rfkill state.
3. If a Wi-Fi soft block exists, clear only the software block for Wi-Fi.
4. Do not attempt to clear a hardware rfkill block.
5. Request `nmcli radio wifi on`.
6. Read back the result.
7. Verify that NetworkManager reports Wi-Fi enabled.
8. Inventory all NM-managed Wi-Fi devices.
9. Record whether they are available, connected, connecting, or unavailable.
10. Exit successfully only if the radio-enable operation is genuinely confirmed, or report a clearly classified hardware limitation.

The operation must be idempotent.

If Wi-Fi is already enabled, do not reset or cycle the radio.

Do not run `nmcli connection up` just because the radio has been enabled.

NetworkManager already autoconnects profiles with `connection.autoconnect=yes`.

The archive's prior A75 measurements show that manually activating a profile during cold boot can serialize behind an ongoing autoconnect and add approximately 25 seconds to multi-user startup.

Do not bring that delay back.

## 5.4 rfkill handling

Inspect the actual output of:

`rfkill list`

Distinguish:

- Soft blocked.
- Hard blocked.

Clear a Wi-Fi soft block where required.

Do not use `rfkill unblock all`.

Do not manipulate unrelated Bluetooth or other radio devices.

If hard-blocked:

- Report the hardware block.
- Do not claim that Wi-Fi is enabled.
- Do not repeatedly hammer the device.
- Do not bypass the hardware protection.

## 5.5 Bounded NetworkManager readiness

Do not assume that `After=NetworkManager.service` means that NetworkManager's D-Bus API is immediately ready.

Wait for:

- `nmcli -t -f RUNNING general` to report `running`.
- The radio property to be readable.
- The D-Bus operation to succeed.

Use a bounded retry policy.

Do not use a large arbitrary fixed sleep.

If readiness is not achieved, log the precise reason and return a meaningful failure.

A failed readback must never be logged as Wi-Fi ON.

## 5.6 Multiple WLAN interfaces

Historical live evidence contains both `wlan0` and `wlan1`.

Do not hardcode only `wlan0`.

Use NetworkManager's device inventory to identify all actual devices whose type is Wi-Fi.

The global NetworkManager `WirelessEnabled` property is the primary radio-power state.

Device availability and connection state are separate properties.

The helper must not fail merely because the expected interface has a different name.

---

# 6. MAKE THE BOOT SERVICE ORDERING AND EXECUTION RELIABLE

Inspect:

`services/nuxel-s10/systemd/nuxel-wifi.service`

The current unit is a oneshot service ordered after NetworkManager and wanted by `multi-user.target`.

Preserve this simple model unless live evidence justifies a small correction.

Requirements:

- Run after NetworkManager is started.
- Wait for its actual D-Bus readiness in the helper.
- Run once per boot.
- Do not run continuously.
- Do not create a radio toggle loop.
- Do not compete with NetworkManager.
- Do not block the entire boot indefinitely.
- Preserve meaningful journal output.

Ensure the service is enabled and its active unit file matches the repository.

## 6.1 Prevent repeated invocation from re-enabling Wi-Fi during a session

The user should be able to turn Wi-Fi OFF manually after boot.

Therefore boot activation must not run again and force Wi-Fi back ON later in the same session.

Inspect how `nuxel-apply-pwnage36000.sh` invokes the service.

The service can be restarted by the apply script.

If there is any possibility of repeated invocation within one boot, implement a boot-ID-aware guard or equivalent single-boot execution guarantee.

A suitable approach is to associate a successful execution marker in `/run` with:

`/proc/sys/kernel/random/boot_id`

Requirements:

- A new boot ID permits a fresh default-on operation.
- A repeated service invocation within the same boot does not overwrite the user's manual OFF choice.
- A failed readiness attempt does not falsely mark the boot as successfully initialized.
- A legitimate next boot runs the enable operation again.
- The marker contains no Wi-Fi secrets.

Choose the simplest robust implementation consistent with systemd's lifecycle.

---

# 7. FIX THE STAGING AND BOOT-DEPLOYMENT PATH

This is critical.

The source helper is installed to:

`/usr/lib/nuxel/nuxel-wifi-up.sh`

by:

`services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh`

The stage root defaults to:

`/usr/lib/nuxel/stage36000`

The staged source is:

`/usr/lib/nuxel/stage36000/nuxel-s10/bin/nuxel-wifi-up.sh`

The apply script currently installs this staged helper without a version comparison.

Therefore:

**Update the stage helper and the source repository together.**

Inspect the rootfs build pipeline and release packaging to make sure the corrected helper reaches newly built Nuxel images.

Verify all relevant copies:

- Repository source.
- Rootfs stage copy.
- Deployed `/usr/lib/nuxel/nuxel-wifi-up.sh`.
- Systemd unit source.
- Deployed systemd unit.

Do not fix the deployed file and leave the old staged file behind.

That would recreate the bug at the next boot.

## 7.1 Apply-script comments and service handling

Update stale comments in:

`services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh`

The script must no longer describe Wi-Fi as a radio that boot must leave disabled.

Keep radio manipulation inside the dedicated Wi-Fi helper, rather than scattering `nmcli radio wifi on` throughout the general apply script.

Ensure the apply script does not repeatedly invoke the helper during the active session.

If it currently restarts an already-completed `nuxel-wifi.service`, review whether a guarded start or another one-shot mechanism is more appropriate.

Do not cause a user's deliberate in-session OFF state to be reversed by a later unrelated apply operation.

---

# 8. FIX QUICK SETTINGS INITIALIZATION

Inspect:

`pwa/nuxel-home/js/qs.js`

This is a separate required part of the fix.

The actual radio may already be ON while the Quick Settings tile says OFF.

## 8.1 Replace false initial state with UNKNOWN

Currently:

`wifi: false`

Change the initial state to a representation of UNKNOWN/not-yet-loaded.

Do not render Wi-Fi OFF before an authoritative backend state has been received.

Use an explicit state model:

- `unknown`
- `enabled_disconnected`
- `connecting`
- `connected`
- `internet`
- `disabled`
- `unavailable`

The primary tile ON/OFF visual state must represent radio power, not internet connectivity.

## 8.2 Correct state interpretation

The authoritative field is:

`status.network.wifi_enabled`

When this exists and is a real boolean:

- `true` means the radio is ON.
- `false` means the radio is OFF.

This value must win over unrelated or stale UI state.

For older or partial bridge responses, only use a documented and reliable fallback:

- `wifi_state=connected` → radio ON.
- `wifi_state=internet` → radio ON.
- `wifi_state=connecting` → radio ON.
- `wifi_state=enabled_disconnected` → radio ON.
- `wifi_state=disabled` → radio OFF.

A value of `unavailable`, a missing state, or an unavailable bridge must not automatically be converted into OFF.

Do not confuse:

- Radio ON.
- Wi-Fi connected.
- Internet available.

These are three distinct conditions.

A Wi-Fi radio can be ON even when there is no network connection.

## 8.3 Correct `getPhoneStatus()` fallback handling

Inspect:

`pwa/nuxel-home/js/bridge.js`

The current fallback network object does not contain the Wi-Fi fields.

Do not make the frontend treat it as authoritative.

Either:

- Return an explicit unknown Wi-Fi state from the fallback, or
- Make `qs.js` reject incomplete status objects as authoritative.

Prefer both when consistent with the existing bridge contract.

An unavailable bridge must not overwrite a previously confirmed state with false.

## 8.4 Startup synchronization

The current `_init()` calls `_syncState()` once.

That is not reliable if Nuxel Home starts before the bridge or NetworkManager status path is ready.

Implement robust initialization.

Requirements:

1. Render Wi-Fi as UNKNOWN/CHECKING.
2. Request the actual phone status.
3. Validate that `wifi_enabled` is genuinely available.
4. Update the tile only after valid readback.
5. If the bridge is not ready, retry using bounded backoff.
6. Do not perform rapid infinite polling.
7. Do not run expensive polling continuously in the background.
8. Refresh when Quick Settings is opened.
9. Ensure a later valid response updates the tile.
10. Do not let an older asynchronous response overwrite a newer user action.

Use a single in-flight synchronization request where appropriate.

Prevent concurrent requests from producing stale UI results.

## 8.5 Unknown state presentation

If state is unknown:

- Use a neutral/checking appearance.
- Do not use the OFF styling.
- Do not falsely show the radio as enabled.
- Do not falsely show it as disabled.
- Expose an understandable status or accessibility label.
- Do not permit a click to blindly invert an unknown state.

When the user presses the tile while its state is unknown:

1. Fetch authoritative state.
2. Wait for a valid response.
3. Determine the actual requested action.
4. Apply it.
5. Verify backend readback.
6. Update the UI.

Never assume an unknown state means OFF.

## 8.6 UI state should use the radio property

The existing code combines `wifi_enabled`, `wifi_connected`, and `wifi_state` using Boolean OR.

Correct the semantics.

The Quick Settings tile should show ON when the radio is enabled even when disconnected.

The separate status-bar connection icon can continue communicating connection/internet state.

Do not make the quick-setting turn OFF merely because the internet is unavailable.

---

# 9. KEEP MANUAL WIFI ON/OFF FUNCTIONAL

Inspect the existing:

`_setWifiEnabled(enabled)`

method in `qs.js`.

Preserve the existing capability requirement:

`network:manage`

Preserve the existing backend operation:

`network / wifi-enabled`

Preserve the NetworkManager `WirelessEnabled` D-Bus implementation.

Requirements:

- Fetch current actual state before deciding what a toggle click means.
- Request the opposite state.
- Verify the backend's returned `wifi_enabled` boolean.
- Update the UI only after successful readback.
- Show an honest error when permission or backend access fails.
- Re-sync state after an error.
- Clear the pending visual state correctly.
- Prevent double clicks from issuing overlapping toggles.

Do not optimistically mark ON or OFF before NetworkManager confirms it.

Do not change Wi-Fi credentials.

Do not recreate profiles.

Do not introduce another supplicant.

## 9.1 Runtime manual OFF contract

After the boot helper has completed:

- The user can manually turn Wi-Fi OFF.
- The radio remains OFF for the rest of the session.
- No background unit or timer immediately turns it back ON.
- Quick Settings displays OFF based on actual NetworkManager readback.

At the next normal boot:

- The boot helper enables Wi-Fi again.

This is the exact new user policy.

---

# 10. UPDATE THE OLD PWNAGE-37000 TESTS

Inspect:

`tests/pwnage37000/test_wifi_owner_controlled.py`

Replace the old assumptions.

The old tests assert that the helper must not enable Wi-Fi.

Those are now regression tests for the wrong requirement.

Create focused tests for the new contract.

## 10.1 Boot helper tests

Test:

- NetworkManager running and radio already ON.
- NetworkManager running and radio OFF.
- Wi-Fi soft-blocked.
- Wi-Fi hard-blocked.
- NetworkManager initially unavailable.
- NetworkManager becomes ready within the bounded wait.
- NetworkManager never becomes ready.
- No Wi-Fi device currently enumerated.
- One WLAN device.
- Multiple WLAN devices.
- Radio ON succeeds and readback confirms it.
- Radio ON command fails.
- Readback disagrees with the command.
- Repeated helper invocation within one boot.
- A new boot ID permits a new enable attempt.

Use a fake `nmcli`, fake `rfkill`, and filesystem fixtures where suitable.

Do not require a physical Wi-Fi OFF operation during the live SSH session.

## 10.2 Installer/staging tests

Test that:

- The staged helper contains the new default-on policy.
- The deployed helper matches the staged intended version.
- The apply script no longer claims Wi-Fi is never enabled at boot.
- The general apply script does not introduce a competing radio controller.
- The boot service is enabled.
- The helper is executed once per boot.

## 10.3 Quick Settings tests

Test:

- Initial Wi-Fi state is UNKNOWN, not false.
- Authoritative `wifi_enabled=true` renders ON.
- Authoritative `wifi_enabled=false` renders OFF.
- `enabled_disconnected` renders ON.
- `connecting` renders ON.
- `connected` renders ON.
- `internet` renders ON.
- Missing `wifi_enabled` remains UNKNOWN.
- Bridge fallback does not render OFF.
- Bridge temporarily unavailable does not render OFF.
- A delayed valid status changes UNKNOWN to ON.
- A later OFF state changes ON to OFF.
- An old asynchronous response cannot overwrite a new user toggle.
- Permission denial does not claim the operation succeeded.
- Backend readback mismatch is surfaced.
- A fresh panel open refreshes the state.

## 10.4 Existing tests

Run the relevant test suites.

Do not hide failures by weakening unrelated tests.

Do not delete the former policy test simply to make the test suite green.

Replace its expectations with the new explicit default-on boot policy.

---

# 11. LIVE DEPLOYMENT WITHOUT DROPPING WIFI SSH

The current device is reachable through WLAN.

Keep that path intact.

## 11.1 Deployment order

1. Update the source helper.
2. Update the staged helper.
3. Update service metadata/comments.
4. Update the Quick Settings frontend.
5. Update bridge fallback handling where needed.
6. Update the automated tests.
7. Run the focused offline tests.
8. Review all changed files.
9. Back up the deployed helper, unit, and frontend assets.
10. Deploy the minimal corrected files.
11. Run `systemctl daemon-reload`.
12. Do not restart NetworkManager.
13. Do not cycle the wireless interface.
14. Verify the current Wi-Fi SSH connection remains alive.
15. Verify the live radio and Quick Settings state.

## 11.2 Test the live helper safely

If the current radio is already ON:

- Running the helper must be idempotent.
- It must not disconnect or cycle the connection.
- It must confirm that Wi-Fi is already enabled.
- It must leave the live connection intact.

If the current radio is not ON but SSH is genuinely routed over the same WLAN, treat that as an inconsistent state and investigate before making a disruptive change.

Do not use the live SSH session to test a command that turns Wi-Fi OFF.

---

# 12. REBOOT AND POST-BOOT VERIFICATION

A boot-policy change must be verified after a fresh boot.

Before reboot:

1. Verify that the current WLAN SSH route is understood.
2. Verify that a saved usable connection is available.
3. Verify its autoconnect setting without exposing its credentials.
4. Verify the new boot helper is staged correctly.
5. Verify the `nuxel-wifi.service` unit is enabled.
6. Verify Quick Settings and bridge code have been deployed.
7. Verify rollback files exist.
8. Save all evidence.
9. Notify the owner that SSH will disconnect during the planned reboot.

Do not deliberately disable Wi-Fi before reboot while relying on the same Wi-Fi SSH connection for recovery.

The offline tests must cover the previously-disabled radio branch.

Then perform one normal reboot as the acceptance test.

After reboot:

- Reconnect to the existing phone address over Wi-Fi SSH using the specified key.
- Confirm the current boot ID changed.
- Confirm NetworkManager is running.
- Confirm `nmcli radio wifi` reads enabled.
- Confirm the Wi-Fi radio is not soft-blocked.
- Confirm no hardware block is being hidden.
- Confirm the active Wi-Fi device state.
- Confirm saved-profile autoconnect if a network is available.
- Confirm the SSH route is again over WLAN.
- Confirm the deployed helper is the corrected version.
- Confirm the service completed successfully.
- Confirm no repeated enable loop exists.
- Inspect the new boot journal.

## 12.1 Physical Quick Settings verification

The owner must be able to unlock Nuxel and open Quick Settings.

Verify:

- The Wi-Fi tile is visibly ON.
- It does not initially appear OFF.
- Its state remains correct after the bridge becomes ready.
- It remains ON even if there is temporarily no internet.
- A genuine radio OFF state is still represented as OFF.

If the UI requires a cache refresh or service worker update, deploy the proper versioned asset/cache invalidation mechanism.

Do not require manually clearing browser data after every deployment.

---

# 13. FINAL ACCEPTANCE MATRIX

Use PASS / FAIL / BLOCKED / NOT TESTED.

| ID | Requirement | PASS evidence |
|---|---|---|
| SSH-01 | Existing Wi-Fi SSH preserved during deployment | Same WLAN management path remains active |
| WIFI-01 | Boot helper default-on policy | Source and test prove radio enable request |
| WIFI-02 | rfkill soft block | Soft block cleared where applicable |
| WIFI-03 | Hardware block handling | Hard block reported honestly |
| WIFI-04 | NetworkManager radio readback | `WirelessEnabled=true` |
| WIFI-05 | WLAN device discovery | All actual Wi-Fi devices enumerated |
| WIFI-06 | Saved network autoconnect | Existing profile reconnects when available |
| SERVICE-01 | Wi-Fi service enabled | `systemctl is-enabled` confirms |
| SERVICE-02 | Service readiness | NetworkManager-ready check succeeds |
| SERVICE-03 | One-time execution | No repeated radio override during session |
| STAGE-01 | Source/stage parity | Correct script in rootfs stage |
| STAGE-02 | Deployed parity | Deployed script matches intended source |
| TEST-01 | Old owner-controlled tests corrected | New tests enforce boot ON |
| QS-01 | Initial UI state | UNKNOWN rather than false OFF |
| QS-02 | Valid radio ON state | Tile ON |
| QS-03 | Valid radio OFF state | Tile OFF |
| QS-04 | Missing bridge state | Does not falsely show OFF |
| QS-05 | Delayed bridge availability | State updates when available |
| QS-06 | Toggle correctness | Backend readback controls UI |
| QS-07 | No stale async overwrite | Latest state wins |
| BOOT-01 | Actual reboot completed | New boot ID |
| BOOT-02 | Wi-Fi enabled after reboot | NetworkManager confirms |
| BOOT-03 | Wi-Fi SSH after reboot | Successful reconnect |
| BOOT-04 | Quick Settings after reboot | Owner confirms ON visually |
| SAFE-01 | Current connection preserved | No accidental radio OFF or interface down |
| SAFE-02 | Runtime manual OFF remains possible | Automated backend/UI test and safe owner verification |

A successful software build is not proof of a successful boot.

A successful SSH connection is not proof that the Quick Settings UI is correct.

A green Quick Settings tile is not proof that NetworkManager has actually enabled Wi-Fi.

The three evidence layers must agree.

---

# 14. DOCUMENTATION AND EVIDENCE

Store evidence in:

`docs/beta-finalization/live/evidence/pwnage-41000/`

Create:

`docs/beta-finalization/live/PWNAGE-41000-TODO.md`

Create:

`docs/beta-finalization/live/PWNAGE-41000-REPORT.md`

Include:

- Initial SSH route proof.
- Initial NetworkManager radio state.
- Initial rfkill state.
- Initial Quick Settings state.
- Source/deployed/staged helper comparison.
- Unit file and enablement.
- Relevant boot journal entries.
- New helper logs.
- New test results.
- Frontend state tests.
- Bridge fallback tests.
- Post-deployment radio readback.
- Post-reboot NetworkManager status.
- Post-reboot Wi-Fi SSH reconnection.
- Owner's Quick Settings confirmation.
- Rollback instructions.

Redact credentials, SSIDs, BSSIDs and MAC addresses from evidence.

---

# 15. FINAL REPORT FORMAT

Report:

## Root cause

Explain that PWNAGE-37000 deliberately introduced a boot policy that leaves Wi-Fi disabled.

Explain the separate Quick Settings bug where incomplete bridge status becomes false OFF.

## Boot helper

Describe the new radio enable sequence and actual readbacks.

## NetworkManager

Report the live radio state and the real Wi-Fi device(s).

## Quick Settings

Explain initial state, bridge fallback, delayed startup synchronization, and visual state after reboot.

## Stage and deployment parity

List repository, staged and deployed files, including their hashes.

## Tests

Report the rewritten boot-policy tests and frontend tests.

## Reboot

Report the new boot ID, Wi-Fi radio state, saved network connection and SSH reconnection.

## Owner confirmation

State whether the physical Quick Settings tile was visibly ON after reboot.

## Remaining issues

List any genuine hardware or boot blockers.

## Rollback

Provide exact rollback commands and backup paths.

---

# FINAL NON-NEGOTIABLE RULES

1. Wi-Fi must default to ON after every normal boot.
2. Manual OFF must still work during the current session.
3. NetworkManager remains the only network/radio manager.
4. Soft rfkill may be cleared; hard rfkill must be respected.
5. Do not restart NetworkManager unnecessarily.
6. Do not interrupt the current WLAN SSH session.
7. Do not hardcode only `wlan0`.
8. Update the staged helper, not just the repository copy.
9. Replace the old PWNAGE-37000 tests that enforce the unwanted OFF-preserving policy.
10. UNKNOWN bridge state must never be silently interpreted as OFF.
11. Quick Settings must reflect the actual NetworkManager radio property.
12. Perform one controlled reboot and verify both SSH and the physical UI afterward.
13. Do not touch unrelated Nuxel features.

**PWNAGE-41000: THE WIFI SWITCH MUST START ON. EVERY BOOT. NO MORE FALSE OFF.** 🐧📶
