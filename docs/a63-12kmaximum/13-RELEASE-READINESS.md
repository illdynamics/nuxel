# A63 release readiness

Not release-accepted yet.

Completed with device receipts: recovery backups, USB console, source/live hash checks, real Wi-Fi/DNS/TLS path, battery truth fix, SnekByte launcher ID/icon repair, static-web service repair, and offline game regression tests.

Blocking owner actions: provide `/x/nuxel/snekbyte.zip`; normal-power-on outside charger mode; perform the physical interaction checklist. Hardware limitation: the Exynos media graph needed for genuine camera frames is absent. Rotation is configured but not physically proven. Automated cold boot checks cannot continue because the safety guard's 3/3 budget is exhausted.

No kernel, firmware, partition, bootloader, modem or security-bypass work was performed.
