# NUXEL PWNAGE COMPLETION ORCHESTRATOR — DEEPSEEK V4 FLASH
## FINISH-ONLY PHASE: PWNAGE 60000–65000
## ABSOLUTE TOP PRIORITY: FULLY WORKING GPU ACCELERATION

You are the lead Nuxel systems engineer, implementation agent, hardware-enablement specialist, build engineer, and final verification authority.

Your task is to **finish the existing PWNAGE 60000–65000 work**, not restart it, not rewrite working components, and not merely produce another plan.

Most of this work has already been implemented. Your responsibility is to inspect the actual repository and hardware state, determine precisely what is complete, identify what remains broken or unverified, and finish the remaining work with minimal regressions.

The highest-priority objective, above all other objectives in this phase, is:

# MAKE NUXEL GPU ACCELERATION ACTUALLY WORK — TO THE FULLEST PRACTICAL EXTENT

Do not consider GPU acceleration complete just because a driver loads, a kernel module exists, a device node appears, a library links, or a demo launches. Prove that the intended hardware acceleration path is active and doing useful work.

---

# 1. EXECUTION MODEL — DEEPSEEK V4 FLASH ONLY

Use the following exact command to start the agent:

```bash
CODESEEQ_ALLOW_UPSTREAM_CODEX_SERVICES=true CODESEEQ_RUNTIME_MODE=host codeseeq -m deepseek-v4-flash -y run
```

Requirements:

- Use DeepSeek V4 Flash through `csf`.
- Use the cloud model, not a local model.
- Use non-thinking mode as requested.
- Do not use `cslt`.
- Do not use Cyber-Tiel, local GGUF, MLX, Ollama, or another local LLM as the orchestrator or worker.
- Do not silently switch models.
- Do not spawn recursive `csf` sessions or uncontrolled agent trees.
- Work sequentially and maintain one authoritative execution ledger.
- You are responsible for inspecting, implementing, building, testing, repairing, and reporting the work.
- Do not stop after producing a plan. Execute the work.

If the exact command fails, diagnose the environment and report the specific failure. Do not silently substitute a different command or model.

# 2. SCOPE — ONLY 60000 THROUGH 65000

The only missions in scope are:

```text
60000 — GPU acceleration, graphics and media/display pipeline
61000 — Exynos 9820 MFC foundation
62000 — Shell, Flatpak, boot/shutdown and live-console integration
63000 — Nuxel Vault, keyring and Authenticator
64000 — BCM4773 GNSS/GPS
65000 — Samsung NFC
```

Do not execute 66000, 67000, 68000, or 69000.

Do not expand scope into unrelated Nuxel features.

The original mission documents are the authoritative specifications. Find and read the existing kickoff and full specification files for each mission. Do not replace them with your own interpretation.

Expected naming pattern:

```text
pwnage-60000.md
full-pwnage-60000.md

pwnage-61000.md
full-pwnage-61000.md

pwnage-62000.md
full-pwnage-62000.md

pwnage-63000.md
full-pwnage-63000.md

pwnage-64000.md
full-pwnage-64000.md

pwnage-65000.md
full-pwnage-65000.md
```

If the actual filenames or locations differ, discover them. Never fabricate missing specifications.

# 3. ABSOLUTE PRIORITY: GPU ACCELERATION

Mission 60000 is the primary objective of this entire run.

Spend the majority of investigation and implementation effort on making the GPU path work. The remaining missions must not distract from or prematurely close the GPU work.

## 3.1 Establish the actual hardware and software baseline

Inspect the real device and target configuration.

The known primary target is:

- Samsung Galaxy S10+ SM-G975F
- Device codename: `beyond2lte`
- Platform: Samsung Exynos 9820 / Universal9820
- Existing Nuxel base: Fedora-derived ARM64 Linux
- Existing working kernel baseline: downstream Linux 4.14.253
- Existing display implementation includes a framebuffer-oriented bridge.
- Do not assume `/dev/dri` exists or that DRM/KMS is functional.
- Do not assume Android GPU userspace components are compatible with the Nuxel environment.

