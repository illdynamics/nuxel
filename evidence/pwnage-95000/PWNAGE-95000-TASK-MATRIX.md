| PWNAGE ID | Pairing | Requirements | Overall status | Confidence | Evidence |
|---|---|---:|---|---|---|
| 2000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 3000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 4000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 8000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 9000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 10000 | PAIR | 8 | `NOT_IMPLEMENTED` | HIGH | New untracked NEXUS+NEO Phase 0 prompts appeared during the audit (mtime 2026-11-08 18:06); no implementation, build, deployment or live evidence exists. |
| 11000 | PAIR | 10 | `NOT_IMPLEMENTED` | HIGH | New untracked NEXUS+NEO Phase 1 prompts appeared during the audit (mtime 2026-11-08 18:06); prerequisite Phase 0 is not implemented. |
| 12000 | CONFLICTING_VERSIONS | 7 | `SPEC_INCOMPLETE` | HIGH | ID collision: old SnekByte kickstarters use 12000, while new untracked NEXUS+NEO Phase 2 prompts also use 12000. No single unambiguous historical requirement set; Phase 2 is not implemented. |
| 14000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 15000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 16000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 17000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 18000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 19000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 20000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 21000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 22000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 23000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 24000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 25000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 26000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 27000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 28000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 29000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 30000 | PAIR | 1 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.1 commit da0426b8; tests/pwnage30000 pass; live app tree/registry present. |
| 31000 | PAIR | 1 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2; tests exist; live preload receipt shows ALREADY_RAN for current boot. Test drift: older preload expectations fail against P90-era code. |
| 32000 | PAIR | 24 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2 commit b4e2f51e; tests/pwnage32000 contracts. |
| 33000 | PAIR | 35 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2 commit b4e2f51e; contacts/messages/dialer tests. One stale Recorder test expectation. |
| 34000 | PAIR | 37 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2 commit b4e2f51e; tests/pwnage34000 pass. |
| 35000 | PAIR | 45 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2 commit b4e2f51e; performance/navigation changes present in current tree. |
| 36000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 37000 | PAIR | 40 | `DEPLOYED_UNVERIFIED` | MEDIUM | Commit 02941a40 and v0.7.3; current tree contains butterscotch profile. Some tests are stale against later P89/P90 audio changes. |
| 38000 | PAIR | 50 | `DEPLOYED_UNVERIFIED` | MEDIUM | Commit 1c2eb21f/v0.7.4; audio path owner-confirmed historically; tests/pwnage38000 pass. |
| 39000 | PAIR | 15 | `PARTIALLY_DEPLOYED` | MEDIUM | Evidence pwnage-39000 records Wi-Fi boot and stabilization; several polish items remained partial. |
| 40000 | PAIR | 19 | `DEPLOYED_UNVERIFIED` | MEDIUM | Speaker root cause and owner-confirmed audio in v0.7.4 history; current tree has tests but three assertions are stale after P89 audio redesign. |
| 41000 | PAIR | 30 | `DEPLOYED_UNVERIFIED` | MEDIUM | Wi-Fi boot/default state work is present; live Wi-Fi SSH is working, but a fresh boot cycle was not repeated in this audit. |
| 42000 | PAIR | 68 | `PARTIALLY_DEPLOYED` | HIGH | Network GeoClue location is live; satellite GNSS remains BLOCKED_FIRMWARE. |
| 43000 | PAIR | 59 | `PARTIALLY_DEPLOYED` | MEDIUM | Boot/lockscreen/UI work landed; hardware audio/USB experiments and owner checks remain partial. |
| 44000 | PAIR | 67 | `DEPLOYED_UNVERIFIED` | MEDIUM | Commit 100c6890; PWNAGE-44000 live report covers drag, power menu, screenshot, gallery, files, status truth. |
| 45000 | PAIR | 140 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-45000 live report; MTP/security/app registry/flashlight paths live; NFC/fingerprint/cellular remain blocked. |
| 46000 | PAIR | 88 | `PARTIALLY_DEPLOYED` | HIGH | Seven orientation modes and manual transforms work; auto-rotation blocked by sensor hub. Some tests intentionally stale after Doom landscape policy. |
| 47000 | PAIR | 57 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-47000/92000 reports: XRDP/VNC physically verified; scrcpy is Android-only; USB network remains blocked. |
| 49000 | PAIR | 135 | `DEPLOYED_UNVERIFIED` | MEDIUM | PWNAGE-49000 source/headless report plus later live deployments; one cache-version test is stale (current p94000 cache-buster). |
| 50000 | PAIR | 91 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-50000 graphics report: Mali/kbase/EGL and SHM WebKit work; DMA-BUF/zero-copy blocked. |
| 51000 | PAIR | 86 | `PARTIALLY_DEPLOYED` | HIGH | Kernel/flatpak/graphics blockers report; several blockers remain kernel/hardware-bound. |
| 52000 | PAIR | 60 | `PARTIALLY_DEPLOYED` | MEDIUM | PWNAGE-52000 ledger marks many items PASS/partial; one Quick Settings test is stale against P94 extended-level model. |
| 53000 | PAIR | 42 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-53000 graphics report: linear dmabuf/Mali path works; WebKit hardware transport remains blocked. |
| 54000 | PAIR | 128 | `PARTIALLY_DEPLOYED` | HIGH | Seven-mode orientation and manual rotation verified; auto sensor path remains blocked. |
| 55000 | PAIR | 108 | `BLOCKED` | HIGH | WebKit/DMA-BUF/DRM/VGEM prerequisite absent; no /dev/dri; zero-copy scanout unavailable. |
| 56000 | PAIR | 72 | `PARTIALLY_DEPLOYED` | HIGH | Flatpak/user-namespace integration is live (Ferdium/Stremio running); full ARM64 app/portal matrix remains partial. |
| 57000 | PAIR | 99 | `BLOCKED` | HIGH | Broadcom SSP sensor hub is down; raw accelerometer values are zero; vendor patch/runtime missing. |
| 58000 | PAIR | 82 | `VERIFIED_LIVE` | HIGH | PWNAGE-58000 deployed and measured across repeated boots; idle-wakeup work wired into rootfs and live services. |
| 60000 | PAIR | 19 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-60000 report: GPU-SHM production profile live; WebKit DMA-BUF, zero-copy, MFC, HDMI/casting blocked. |
| 61000 | PAIR | 47 | `PARTIALLY_DEPLOYED` | HIGH | MFC kernel/userspace/firmware design implemented; no physical decode; host test blocked by missing linux/videodev2.h in audit environment. |
| 62000 | PAIR | 14 | `DEPLOYED_UNVERIFIED` | MEDIUM | PWNAGE-62000/72000 live hash parity and shell health; physical app/touch matrix remains owner-only. |
| 63000 | PAIR | 14 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-63000/73000 live hash parity and host suites; keyring has not been initialized by owner. Current NuXtore catalog integrity fails on changed Doom files. |
| 64000 | PAIR | 15 | `PARTIALLY_DEPLOYED` | HIGH | GNSS provider/diagnostics deployed; satellite fix BLOCKED_FIRMWARE. |
| 65000 | PAIR | 33 | `PARTIALLY_DEPLOYED` | HIGH | NFC daemon deployed and running OFF; kernel NFC class/physical tag read blocked. |
| 66000 | PAIR | 14 | `BLOCKED` | HIGH | QBT2000 sensor/driver present; no verified TEE-backed provider; enrollment correctly refused. |
| 67000 | PAIR | 39 | `BLOCKED` | HIGH | SSP sensor hub down; auto-rotation cannot receive real samples. |
| 68000 | PAIR | 48 | `BLOCKED` | HIGH | MFC hardware decode not physically proven; matching firmware/patched kernel not landed. |
| 69000 | PAIR | 18 | `BLOCKED` | MEDIUM | NuXtream/casting product absent; DP Alt Mode/DRM absent; USB-C audio requires owner hardware and USB-role testing. Diagnostics/config groundwork only. |
| 70000 | FULL_ONLY | 7 | `DEPLOYED_UNVERIFIED` | MEDIUM | PWNAGE-70000 live completion addendum in the 60000 report: atomic userspace deploy and GPU-SHM verifier passed; cold boot/benchmark not repeated. |
| 71000 | FULL_ONLY | 22 | `BLOCKED` | HIGH | MFC patched kernel/firmware/first decode not landed; MFC remains BLOCKED_GUARDED. |
| 72000 | FULL_ONLY | 7 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-72000 final report: source/live hashes match, userspace deployed, shell healthy; physical matrix owner-only. |
| 73000 | FULL_ONLY | 7 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-73000 final report: live 63000 hashes match and host suites pass; keyring/Vault owner acceptance pending. |
| 80000 | PAIR | 115 | `DEPLOYED_UNVERIFIED` | MEDIUM | PWNAGE-80000 report and tests; live app/navigation behavior partially revalidated by later tasks. |
| 81000 | PAIR | 133 | `PARTIALLY_DEPLOYED` | MEDIUM | PWNAGE-81000 workstreams carried into later live images; several owner/performance checks remain. |
| 82000 | PAIR | 132 | `PARTIALLY_DEPLOYED` | MEDIUM | PWNAGE-82000/84000 live reports; one stale Vesktop fallback assertion. |
| 83000 | PAIR | 26 | `BLOCKED` | HIGH | Camera FIMC-IS firmware/setfiles/media graph absent; no captured frame. |
| 84000 | PAIR | 202 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-84000 live report: clock/alarm/mic/downloader fixes deployed; camera/flatpak/Doom owner checks remain. |
| 85000 | PAIR | 55 | `VERIFIED_LIVE` | HIGH | PWNAGE-85000 live report: Flatpak stall root-caused/fixed and measured; whole-device residual idle poll documented. |
| 86000 | PAIR | 61 | `BLOCKED` | HIGH | Camera firmware/ISP/setfiles still missing; no physical frame. |
| 87000 | PAIR | 42 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-87000 hardware-verified alarm/timer audio and scroll fixes; lockscreen visual/owner checks remain. |
| 88000 | PAIR | 67 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-88000 live report: Doom/services/spoof/theme work; Waydroid and some physical items blocked. |
| 89000 | PAIR | 14 | `VERIFIED_LIVE` | HIGH | PWNAGE-89000 report: deployed hashes match; four measured boots, alarm/timer/readiness/SSH checks pass. |
| 90000 | PAIR | 15 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-90000 final report: source/integration/host tests; several physical input checks remain NOT RUN. |
| 91000 | PAIR | 33 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-91000 report: safe boot/service changes and hardware audits; hardware completion blocked. |
| 92000 | FULL_ONLY | 52 | `PARTIALLY_DEPLOYED` | HIGH | REPORT-USBNET: direct LAN XRDP/VNC physically verified; USB network/SSH blocked/unvalidated. |
| 93000 | PAIR | 74 | `PARTIALLY_DEPLOYED` | MEDIUM | All four workstreams deployed; 422/423 canonical live targets match; notification hub/API and icon resolution live. Uncommitted; physical finger/gesture acceptance pending; 2 launcher-registry checks fail. |
| 94000 | PAIR | 156 | `PARTIALLY_DEPLOYED` | MEDIUM | Deployed stamp 20261108T173717; 93/93 P94 source checks and 20/20 Back cycles. Uncommitted; Doom music, human audibility, landscape desktop remain incomplete. Live NuXtore Doom bundle digests are stale. |
| 96000 | PAIR | 35 | `NOT_IMPLEMENTED` | HIGH | New untracked PWNAGE-96000 prompt appeared during the audit (mtime 2026-11-08 18:40); no implementation, build, deployment or live evidence exists. |
