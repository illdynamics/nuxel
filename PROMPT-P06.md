# Nuxel component P06 — Repair current hard-red regression gates

## Agent mission (this branch ONLY)

You are the Nuxel Fedora ARM64 phone OS engineering agent, working in a dedicated Git feature branch. Implement **only component P06: Repair current hard-red regression gates** in this existing repository. This file is the complete scope for the current run; do not implement the other screenshot items in this branch. Reuse actual Nuxel architecture and existing services instead of creating parallel or fake substitutes.

Target platform: Samsung Galaxy S10+ SM-G975F / Exynos 9820; Nuxel Fedora ARM64 without Android framework dependencies. A MacBook host may build/test; the live phone may not be connected. Don't assume a hardware verification that did not happen.

## Component-specific implementation contract

1. Inspect all currently failing required checks and their intended contracts.
2. Fix genuine application defects before weakening tests.
3. Separate obsolete tests from newly intended behavior using documented rationale.
4. Preserve independent smoke checks for boot, input, navigation and recovery.

## Required workflow

1. Inspect actual repository files, test/deploy docs, and component dependencies. Record existing behavior and smallest coherent repair/implementation plan.
2. Implement source, assets, service/config changes and useful tests needed for this component. Preserve working launcher navigation, haptics, custom icon assets, Home layouts and USB recovery.
3. Run the most relevant local tests/build/lint. For AArch64 native code, cross-build or document precise toolchain restrictions. Never pass off mocks as physical checks.
4. Write `docs/component-reports/p06.md` with code paths changed, commands/receipts, PASS/FAIL/BLOCKED/NOT_TESTED, actual device deployment status, unresolved issues and safe rollback instructions.
5. Commit **only this component's** code, tests, documentation and report on the checked-out branch. Do not merge into main, switch branches, add secrets, or generate unrelated features. Check `git status` and finish with a clean worktree. The queue runner will push this branch.

## Acceptance gates

- Every component-specific item above is implemented or explicitly marked BLOCKED with concrete evidence (not omitted).
- Tests exercise real behavior and failure paths, not only static references.
- Where a feature touches the phone, distinguish mock/host tests from live deployed and owner-confirmed results.
- Any dangerous hardware operation (flashing, bootloader/partition write, kernel replacement, unsafe amplifier or LED setting) is **forbidden** during this task.
- If a critical external dependency blocks this feature, produce the smallest safe implementation, a precise blocker report, and stop attempts; do not let manual hardware proof stall unrelated tasks in the queue.

**Start with a source audit; implement, test, commit and report. COMPONENT P06 ONLY.**