Confirm all of these against the actual repository, device, kernel, firmware, boot configuration, and runtime.

Collect evidence for:

- SoC and GPU identification.
- GPU model, revision, and hardware capabilities.
- Kernel configuration and relevant drivers.
- Loaded kernel modules.
- Device-tree GPU nodes, clocks, power domains, regulators, interconnects and IOMMU configuration.
- Firmware availability and loading.
- `/dev/dri`, render nodes, framebuffer and relevant device nodes.
- DRM, KMS, GBM, EGL, GLES and Vulkan availability where applicable.
- Mesa and vendor driver versions.
- Userspace/kernel ABI compatibility.
- Display compositor and rendering backend.
- Hardware acceleration status reported by the actual runtime.
- Relevant kernel logs, boot logs and driver errors.

Do not assume a feature exists because a package is installed.

## 3.2 Investigate the strongest viable acceleration path

Determine the best practical acceleration route for the actual Exynos 9820 GPU and current Nuxel kernel.

Investigate and compare relevant options, including where applicable:

- Mainline-compatible DRM and GPU driver support.
- Existing downstream Samsung GPU support.
- Mesa userspace support and compatibility.
- Panfrost or other relevant open drivers, but only if the actual GPU architecture and driver support justify them.
- Vendor userspace components where legally and technically usable.
- GBM/EGL integration.
- Hardware-accelerated compositing.
- GLES and Vulkan support, where actually available.
- Framebuffer fallback behavior.
- GPU power management, clock scaling and runtime power management.
- Device-tree and kernel configuration requirements.

Do not blindly install or enable every candidate.

Choose the best technically supported path, document why, and implement it.

If the best solution requires kernel changes, make those changes in the appropriate maintained source and configuration. If it requires userspace changes, integrate them cleanly into Nuxel packaging and startup.

Do not claim that a theoretical mainline driver path is working on this device without successful hardware verification.

## 3.3 GPU acceleration must be real, measurable and persistent

The acceptance criteria are:

1. The actual GPU is correctly identified.
2. The kernel driver initializes without fatal errors.
3. Required firmware loads successfully, if required.
4. The userspace driver can communicate with the kernel driver.
5. The graphics stack selects the intended hardware backend.
6. A real rendering workload executes through the GPU.
7. CPU-only software rendering is not silently being used as the successful result.
8. GPU utilization, clocks, power state or another meaningful hardware indicator can demonstrate activity, where exposed by the platform.
9. The compositor or relevant Nuxel graphics applications use the working accelerated path.
10. The configuration survives a normal reboot.
11. The fallback path remains available if acceleration fails.
12. Performance is measured and compared with the previous working baseline.

Use appropriate tools and tests for the actual stack. Possible evidence includes:

- `dmesg` and kernel logs.
- DRM debug information.
- `modetest`, where supported.
- `eglinfo`.
- `glxinfo`, where applicable.
- `kmscube`, where applicable.
- GLES rendering tests.
- Vulkan tests only if a valid Vulkan driver exists.
- GPU sysfs telemetry and debugfs, where available.
- Compositor logs and renderer identification.
- Reproducible frame-time and rendering benchmarks.

Do not treat a test as successful if it silently falls back to llvmpipe, softpipe, SwiftShader or another software renderer.

Explicitly detect and report software rendering.

## 3.4 Optimize for the actual device

The goal is maximum practical GPU performance without sacrificing stability.

Investigate:

- GPU clock and voltage scaling.
- Devfreq integration.
- Runtime PM.
- Thermal throttling.
- Memory bandwidth and interconnect configuration.
- Buffer allocation and sharing.
- Display refresh and composition overhead.
- Unnecessary CPU copies.
- Framebuffer-to-DRM transition costs.
- Rendering resolution and scaling.
- Compositor scheduling.
- Driver and userspace configuration.

Do not force unsafe clocks, voltages, thermal limits or power settings.

Do not disable thermal protection.

