# PWNAGE-67000 — Kickstarter / Execution Prompt

Read **all of `full-pwnage-67000.md`** in the repository root and execute it as the implementation specification for the Samsung Galaxy S10+ (`beyond2lte`) gyroscope/accelerometer and automatic screen-rotation mission.

Do not write another research-only report. First inspect the current source and live target state, run the existing orientation tests, and preserve the already-working four fixed rotation modes, seven policy choices, Phoc transform map, single touch-matrix owner and sole framebuffer presenter.

The real blocker is the BCM47752KUB1G sensor hub / LSM6DSO data path: the repository evidence shows Samsung sensor nodes and IIO stubs, but accelerometer `raw_data` remained `0,0,0`; the BBD/SSP handshake failed; vendor `lhd` components were present on the read-only vendor partition while the required Android/Bionic runtime (`/system/bin/linker64`) was missing from the recorded Nuxel root. Resolve the exact compatible LHD/BBD runtime or implement a lawful native provider. Do not guess protocol bytes, enable bits, firmware, linker paths or vendor ABI; do not copy proprietary blobs into Git without permission; do not flash partitions or reset the shared hub in a loop.

Get genuine, fresh accelerometer samples first, calibrate the sensor-to-display mount matrix on the physical phone, and connect them to the existing `nuxel-orientationd` policy. Make Auto (FULL/PT/LS) work while retaining hysteresis, flat-phone hold, truthful degraded status, sensor power leases and exact compositor/touch read-back. Gyro fusion is optional and must remain separate until gyro data, units and axes are independently verified; accelerometer gravity is sufficient for initial auto-rotation.

Implement and test the actual code, update the S10+ image builder, add physical validation and evidence, and create a safe Wi-Fi SSH deployment plus rollback. If an owner-supplied firmware/runtime artifact is genuinely missing, complete all safe work and identify the precise blocker without claiming Auto works.

Follow the phase order, safety rules, tests, deliverables and acceptance checklist in `full-pwnage-67000.md`. Finish with changed-file summary, test counts, live sensor evidence, measured rotation latency, remaining owner-only tests, deployment command and rollback command.
