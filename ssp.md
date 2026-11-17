connect to Nuxel over ssh use key ~wicked/.ssh/wicked_wqn_id_rsa to connect to Nuxel, use root user and IP 10.11.12.99

Continue the Nuxel S10+ BCM47752 SSP recovery from the latest committed repository state.

Read `reports/SSP-STOCK-RUNTIME-2026-11-17.md` and all supporting evidence.

The matching Samsung G975FXXS9DTK9 Android runtime has now been recovered. All four vendor anchors match, zero dynamic library dependencies remain unresolved, and Samsung `lhd` executes with stock VNDK libraries inside hardware-denied isolation.

DO NOT repeat the stock firmware acquisition, runtime extraction, or previous sandbox assertion unless new evidence requires it.

Your next engineering objective is to establish the exact, verified initialization and communication contract between the existing Samsung `lhd` daemon, the kernel BBD interface, and the BCM47752 sensor hub.

Prioritize:

1. Analyze existing Samsung kernel, daemon and BBD transport implementations and search trustworthy upstream references for the exact initialization protocol.
2. Determine the expected messages, acknowledgements, error states, timeout behavior, startup ordering and firmware-loading responsibilities.
3. Investigate the existing native downloader's incorrect acceptance of unrelated transport packets as successful acknowledgements. Implement and test a correct protocol state machine only when supported by trustworthy evidence.
4. Improve the isolated test framework so it can exercise verified protocol behavior without exposing live power controls or requiring speculative hardware writes.
5. Characterize the daemon's configuration warnings, Binder dependency, and socket-denial messages; distinguish genuine initialization blockers from sandbox artifacts.
6. Prepare a documented, bounded physical hardware-init trial only after demonstrating a credible protocol path, with recovery provisions and explicit owner approval for any state-changing operation.
7. Once authorized and validated, obtain actual, physically changing accelerometer and gyroscope samples. Then verify Nuxel automatic rotation and relevant regressions.

Preserve commits `7cd354d4` and `3c06d253`, all working UI changes, and the recovered stock runtime.

Continue implementing and testing all safe work rather than stopping at a research report.

Do not invent an ACK, bypass protocol validation, make speculative firmware writes, expose unrestricted host sysfs or report synthetic sensor readings as real.

The success criterion remains verified physical motion data and functional hardware-driven rotation. Report any remaining external blocker precisely, without claiming success prematurely.