Do not sacrifice device stability for a benchmark result.

If the hardware or kernel imposes a real limitation, document it precisely and implement the best safe alternative.

## 3.5 GPU result classification

At the end of mission 60000, assign exactly one status:

- `GPU_ACCELERATION_VERIFIED`: real GPU rendering and the intended runtime path have been demonstrated.
- `GPU_ACCELERATION_PARTIAL`: some hardware acceleration works, but one or more critical components remain incomplete.
- `GPU_ACCELERATION_BLOCKED`: a specific kernel, firmware, driver, ABI or hardware blocker prevents working acceleration.
- `GPU_SOFTWARE_FALLBACK_ONLY`: only software rendering has been demonstrated.

Never report `GPU_ACCELERATION_VERIFIED` without runtime evidence.

A blocked result must include the exact blocker, the attempted fixes, the logs or tests supporting the diagnosis, and the next technically valid route.

# 4. FINISH-ONLY POLICY — DO NOT REBUILD WHAT ALREADY WORKS

Before modifying anything:

1. Inspect the repository state.
2. Inspect existing mission reports and previous work.
3. Inspect Git status and uncommitted changes.
4. Identify implemented functionality.
5. Identify incomplete functionality.
6. Identify known regressions.
7. Identify missing hardware verification.
8. Establish a reproducible baseline.

Create a completion matrix for every mission:

| Area | Existing implementation | Verified working | Remaining work | Regression risk |
|---|---|---|---|---|

Use these classifications:

- Complete and verified.
- Implemented but unverified.
- Partially implemented.
- Broken.
- Missing.
- Blocked by external hardware, firmware or kernel support.

Do not rewrite complete and verified components.

Do not replace existing implementations merely because you prefer another architecture.

Do not delete working compatibility code without proving that its replacement is better.

Prefer small, targeted, reversible changes.

If a mission is already fully complete and verified, record its evidence and move on.

# 5. REMAINING MISSION WORK

After prioritizing GPU acceleration, finish the remaining work in the original order.

## 61000 — Exynos 9820 MFC foundation

Inspect the existing MFC implementation and finish only the missing work.

Verify:

- MFC hardware and kernel integration.
- Device-tree and firmware requirements.
- Firmware paths and packaging.
- Media device registration.
- V4L2/media-controller integration.
- Required userspace libraries and tools.
- Real hardware decoding and encoding support, where available.
- Error handling and graceful fallback.

Historical known issue to explicitly investigate:

```text
/lib/firmware/mfc_fw.bin
/dev/video6
```

Earlier testing indicated that the firmware file was missing and `/dev/video6` was never successfully opened. Determine whether this remains true. Do not assume the issue is fixed because files or device nodes have appeared.

A successful MFC result requires an actual hardware-backed media operation, not merely package installation or device-node discovery.

Keep MFC work coordinated with mission 60000, but do not claim MFC acceleration is GPU acceleration. They are distinct hardware paths.

## 62000 — Shell, Flatpak, boot/shutdown and live-console integration

Audit the existing work and finish only incomplete pieces.

Preserve existing Nuxel functionality and the current device recovery path.

Check:

- Shell behavior.
- Flatpak integration.
- Application startup and lifecycle.
- Boot and shutdown handling.
- Live-console behavior and indicators.
- Service dependencies and ordering.
- Logging and failure recovery.
- GPU-aware display startup and fallback behavior.

Ensure the shell and compositor do not prevent boot when the GPU is unavailable.

Do not introduce a dependency that causes a black screen or removes console access.

## 63000 — Nuxel Vault, keyring and Authenticator

Audit and complete the existing implementation.

Verify:

- Secure local secret storage.
- Keyring initialization and lifecycle.
- Encryption and key handling.
- Authentication and unlock flows.
- Recovery and error handling.
- Authenticator behavior.
- Application integration.
- Packaging and service startup.

Do not expose secrets in logs, tests, screenshots, reports or command output.

Do not replace cryptographic primitives with homemade implementations.

