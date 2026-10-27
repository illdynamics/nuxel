# 🐧 PWNAGE 28000 — TRI-LINK + HOME-UNLOCK KICKSTARTER

Read and execute `./NUXEL-28000-TRI-LINK-UBERFIXER-UBERPROMPT.md` as the full specification. Work in the existing Nuxel repository; inspect the actual code and current git/deployment state first.

Implement the Tri-Link Console with **three separate icons in the Applications window**: **Serial Live Console**, **USB SSH Console**, and **Wi-Fi SSH Console**. Preserve serial as the recovery path; make Wi-Fi SSH a real, secure authenticated shell where supported; implement USB SSH only if the current Samsung S10+ Exynos 9820/Linux 4.14 gadget stack and host actually support it. If not, show an honest unavailable state and document evidence—do not fake success or flash the kernel.

Also fix the navigation root cause so **boot → lockscreen → successful unlock always lands on the Home desktop**, never the Applications window. Add automated tests, check the three entries are registered exactly once, verify the lockscreen and existing Wi-Fi/browser/charging/serial behavior, and report host tests separately from physical S10+ evidence.

**Safety first:** inspect for active PWNAGE 25000/other deployment work and current serial-port ownership. Do not mutate overlapping files or deploy while another transaction/agent owns the device. Never run two serial clients concurrently. Preserve recovery, checkpoint changes, and provide rollback steps. No kernel flashing, wiping, or unrelated changes.

Finish with actual code changes, tests and a concise evidence-based report. Do not stop after writing a plan.

