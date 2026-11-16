# Nuxel S10+ Fingerprint Pwnage Pack

This pack is an engineering handoff for the Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820 QBT2000 ultrasonic fingerprint path.

## Contents

- `full-pwnage-finger.md` — complete implementation, secure architecture, permission-manager, deployment, physical-test and one-reflash specification.
- `pwnage-finger.md` — short kickstarter for the Nuxel agent.
- `scripts/acquire-s10plus-fingerprint-evidence.sh` — read-only ADB evidence/acquisition helper.
- `reference/` — snapshots of the relevant uploaded-repository report, reflash plan, current provider/security code, permission registry/manager UI, API authorization excerpt, device-node policy, diagnostics, tests and TEEGris boot-log excerpts.
- `SHA256SUMS` — hashes of all pack files, generated after assembly.

## Repository verdict from the uploaded ZIP

The QBT2000 sensor/driver is already visible in the recorded device evidence. The live capture shows `/dev/qbt2000_fd` and `/dev/qbt2000_ipc` as `root:root` mode `0600`, and `/sys/class/fingerprint/fingerprint` reports `QBT2000`. The current bridge provider correctly refuses enrollment/authentication because no verified secure provider is present.

The repo does **not** contain a verified QBT2000 fingerprint TA, trusted provider or product signing material. This pack does not fabricate or include proprietary firmware. No TA, TEE container, secure image or calibration firmware has been built here.

A TEEGris boot log does exist. It identifies Samsung Secure OS 3.1.0.0 on Exynos 9820. One boot sequence reports an incorrect hash for `bin/libtzld.so` and fails to unpack `startup.tzar`; a separate log segment reports a different container size and later loader completion. The agent must reconcile those separate boot attempts against the current device instead of assuming that TEE is simply absent or healthy.

The target is **Exynos 9820 / TEEGris 3.1**, not the Qualcomm S10+ / QSEE path. Samsung's public developer overview describes TEEGris as a TrustZone environment with Trusted Storage and APIs, but it does not provide this phone's proprietary QBT2000 TA or production signing authority.

## How to use

1. Extract the ZIP into the Nuxel repository root.
2. Read `full-pwnage-finger.md`.
3. Start the agent with `pwnage-finger.md`.
4. When the exact S10+ is attached through an already-authorized ADB/TWRP session and its identity is verified, run:

   ```sh
   bash scripts/acquire-s10plus-fingerprint-evidence.sh
   ```

5. Review the generated host-side directory. The helper is read-only on the phone. It never mounts or writes partitions, never reboots/flashes, never reads the QBT device-node contents, and never accesses `/data`, `/efs`, `/persist`, RPMB, secure storage or biometric enrollment data.

The script copies only matching, ordinary files found in whitelisted normal `/vendor`, `/system`, or `/odm` trees. A missing/mounted-path issue is reported rather than auto-mounted. The resulting files may be proprietary; keep them private and use only with lawful authorization.

## Important limits

- The pack is not a TEE/TA firmware download.
- It does not implement a fingerprint matcher.
- A userland `fprintd` process or visible UI is not proof of QBT2000 support.
- Do not expose `/dev/qbt2000_*` to applications.
- Do not bypass Samsung TEEGris signature/hash checks.
- Do not perform a standalone reflash. Prepare secure/vendor payloads for the single controlled combined batch, and require explicit operator review.

## Key code issues already identified

1. `fingerprint_provider.py` deliberately forces `secure = bool(devs) and False` and refuses enroll/delete/test. Do not merely remove this guard.
2. Fingerprint mode saves `fallback_pin_salt`/`fallback_pin_verifier`, but `SecurityProvider.unlock()` currently calls `_verify_locked()`, which only checks `salt`/`verifier`. Add mode-aware fallback verification before fingerprint can be enabled.
3. The API's privileged-provider `_owner_ok` mutation check includes NFC and Security but currently omits fingerprint/biometrics verbs. Add verb-specific Settings/OS authorization and caller identity validation.
4. The canonical permission registry and Permission Manager UI contain no biometric capability mapping yet. Implement a default-deny, app-scoped `biometric:authenticate` permission and a separate system-only `biometric:manage` authority; no ordinary app receives device-node access or enrollment authority.

No phone changes or live deployment were performed when creating this pack.
