# PenGuru on native Nuxel

This is a partially implemented, local-first subsystem, not a completed
dual-runtime/voice product. The application and Settings panel use the real
launcher-authenticated bridge. No cloud inference is configured. Services are
OFF by default and are not enabled at boot by the installer.

## Install and test

The installer runs **on the handset as root**, with a staged repository tree:

```sh
sh services/nuxel-penguru/tools/build-worker.sh \
  /root/penguru-build/llama.cpp /tmp/penguru-llama-worker
python3 services/nuxel-penguru/tools/install-device.py \
  --source-root "$PWD" --worker /tmp/penguru-llama-worker
python3 services/nuxel-penguru/tools/device-api-check.py
```

Prerequisites: Python with `cryptography`, systemd, C compiler, binutils,
the existing Nuxel HTTP bridge and PWA installation, and matching ARM64
llama.cpp libraries in `/opt/nuxel-llama`. The build rejects a wrong revision
or tracked modifications to the upstream checkout. Pinned llama.cpp revision:
`de32b268c4ad55d45f3b7b16c029f4e077f4ba74`.

To reproduce the libraries in a fresh ARM64 environment, check out that exact
revision from `ggml-org/llama.cpp`, configure a separate build directory using
`cmake -S . -B build -DBUILD_SHARED_LIBS=ON -DGGML_CUDA=OFF
-DGGML_VULKAN=OFF -DLLAMA_BUILD_TESTS=OFF`, then build the `llama` target.
This turn rebuilt the worker against the **existing** matching device libraries;
a clean rebuild of the libraries is not claimed.

The staged tree must include `services/nuxel-penguru`,
`services/nuxel-bridge/src/penguru_api.py`, `pwa/nuxel-apps/penguru`,
the Settings HTML and `penguru-*.js` files, the common app registry, and
`assets/nuxel-penguru-squad.png`. Keep model weights and private signing keys
out of this tree/archive and Git. Never overwrite the device's public trust
key merely to make an installation pass.

The installer merges only the PenGuru registry entry, Settings tab/section,
and bridge route. It preserves unrelated live changes, existing signed
manifests, models and trust keys. It restarts the HTTP bridge (existing app
tokens must be refreshed), but not SSH, networking, the display session or
the handset. Close and reopen Settings/home after installation to load the
new assets. The application is named **PenGuru Squad**; the Settings tab is
**PenGuru AI**.

Each installation prints a receipt under `/var/backups/nuxel-penguru/`.
The installer automatically restores files if it fails. For a later rollback:

```sh
python3 services/nuxel-penguru/tools/rollback-device.py \
  /var/backups/nuxel-penguru/TIMESTAMP/receipt.json
```

Restore newest receipts first. Rollback refuses post-install file edits and
does not remove model data, trust keys or the service account. Receipts before
the ownership-metadata update do not record original owner IDs. An automatic
early-install rollback was exercised; later manual rollback is supplied but
has not been exercised on the final installation.

## Trust and downloads

The two repository GGUF manifests are **unsigned**. The handset also has an
older test-signed CodeBird manifest and downloaded model. Neither is a
production-ready release package. Both model menus display immutable revisions,
sizes, hashes, license notices, and the exact trust failure. Download buttons
remain disabled for untrusted packages; checking a license box is not a trust
bypass. A trusted signed manifest enables the existing download path, which
requires exact-revision license acknowledgement and a real runtime self-test
before READY. This turn did not download multi-gigabyte models or accept a
model license for the owner.

Only an explicitly isolated engineering test may opt into the already installed
test key with `device-runtime-check.py codebird --test-signature`. The check
hashes the package, verifies the signature, loads it and generates tokens. It
does not install a trust key, alter production configuration, write a READY
record, or promote test artifacts. Run it unprivileged with a bounded transient
systemd unit, as recorded in `reports/PENGURU-DEVICE-INTEGRATION-2026-11-17.md`.

## Local checks

```sh
python3 services/nuxel-penguru/tests/test_registry.py
python3 services/nuxel-penguru/tests/test_routing.py
python3 services/nuxel-penguru/tests/test_installation.py
python3 services/nuxel-penguru/tests/test_worker_protocol.py
python3 -m compileall -q services/nuxel-penguru
node --check pwa/nuxel-apps/penguru/penguru.js
node --check pwa/nuxel-apps/settings/penguru-settings.js
node --check pwa/nuxel-apps/settings/penguru-models.js
node pwa/nuxel-common/verify-wiring.js
```

The worker emits response text only in escaped token events. Completion events
carry metadata, not duplicated unescaped text. Malformed worker JSON, abnormal
exits and the 180-second watchdog are explicit errors. Diagnostic stderr is
drained into a bounded 64-KiB tail instead of retained without limit. The worker
checks that creating an Internet socket is denied before loading a model.

## Not implemented or not accepted

- Production-trusted model release and successful owner-driven download UI test.
- ChatBird generation on this handset.
- ONNX Runtime GenAI adapter and compatible exported model packages.
- Approved SonarBird encoder/classifier bundle; only deterministic routing works.
- Microphone capture, local STT, tested Penguru wake-phrase model and native overlay.
- Privileged writes, approvals/rollback broker, and generated-code execution.
- Full conversation quality, soak, thermal, suspend/resume and physical UI acceptance.

These remain visibly unavailable. A successful CodeBird test does not imply
completion of those features or acceptance of the full kickstart specification.
