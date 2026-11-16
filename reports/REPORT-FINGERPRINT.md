# Fingerprint completion report — Galaxy S10+ (`beyond2lte`)

## 1. Executive verdict

`BLOCKED_SECURE_PROVIDER`. The qbt2000 ultrasonic sensor and kernel driver are present (`/dev/qbt2000_fd`, `/dev/qbt2000_ipc`, `/sys/class/fingerprint/fingerprint`), but there is no verified TEE-backed enrollment/authentication provider. The bridge correctly refuses enrollment and keeps PIN/password fallback. A detected device node is **not** an authenticated biometric provider.

## 2. Target identity

- SM-G975F `beyond2lte`, Exynos 9820.
- Sensor: Samsung/QCOM qbt2000 under-display ultrasonic fingerprint sensor (live sysfs `name=QBT2000`, `vendor=QCOM`, `type_check=7`).
- Transport: two character devices `/dev/qbt2000_fd` (`237:0`) and `/dev/qbt2000_ipc` (`237:1`); sysfs class `/sys/class/fingerprint/fingerprint`.
- Confidence: **high** for sensor/driver presence; **unproven** for the exact secure-world TA/firmware revision.

## 3. What already exists

| Area | Source/path |
|---|---|
| Provider | `services/nuxel-bridge/src/fingerprint_provider.py` |
| Policy | `configs/nuxel/security/biometric-unlock.json` (disabled by default) |
| Bridge/UI | fingerprint status in Settings/Quick Settings; lockscreen PIN fallback |
| Detection | `/dev/qbt2000_*`, `/sys/class/fingerprint`, kernel qbt2000 driver |
| Tests | `tests/pwnage52000`, `tests/pwnage65000` security tests |

## 4. Latest evidence

| Check | Result | Tier |
|---|---|---|
| Device nodes | `/dev/qbt2000_fd`, `/dev/qbt2000_ipc` present | `PASS_DEVICE_RUNTIME` |
| Sysfs identity | `name=QBT2000`, `vendor=QCOM`, `type_check=7`, `position=13.77,0.00,...`, `bfs_values="FP_SPICLK":"25000000"` | `PASS_DEVICE_RUNTIME` |
| Kernel log | `fps_qbt2000_work_func_debug: ldo:0,ipc:0,wuhb:0,tz:1,type:qbt2000,int:0,0` every ~11 s | `PASS_DEVICE_RUNTIME` |
| Bridge status | `state=BLOCKED_SECURE_PROVIDER`, `sensor.detected=true`, `provider.secure_tee=false` | `PASS_DEVICE_RUNTIME` |
| fprintd/libfprint | absent / not a qbt2000 provider | `PASS_DEVICE_RUNTIME` |
| Enrollment/delete/test | refused fail-closed | `PASS_DEVICE_RUNTIME` |
| PIN fallback | required, credential set | `PASS_DEVICE_RUNTIME` |

## 5. Full dependency chain

| Stage | Current state |
|---|---|
| qbt2000 sensor + SPI/power/IRQ | driver bound; `tz:1` in work log |
| Kernel qbt2000 driver | device nodes + sysfs present |
| Secure-world/TEE boundary | **not established**; no verified TA/provider |
| Trusted application/firmware | unknown/missing |
| Enrollment/authentication service | not implemented |
| OS biometric API / pam/system service | not available (no supported fprintd backend) |
| Lockscreen authorization | PIN fallback only |

## 6. First failing stage

**Secure provider / TEE.** The driver exposes nodes and a periodic work log, but there is no verified trusted application or secure provider that can enroll, store, and compare templates inside the secure world. The bridge's `secure = bool(devs) and False` is the correct fail-closed boundary.

## 7. Why prior attempts have not completed the feature

- `fingerprint_provider.py` deliberately refuses enrollment because no verified TEE-backed provider exists.
- `fprintd`/`libfprint` presence alone does not imply qbt2000 support; the live image does not have a qbt2000 backend.
- A sysfs/driver node was never treated as authentication success.

## 8. Best recommended architecture

**Primary:** a vendor-authorized secure path:
`sensor → qbt2000 kernel driver → TEE/secure world → Samsung trusted application/firmware → enrollment/authentication service → Nuxel biometric API → lockscreen authorization`.