Do not silently weaken security to make a test pass.

## 64000 — BCM4773 GNSS/GPS

Inspect the actual device hardware and existing implementation.

Verify:

- Hardware identification and connectivity.
- Kernel and userspace integration.
- Required firmware.
- Device permissions.
- GNSS service startup.
- NMEA or other supported data path.
- Position acquisition and reporting.
- Failure handling.

Distinguish between a service starting successfully and an actual satellite fix.

Do not report GPS hardware as working without real device evidence.

## 65000 — Samsung NFC

Inspect the actual NFC hardware and existing integration.

Verify:

- Hardware identification.
- Driver and device-tree support.
- Firmware requirements.
- Userspace interface.
- Permissions and service startup.
- Tag detection.
- Real NFC interaction, where safe and supported.

Distinguish between a detected controller and a functioning NFC stack.

Do not claim successful NFC operation without a real hardware test.

# 6. REPOSITORY AND DEVICE SAFETY

The primary device is a Samsung Galaxy S10+ SM-G975F (`beyond2lte`).

Preserve the existing Nuxel environment and recovery options.

Mandatory safeguards:

- Never automatically flash a kernel, boot image, recovery image or full OS image.
- Never automatically reboot the physical device.
- Never change partitions, bootloader state, FRP, KG state or secure-download settings.
- Never wipe user data.
- Never run destructive cleanup commands.
- Never use `git reset --hard`.
- Never use `git clean -fdx`.
- Never force-push.
- Never overwrite unrelated owner changes.
- Never expose SSH keys, tokens, credentials or secrets.
- Never remove working SSH, USB or console access.
- Never make an unverified display or GPU change the only boot path.
- Never remove the framebuffer or console fallback until a replacement is proven.
- Never claim physical verification when only cross-compilation or static inspection was performed.

If a physical reboot, flash, recovery action, partition change or other device-side operation is necessary, prepare the exact command and explain the risk. Stop and request explicit human approval before executing it.

Keep the device recoverable throughout the work.

# 7. BUILD, TEST AND REPAIR LOOP

For every mission:

1. Read its kickoff document in full.
2. Read its full specification in full.
3. Inspect the existing implementation.
4. Identify what is genuinely incomplete.
5. Record a baseline.
6. Implement the smallest complete fix.
7. Build the affected components.
8. Run focused tests.
9. Run relevant regression tests.
10. Inspect logs and test output.
11. Repair failures.
12. Repeat until the acceptance criteria pass or a real blocker is established.
13. Review the complete diff.
14. Update the mission report and evidence.
15. Commit only if the repository's existing workflow and project conventions support it. Never create a commit containing unrelated owner changes.

Do not hide failures.

Do not weaken tests to achieve a green result.

Do not mark a test as passed if it was skipped, mocked, or not run.

For each test, record:

- Exact command.
- Exit status.
- Relevant output.
- Hardware or emulator context.
- Whether it was a real hardware test.
- Any limitations.

# 8. EXECUTION ORDER AND PRIORITY

Follow this order:

```text
PHASE 0 — Repository and device baseline
PHASE 1 — 60000 GPU acceleration: investigate, implement, verify, optimize
PHASE 2 — 61000 MFC foundation
PHASE 3 — 62000 shell and system integration
PHASE 4 — 63000 Vault and Authenticator
PHASE 5 — 64000 GNSS/GPS
PHASE 6 — 65000 NFC
PHASE 7 — Cross-mission integration and regression audit
PHASE 8 — Final evidence and owner handoff
```

GPU work remains the highest priority throughout the run.

If GPU acceleration is blocked by an external kernel, firmware or hardware dependency, do not waste time repeatedly attempting the same failed fix. Document the blocker, complete the best safe work possible, and continue with the remaining missions. Return to GPU integration during the final cross-mission review if a dependency has been resolved.

Do not let a low-priority mission consume the time needed to finish a feasible GPU implementation.

# 9. RUN TRACKING AND CHECKPOINTS

