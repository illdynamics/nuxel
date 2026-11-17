Continue the Nuxel Galaxy S10+ Exynos9820 FIMC-IS camera recovery from `/Users/wicked/x/nuxel`.

connect to Nuxel over ssh use key ~wicked/.ssh/wicked_wqn_id_rsa to connect to Nuxel, use root user and IP 10.11.12.99
if you need to reflash anything thats impossible without TWRP access, you are allowed to reboot into recovery and reflash th
e phone. if you reflash and it ends up in TWRP again that means I did that and it bootlooped/hung/crashed. then you re-inves
tigate, fix and reflash again until we boot into nuxel again then it was successful.

I have extracted `NUXEL_CAMERA_RECOVERY_V2/` into the existing repository.

Read and execute the COMPLETE engineering mission in:

`NUXEL_CAMERA_RECOVERY_V2/02_AGENT_CAMERA_CONTINUE_UNTIL_VERIFIED.md`

Also read the accompanying independent audit, SHA-256 evidence JSON, README, and original recovery-tool source.

**Latest reported camera commits:**
- `180d9839`
- `a4ad813c`

Reconcile the separate camera worktree `/tmp/nuxel-camera-endgame-audit` with my current repository, preserving all existing changes.

The rear-main 2L4 sensor successfully reached EEPROM calibration, but physical capture stopped at `fimc_is_sec_run_fw_sel (-5)` with the message `Camera: Failed open phone firmware`.

Independent analysis of the supplied archive confirms that seven of the eight bundled camera firmware files disagree with the recorded manifest.

**Your immediate priority is to identify the exact firmware file, loader path, and source-level failure condition.**

Recover and verify matching camera firmware from my previously downloaded Samsung `G975FXXS9DTK9` stock AP, which was already used successfully for SSP runtime recovery.

Use the supplied tools to compare stock, current bundled and pinned public-reference firmware candidates. Do not blindly install mismatched blobs or regenerate hashes just to make validation pass.

Implement every justified host-side fix, firmware-path correction, build adjustment and regression test that can be completed safely.

Once a complete, compatible firmware set and defensible recovery procedure are established, present the exact bounded hardware trial for approval.

After authorization, work toward the first genuine, nonzero, physically captured rear-main frame. Then continue through remaining cameras, PipeWire, camera portals, camera application support, recording, privacy, suspend/resume and reboot verification.

Do not stop at another research report while further safe implementation or testing work is possible. Do not manufacture success, repeat uncontrolled sensor initialization attempts or perform unattended flashing.

Deliver actual working code, verified commits, physical evidence and clear remaining blockers.

**The final goal is a genuinely functional S10+ camera system—not merely successful firmware loading or simulated preview.**