The service must store templates only inside the secure provider, enforce anti-spoof/rate-limit/lockout, and keep PIN fallback. The public userspace may receive only match/no-match and slot metadata, never raw images or templates.

**Fallback:** none that preserves security. A userspace-only matcher or a fake `fprintd` backend would be rejected.

## 9. Required work inventory

| Area | Work |
|---|---|
| Kernel/DT | confirm SPI/power/IRQ/LPM gating and qbt2000 driver ABI |
| TEE/TA | lawful vendor trusted application/firmware, secure storage, anti-spoof |
| Provider | enrollment/auth/deletion service with secure channel |
| OS integration | PAM/system service, lockscreen challenge, rate limit/lockout |
| Recovery | PIN fallback, template deletion/revocation |
| Tests | real enrollment, repeated genuine auth, spoof rejection, deletion |

## 10. Source/upstream research

- No upstream mainline qbt2000 secure provider for this Samsung sensor.
- The vendor TA/firmware and secure-world dependencies are not in the repo.
- `fprintd`/`libfprint` have no demonstrated qbt2000 support here.

## 11. Buildability

- The bridge/provider integration is buildable from repo sources.
- Secure enrollment requires vendor/OEM TEE material and keys; this is not obtainable from public sources alone.
- No TEE/firmware writes are authorized in this mission.

## 12. Risks and constraints

- Never export/copy biometric templates or raw images.
- Never bypass secure boot/TEE/anti-spoof.
- Never disable PIN fallback or make biometric disable ineffective.
- Do not confuse charger/LPM mode with normal interactive mode.

## 13. Phased roadmap

| Phase | Goal | Gate |
|---|---|---|
| 0 | Prove sensor/SPI power and secure-world channel existence | Read-only evidence |
| 1 | Obtain/lawfully integrate the vendor TA/provider | Security review |
| 2 | Secure enrollment + template storage | Real enrollment |
| 3 | Authentication challenge/response | Repeated genuine auth |
| 4 | Lockscreen integration + rate limit/lockout | PIN fallback regression |
| 5 | Deletion/revocation and anti-spoof hardening | Owner acceptance |

## 14. Acceptance test matrix

| Test | Required evidence |
|---|---|
| Enrollment | real finger enrolled through secure provider |
| Authentication | repeated genuine match; no raw template leaves TEE |
| Rejection | non-enrolled finger rejected; spoof attempt rejected |
| Lockout | retry/rate-limit policy enforced |
| Deletion | template removed; revoked immediately |
| Fallback | PIN/password still works |
| Reboot | enrollment persists securely |

## 15. Owner inputs required

- Lawful access to the vendor qbt2000 TEE/TA/firmware for this exact device, or an OEM-supported provider.
- Physical enrollment/authentication test.
- Security review/authorization for any TEE integration.

## 16. Confidence and gaps

- **Proved:** sensor/driver/nodes present, no secure provider, enrollment refused, PIN fallback preserved.
- **Inferred:** the blocker is the missing TEE/trusted application, not the kernel driver.
- **Unknown:** exact TA/firmware revision, anti-spoof behavior, secure storage interface, licensing.

## 17. Reflash impact (controlled maintenance)

| Question | Answer |
|---|---|
| Does completing fingerprint require a reflash? | **YES.** A vendor-authorised TEE trusted application/provider and secure storage must be part of the system/vendor image. |
| Boot/kernel too? | Likely yes if the secure provider/TEE handshake requires firmware or vendor partition changes; the qbt2000 kernel driver itself is present. |
| Can it be deployed over SSH now? | **NO.** A userspace-only matcher would be insecure and is explicitly rejected. |
| Batch with PWNAGE-93000? | **YES.** Combine with the camera/GPS/NFC/USBNET reflash batch; PWNAGE-93000's userspace changes can ride along without a separate flash. |
| Controlled batch | Vendor/TEE payload + system image; verify enrollment/authentication and PIN fallback on the inactive slot before switching. |
| Rollback | Keep the previous slot and PIN fallback; never remove the fallback during the experiment. |
| Risk if postponed | Fingerprint remains unavailable; PIN/swipe unlock continues to work. |
