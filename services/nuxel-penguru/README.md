# PenGuru on native Nuxel

This is a partially implemented, local-first subsystem, not a completed
dual-runtime/voice product. The PenGuru Squad app uses the real
launcher-authenticated bridge. Model downloads, runtime selection, voice and
connection settings now live inside the app; the legacy Settings panel is
removed on install. No cloud inference is configured. Services are
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
`services/nuxel-bridge/src/penguru_api.py`, `pwa/nuxel-apps/penguru`
(including `model-library.js`), the Settings HTML, the common app registry, and
`assets/nuxel-penguru-squad.png`. Keep model weights and private signing keys
out of this tree/archive and Git. Never overwrite the device's public trust
key merely to make an installation pass.

The installer merges only the PenGuru registry entry and bridge route, and it
removes the legacy Settings PenGuru tab/section when upgrading an older device.
It preserves unrelated live changes, existing signed manifests, models and
trust keys. It restarts the HTTP bridge (existing app
tokens must be refreshed), but not SSH, networking, the display session or
the handset. Close and reopen Settings/home after installation to load the
new assets. The application is named **PenGuru Squad** and is self-contained.

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

Both immutable GGUF manifests are owner-release signed. The public key is in
`keys/owner-release-public.pem`; the private key lives outside this repository.
The handset's previous test key and manifests were preserved under
`/var/backups/nuxel-penguru/owner-trust-20261117/` before explicit enrollment.

Download buttons require the owner to acknowledge the exact revision's notice.
A pre-existing package can be reused only after hash/signature verification;
its license record is written on that foreground action, and a fresh runtime
self-test must bind to the signed manifest before READY. Legacy test records
cannot silently promote packages. ChatBird's upstream license provenance remains
unresolved; no model weights are redistributed in the release.

`tools/provision-owner-key.py PRIVATE_PATH PUBLIC_PATH` creates or reuses an
Ed25519 key without overwriting a different key. `tools/sign-manifest.py` signs
metadata. Enrollment is a separate owner-authorized operation. The installer
continues to preserve existing handset trust and manifests.

## Local checks

```sh
python3 services/nuxel-penguru/tests/test_registry.py
python3 services/nuxel-penguru/tests/test_routing.py
python3 services/nuxel-penguru/tests/test_installation.py
python3 services/nuxel-penguru/tests/test_worker_protocol.py
python3 -m compileall -q services/nuxel-penguru
node --check pwa/nuxel-apps/penguru/penguru.js
node --check pwa/nuxel-apps/penguru/model-library.js
node pwa/nuxel-common/verify-wiring.js
```

The worker emits response text only in escaped token events. Completion events
carry metadata, not duplicated unescaped text. Malformed worker JSON, abnormal
exits and the 180-second watchdog are explicit errors. Diagnostic stderr is
drained into a bounded 64-KiB tail instead of retained without limit. The worker
checks that creating an Internet socket is denied before loading a model.

## Not implemented or not accepted

- Owner-driven multi-gigabyte download UI acceptance.
- ChatBird generation on this handset.
- ONNX Runtime GenAI adapter and compatible exported model packages.
- Broader SonarBird dataset and physical acceptance beyond the initial synthetic-family evaluation.
- Physically accepted microphone capture, wake-phrase accuracy and a native always-on overlay; foreground button/wake controls remain beta.
- Privileged writes, approvals/rollback broker, and generated-code execution.
- Full conversation quality, soak, thermal, suspend/resume and physical UI acceptance.

These remain visibly unavailable. A successful CodeBird test does not imply
completion of those features or acceptance of the full kickstart specification.
