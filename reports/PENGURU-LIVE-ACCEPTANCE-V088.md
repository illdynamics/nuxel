# PenGuru Squad — Live S10+ Acceptance & Power Profiling (v0.8.8-beta)

**Device:** Samsung Galaxy S10+ (`SM-G975F`, Exynos9820 / beyond2lte)
**Image/kernel:** Nuxel mobile build `Linux WIN-CLIENT 4.14.253-gf7194c1d15ed-dirty` (aarch64), systemd 258 PID 1
**Host:** build host — no permanent handset attachment; live facts taken over Wi-Fi SSH (`root@10.11.12.99`).

> This report records **what was actually measured on this device/environment**.
> Anything not measurable here (continuous soak, thermal-under-load, battery-drain
> curves) is marked `BLOCKED` and never given an invented number. Per the mission,
> a passing unit test is NOT proof that a model generates text on the phone; only
> the on-device CodeBird self-test in `penguru-squad/penguru/implementation/EVIDENCE.md`
> counts as device verification.

## 1. Device reality (Stage 3 preflight) — MEASURED

| Quantity | Value | Source |
|---|---|---|
| Kernel | `4.14.253-gf7194c1d15ed-dirty` aarch64 | `uname -r` on device |
| RAM | 7419 MiB total, ~5627 MiB available | `free -m` |
| CPU | 8× Cortex-A55 (AArch64), NEON/ASIMD + AES present | `lscpu` / `/proc/cpuinfo` |
| Storage (`/`) | 111 GiB, 56 GiB used, 56 GiB free | `df -h` |
| NPU driver | **No user-space NPU (Hexagon/ADSP) node enumerated** — no usable NNAPI backend confirmed | device probe; do NOT assume NPU |
| Backend chosen | **llama.cpp CPU GGUF only** (NEON kernels); ONNX GenAI export not shipped | plan §5.6 / EVIDENCE |

Decision: backends were validated against the real A55/NEON capability, and no NPU
backend was assumed. The llama.cpp CPU build (`GGML_NATIVE=ON`, CPU-only) is the
only runtime in this beta.

## 2. Backend verification on device (Stage 2 / G1)

**CodeBird — `empero-ai/Qwen3.8-4B-Distill-GGUF` Q4_K_M** (`391fc7d…`, manifest sha256 verified):
- Installed at `/var/lib/nuxel-penguru/models/codebird/391fc7d…/gguf-q4km/Qwen3.8-4B-Q4_K_M.gguf` (2,783,446,304 bytes; sha256 matches manifest).
- Load: cold 618 ms / warm 492–524 ms (`architecture=qwen35`, `n_params=4.326e9`).
- Generation (prompt 9 tok → 40 greedy, 4 threads, ctx 4096): **2.610 decode tok/s**; second run 60 tokens **2.500 tok/s**.
- Peak RSS **~2850 MiB** (weights mapped 2572.86 MiB + 257.01 MiB compute buffer).
- Cancellation: SIGTERM during decode emitted `{"event":"cancelled","generated_tokens":1}`, exited 0, worker process gone, free memory returned to baseline → **unload verified**.
- Source: `penguru-squad/penguru/implementation/EVIDENCE.md` (G1 section); command trace in `hw-png-run.log`.

**ChatBird — `Impish_LLAMA_4B_Abliterated-Q4_K_M`:** manifest pinned & integrity-checked against the HF immutable revision, but **not installed** on device: download is gated on the provenance/license review recorded in its manifest (`redistribution: review_required`). Its load/generation self-test runs only after the owner accepts the license record. → *device inference NOT verified for ChatBird this cycle.*

## 3. Live power sample (idle baseline) — MEASURED (single point, not a drain curve)

| Condition | Voltage | Current | Est. terminal power | Note |
|---|---|---|---|---|
| Idle, no AI process (`nuxel-penguru` static/inactive) | 3.926 V | ~1.5 mA | ≈ 5.9 mW | `voltage_now/current_now` at rest; battery 32% |

**Limitation:** this is a single idle sample. A full drain curve (AI off, interface
idle, SonarBird routing, ChatBird/CodeBird active inference, heavy repeated prompts,
post-inference inactivity, battery-saver) requires an attached logger over time and
was **BLOCKED** in this environment — no numbers are invented for those states.

## 4. Thermal / throttling

No sustained compute was driven from the build host this cycle (service kept
inactive by default). Continuous thermal-throttling figures under load are
`BLOCKED`; the prior on-device self-test completed without a thermal event (per
EVIDENCE). No model here is run "always resident" — one heavy worker at a time,
bounded context, 4 threads, disabled-by-default.

## 5. Offline regression evidence (host) — PASS

| Suite | Command | Result |
|---|---|---|
| SonarBird routing (+adversarial no-SYSTEM set) | `python3 services/nuxel-penguru/tests/test_routing.py` | **ALL PASS** |
| Model Store signed-manifest verification | `.../tests/test_registry.py` | **ALL PASS** |
| Worker protocol / queue | `.../tests/test_worker_protocol.py`, `test_installation.py` | **PASS** |
| Bridge P0/P1 (G0) identity + grant boundary | `python3 services/nuxel-bridge/test-security-g0.py` | **ALL PASS** (loopback 401, forged/replayed → rejected, launcher-only native launch, USB:access required) |
| Portal one-shot grant policy | `python3 services/nuxel-portal/test-portal-policy.py` | **PASS** |
| Canonical version lockstep | `python3 tests/pwnage90000/test_release_assets.py` | **0 failures** across all version surfaces |

## 6. Acceptance verdict

- **Deployable as opt-in, disabled-by-default beta:** YES — service installed (`static`, does not auto-start), CodeBird verified on device, G0 closed & regression-tested, download gated behind a signed manifest + license ack + runtime self-test.
- **ChatBird live inference:** NOT VERIFIED (license-gated; install deferred by design).
- **Continuous battery/thermal soak:** BLOCKED in this environment — recorded as such, no figures invented.
- **Recommendation:** ship the opt-in beta with CodeBird only until ChatBird's manifest is signed and its license review clears; keep wake-word/mic disabled by default; one bounded worker at a time.
