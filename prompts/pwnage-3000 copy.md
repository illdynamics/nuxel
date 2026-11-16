# 🐧 NUXEL A54 — PENGUIN RELIABILITY HYPERFIX 3000

**Model:** DeepSeek-v4-pro-thinking. **Target:** the user's CURRENT running Samsung Galaxy S10+ Nuxel Fedora ARM64 installation, with the existing USB Live Console.

Read `./NUXEL-A54-PENGUIN-RELIABILITY-HYPERFIX-UBERPROMPT.md` **fully** and execute its phases. This is a physical-device-focused implementation mission, not an offline report-only task.

Repair FIVE observed regressions:

1. **Wi-Fi:** Connect no longer hangs at "Associating DHCP..."; real AP authentication/association, DHCP, DNS, HTTPS and saved credentials work even after reboot. Distinguish actual NM state from UI text and never reintroduce invalid AP `'/new'`.
2. **Rotation:** Restore seven modes (Auto, Auto Portrait, Auto Landscape, Forced Portrait, Forced Landscape, Reverse Portrait, Reverse Landscape). Automatic modes physically rotate using validated sensors; manual modes immediately work even if sensors unavailable. Remove `undefined` startup state.
3. **Status bar:** Wi-Fi/spinner must never overlap battery or any other icon; fix duplicate layers/layout ownership across rotation and startup.
4. **Boot readiness:** Show real numeric battery percent immediately when readable; restore rotation mode/policy from startup; no minutes-long waiting.
5. **Camera:** Install and physically launch real Fedora `snapshot` native Camera on the S10+, plus complete a separate genuinely Nuxel-owned Camera app. Exynos ISP real-frame availability remains a distinct, honestly reported hardware gate.

Use bounded, source-backed diagnostics, transactional package installs, minimal changes, live USB deployment, rollback and cold-boot verification. Preserve the working lockscreen, keyboard, docks, browser, Photos/media store and recovery console. **No flashing, no kernel changes, no fabricated hardware results, no credential exposure, no unapproved reboot.**

Execute, test and report exact PASS/PARTIAL/BLOCKED gates with real device evidence. 🐧🔥
