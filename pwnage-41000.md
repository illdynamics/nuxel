# PWNAGE-41000 — WIFI ALWAYS ON AT BOOT
## Fix the Boot Radio Policy & Quick Settings State

**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte  
**OS:** Nuxel  
**Connection:** Existing Wi-Fi SSH connection  
**SSH identity:** `~wicked/.ssh/wicked_wqn_id_rsa`

## THE ACTUAL ROOT CAUSE FOUND

The repository contains an explicit policy introduced by PWNAGE-37000 that prevents Wi-Fi from being enabled automatically at boot.

In particular:

- `services/nuxel-s10/bin/nuxel-wifi-up.sh` explicitly says it must not force the radio ON.
- If NetworkManager reports Wi-Fi disabled, the script exits and leaves it disabled.
- `tests/pwnage37000/test_wifi_owner_controlled.py` actively enforces this unwanted behaviour.
- `services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh` installs the staged Wi-Fi helper and retains comments saying boot must not re-enable Wi-Fi.

There is also a likely Quick Settings state bug:

- `pwa/nuxel-home/js/qs.js` initially sets `wifi: false`.
- It performs an initial one-shot status request.
- `pwa/nuxel-home/js/bridge.js` can return a fallback network object without any `wifi_enabled` field when the bridge is unavailable.
- `qs.js` treats that incomplete object as authoritative and converts the missing value into `false`.

This can make the Quick Settings tile show OFF even though the actual phone is already connected and accessible over Wi-Fi SSH.

## REQUIRED MISSION

Fix ONLY:

1. Wi-Fi radio defaults to ON after every normal boot.
2. NetworkManager correctly applies and verifies that state.
3. Quick Settings accurately displays the real radio state.
4. The user can still manually turn Wi-Fi OFF and ON during a session.

### Required execution order

1. Connect through the currently working Wi-Fi SSH connection.
2. Create a TODO checklist and capture the current connection/interface state.
3. Verify that the current SSH route is genuinely using WLAN.
4. Inspect the live NetworkManager radio state and current Quick Settings status.
5. Change the boot policy from owner-controlled OFF preservation to **default ON at boot**.
6. Update the staged boot helper and deployed helper so boot-time installation cannot restore the old policy.
7. Update the PWNAGE-37000 tests that enforce Wi-Fi remaining disabled.
8. Fix the Quick Settings initialization and bridge-state handling.
9. Deploy the minimal changes without disrupting the current SSH connection.
10. Reboot once, reconnect over Wi-Fi SSH, and prove that the radio and Quick Settings are ON.

## REQUIRED BEHAVIOUR

- Wi-Fi radio ON by default after every boot.
- Existing saved Wi-Fi profiles remain intact.
- NetworkManager remains the single radio and connection manager.
- Do not create a second wpa_supplicant.
- Do not manually reconnect an already connecting profile.
- Quick Settings must show ON when the radio is enabled, even without an internet connection.
- A missing or temporarily unavailable bridge response must show UNKNOWN/CHECKING, not falsely OFF.
- A genuine NetworkManager disabled state must show OFF.
- The Quick Settings button must still reliably turn Wi-Fi OFF and ON during the current session.
- Manual OFF must remain respected until the next normal boot, when the boot-default policy enables Wi-Fi again.

## IMPORTANT SAFETY

The phone is currently reachable over Wi-Fi SSH.

- Never run `nmcli radio wifi off` during this mission.
- Never run `rfkill block wifi`.
- Never restart NetworkManager unnecessarily.
- Never disconnect or deactivate the active Wi-Fi connection to test it.
- Do not modify Wi-Fi passwords or unrelated saved profiles.
- Do not modify firmware, kernel, bootloader, or partitions.
- Do not assume the primary interface is always `wlan0`; inspect actual devices.
- Do not expose Wi-Fi credentials in logs.

## DEFINITION OF DONE

After a normal reboot:

1. Wi-Fi is actually enabled in NetworkManager.
2. Any software rfkill block is cleared.
3. The saved network reconnects when available.
4. Wi-Fi SSH reconnects successfully.
5. Quick Settings shows the Wi-Fi tile ON.
6. Opening Quick Settings does not briefly or permanently show a false OFF state.
7. The UI distinguishes radio enabled from network connected.
8. Manually turning Wi-Fi off and back on still works.

**This mission is ONLY about Wi-Fi boot activation and truthful Quick Settings state. Do not touch anything else.** 🐧
