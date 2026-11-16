# PenGuru implementation evidence

Living evidence log. A checked item names the command, test output or device
observation that proves it. Nothing here is marked complete from source alone.

## Environment

- Host: `Linux 4.14.253-gf7194c1d15ed-dirty` aarch64, 8 cores, 7.2 GiB RAM,
  no swap, Fedora 43 userland, systemd 258.
- Build tools present: gcc, g++, cmake, ninja, python3, git.
- `dnf repoquery`: `llama-cpp-tools`/`llama-cpp-devel` not packaged for this
  distro; `onnxruntime`/`onnxruntime-devel`/`python3-onnxruntime` 1.20.1.
- Microphone: ALSA capture devices present (`beyondmadera` / WDMAx).
- Network reachable (HF API + Xet CDN). Exact GGUF metadata verified via the HF
  API and an immutable revision URL (see model manifests).

## G0 — privilege safety

- [x] Bridge defaults to `production`; loopback bypass requires BOTH
  `NUXEL_HTTP_MODE=dev` and `NUXEL_HTTP_DEV_LOOPBACK_BYPASS=1`.
  Evidence: `python3 services/nuxel-bridge/test-security-g0.py` — live server:
  unauthenticated loopback POST is 401; `/api/v1/health` is 401 on device.
- [x] Body `app_id` is bound to the bearer token identity on every POST.
  Evidence: forged app id -> 403 `identity_mismatch`; launcher token for Home
  replayed as another app -> 403; correctly bound token reaches handler.
- [x] Launcher-only apps cannot self-bootstrap a token; self-bootstrapped
  tokens cannot reach authority RPCs.
  Evidence: same test, `Vault cannot self-bootstrap`, `authority RPC refuses`.
- [x] Native launch authority: only a Home-bound launcher token may start
  native/Flatpak entries; PWA and self-bootstrapped tokens -> 403
  `launch_not_authorized`.
- [x] USB mode change now requires `usb:access` (was unchecked).
- [x] `once` grants are consumed and persisted as consumed; second action in
  the same daemon lifetime is denied.
- [x] `session`/owner grants are bound to the daemon session id and cannot be
  replayed in another session.
- [x] Unknown durations/malformed records are denied, never elevated to
  `always`.
- [x] Portal store consumes a one-shot grant atomically (portal policy suite
  passes, including the alias case that previously failed).
- [x] One canonical capability registry: bridge ids resolve through
  `shell/nuxel-shell/nuxel-permissions/capabilities.json`; unknown ids denied.
- [x] Device: nuxel-bridge, nuxel-http-bridge, nuxel-portal, nuxel-permd all
  active with the new code; Home's launcher-minted RPC returns 200; the
  security-state publisher returns `locked=true mode=swipe`.
- [x] Both bridge suites and the permission/portal suites pass locally:
  `services/nuxel-bridge/test-*.py` (11 suites), `test-portal-policy.py`,
  `test-permissions.py` (14), `test-policy-defaults.py` (14),
  `verify-wiring.js` (6 surfaces), launcher activation, tri-link API.

## G1 — llama.cpp (GGUF)

Runtime: upstream **de32b268c4ad55d45f3b7b16c029f4e077f4ba74** (2026-11-15),
built on-device with CMake/Ninja Release, `BUILD_SHARED_LIBS=ON`,
`GGML_NATIVE=ON`, CPU-only. `libllama.so.1.0.0` 5,033,624 bytes plus ggml
shared libraries installed under `/opt/nuxel-llama/`.

Worker: `services/nuxel-penguru/runtime/llama_cpp/worker.c` — native C against
the pinned headers (the Python ctypes prototype was discarded after it crashed
in `llama_backend_init`; no ABI guessing remains). No TCP listener; one job on
stdin; line-JSON events; SIGTERM sets an abort flag polled by the CPU decode.

CodeBird (`empero-ai/Qwen3.8-4B-Distill-GGUF` @
`391fc7d103e3942a408def3e4f51c2f85d464417`, Q4_K_M):

- Download: 2,783,446,304 bytes; device `sha256sum` =
  `dec96e8cf2e11b613bb46513dec485377f9ca5a351e71712ee0e244f287c6790` (matches
  the manifest).
- Load: `architecture=qwen35`, `n_params=4,326,350,848`, `n_vocab=248,320`,
  `load_ms=618` (cold) / 492–524 ms (warm page cache).
- Generation: prompt 9 tokens -> 40 generated, greedy, 4 threads, ctx 4096:
  **2.610 decode tok/s**; second run: 60 tokens, **2.500 tok/s**,
  peak RSS **2850 MiB** (weights mapped 2572.86 MiB + 257.01 MiB compute
  buffer, as reported by libllama).
- Cancellation: SIGTERM during generation emitted
  `{"event":"cancelled","generated_tokens":1}`, exited 0, no worker process
  remained and free memory returned to baseline.
- Pre-existing lint on the pinned build: token_embd tensors report
  `CPU_REPACK` unavailable and use plain CPU ("using CPU instead"); expected
  on this CPU/quantization combination, not an error.

ChatBird: manifest pinned and verified against HF (`084c0f4e…55b7`,
2,778,282,752 bytes, sha256 `8827d0e2…a3733c`). It is **not installed**: the
download is gated on the provenance/license review recorded in its manifest
(`redistribution: review_required`). Its load/generation self-test will run
when the owner accepts the license record.