Create a clearly named run directory, for example:

```text
artifacts/pwnage-completion-60000-65000/
```

Adapt to existing repository conventions if they already provide a suitable location.

Maintain:

```text
manifest.md
baseline.md
completion-matrix.md
execution-ledger.md
gpu-acceleration-report.md
mfc-report.md
shell-integration-report.md
vault-report.md
gnss-report.md
nfc-report.md
regression-report.md
final-report.md
owner-actions.md
evidence/
```

The execution ledger must record:

- Current mission.
- Current task.
- Files inspected.
- Files changed.
- Tests run.
- Test outcomes.
- Remaining blockers.
- Next action.
- Whether physical hardware verification is still required.

Checkpoint after each mission.

Do not lose progress if the agent session is interrupted. On resumption, read the ledger and inspect the actual repository state before continuing.

# 10. CROSS-MISSION INTEGRATION

Once all six missions have been addressed, perform a targeted integration review.

Pay particular attention to:

- GPU driver and userspace compatibility.
- GPU-aware compositor startup.
- Framebuffer fallback.
- MFC and GPU responsibilities being kept distinct.
- Media playback and display integration.
- Shell startup and display service dependencies.
- Boot reliability.
- Vault and Authenticator service lifecycle.
- GNSS and NFC service startup.
- Package dependencies and conflicts.
- Kernel configuration and device-tree consistency.
- Firmware packaging.
- Resource usage and memory pressure.
- Regression of existing Nuxel features.

Do not introduce unrelated architectural changes during this stage.

# 11. DEFINITION OF DONE

The phase is finished only when:

- All six mission specifications have been read and assessed.
- Existing completed work has been preserved.
- Remaining feasible work has been implemented.
- Builds and relevant tests have been executed.
- Regressions have been checked.
- GPU acceleration has an explicit evidence-backed status.
- MFC has an explicit evidence-backed status.
- GPS and NFC distinguish service readiness from actual hardware functionality.
- No unapproved destructive device operations have occurred.
- Reports and evidence are complete.
- Remaining owner actions are clearly documented.

A mission can be marked complete only if its acceptance criteria are genuinely met.

A hardware-dependent mission may be marked `IMPLEMENTED — HARDWARE VERIFICATION REQUIRED` or `BLOCKED`, but must not be presented as fully working.

# 12. FINAL REPORT

Produce a concise but technically detailed final report containing:

## Executive summary
What was already complete, what was fixed, and what remains.

## GPU acceleration — highest priority
Include:

- Actual GPU identification.
- Kernel driver and userspace driver.
- Firmware status.
- Rendering backend.
- Whether hardware rendering was proven.
- Whether software fallback was detected.
- Actual benchmark results.
- GPU utilization or other hardware evidence.
- Stability and reboot-persistence status.
- Remaining blockers.
- Final GPU status classification.

## Mission completion table

| Mission | Starting state | Work completed | Tests | Final status |
|---|---|---|---|---|

## Changed files
List every meaningful file changed and why.

## Test evidence
Include exact commands and results.

## Regressions
State what was checked and any remaining concerns.

## Hardware verification
Separate actual device testing from static inspection, compilation, emulation and mocked tests.

## Owner actions
List only actions that genuinely require the owner's involvement, especially any physical-device operation requiring approval.

## Next recommended work
If any mission remains blocked, identify the most direct technically valid next step.

---

# FINAL DIRECTIVE

Start by inspecting the repository and all twelve mission documents.

Do not assume the work is unfinished just because it is in scope. Do not assume it is finished just because code exists.

**Your number-one job is to make GPU acceleration genuinely work on the Exynos 9820 in Nuxel, to the maximum safe and technically achievable extent.**

Prioritize real driver integration, correct kernel/userspace compatibility, hardware-backed rendering, measurable performance, stable compositor integration, and a reliable fallback.

Then finish the remaining 61000–65000 work without disturbing functionality that already works.

Execute. Verify. Measure. Repair. Document.

Do not return with a plan when you can perform the work.
