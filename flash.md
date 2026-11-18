# Nuxel v0.9.1-beta — safe Wi-Fi userspace deployment (NOT a partition flash)

These commands install only PenGuru/Settings userspace and keep existing kernel, boot images, model files, trust keys and recovery intact. This is **not an OS image flash**. Run from your trusted Mac with the full drop-in repository ZIP extracted. Do not run if device is not responding or SSH identity differs from your known device.

## 0. Preflight and backup

```bash
cd nuxel-main
KEY="$HOME/.ssh/wicked_wqn_id_rsa"    # adjust if your key is elsewhere
HOST=root@10.11.12.99
ssh -i "$KEY" -o StrictHostKeyChecking=ask "$HOST" 'uname -a; cat /etc/os-release | head -6; df -h /var; systemctl status nuxel-penguru --no-pager || true'
ssh -i "$KEY" "$HOST" 'mkdir -p /var/backups/nuxel-penguru; test -d /opt/nuxel-penguru; test -e /usr/lib/nuxel/nuxel-bridge/api.py'
```

The installer already backs up replaced files and records a per-file rollback receipt. Additionally save any current Beak config:

```bash
ssh -i "$KEY" "$HOST" 'test ! -f /var/lib/nuxel-penguru/beak.json || cp -p /var/lib/nuxel-penguru/beak.json /var/backups/nuxel-penguru/beak-before-v091.json'
```

## 1. Package ONLY the userspace files the existing installer consumes

```bash
tar -czf /tmp/nuxel-penguru-v091-userspace.tgz   services/nuxel-penguru   services/nuxel-bridge/src/penguru_api.py   pwa/nuxel-apps/penguru   pwa/nuxel-apps/settings/index.html   pwa/nuxel-apps/settings/penguru-settings.js   pwa/nuxel-apps/settings/penguru-models.js   pwa/nuxel-apps/settings/penguru-beak.js   pwa/nuxel-common/app-registry.json   assets/nuxel-penguru-squad.png
shasum -a 256 /tmp/nuxel-penguru-v091-userspace.tgz
scp -i "$KEY" /tmp/nuxel-penguru-v091-userspace.tgz "$HOST:/tmp/"
```

## 2. Stage and install with rollback support

Only do this when no PenGuru request/download is active. Stopping PenGuru cancels in-flight work.

```bash
ssh -i "$KEY" "$HOST" '
set -eu
mkdir -p /tmp/nuxel-penguru-v091
cd /tmp/nuxel-penguru-v091
tar -xzf /tmp/nuxel-penguru-v091-userspace.tgz
python3 -m compileall -q services/nuxel-penguru
systemctl stop nuxel-penguru-download.service nuxel-penguru.service || true
python3 services/nuxel-penguru/tools/install-device.py --source-root /tmp/nuxel-penguru-v091
systemctl start nuxel-penguru.service
systemctl is-active nuxel-penguru.service
systemctl status nuxel-http-bridge.service --no-pager | head -20
'
```

If the installer fails, it attempts automatic rollback. Otherwise its output names the receipt location for explicit rollback. Do not remove backups until tests pass.

## 3. ONNX Runtime check — SonarBird, NOT GGUF generation

```bash
ssh -i "$KEY" "$HOST" '
/opt/nuxel-penguru-venv/bin/python3 -c "import onnxruntime,tokenizers,numpy; print(onnxruntime.__version__, onnxruntime.get_available_providers())" || true
/opt/nuxel-penguru-venv/bin/python3 -V
ls -l /opt/nuxel-llama/libllama.so /opt/nuxel-penguru/runtime/llama_cpp/penguru-llama-worker 2>/dev/null || true
'
```

If `onnxruntime`/`tokenizers` is missing, install only compatible, verified **Linux aarch64** wheels into the *existing* PenGuru virtualenv after checking Python/glibc versions; do not install `onnxruntime-genai` as a workaround for ChatBird's GGUF. Install instructions on host should use pinned hash-verified wheel builds and on-device self-test. The MiniLM manifest expects `onnxruntime==1.32.0` and the correct tokenizer/runtime parity. The already installed llama.cpp GGUF route uses `Automatic`.

## 4. Owner acceptance tests

1. PenGuru Squad Settings → Generative backend = **Automatic**. Restart PenGuru and refresh; stale ONNX GenAI selection must be cleared.
2. ChatBird: enter Single ChatBird and send a short greeting; verify actual text, not just routing metadata.
3. CodeBird: enter Single CodeBird and request a tiny script; verify actual output.
4. PenGuru Squad AUTO: test CHAT and CODE requests and check route reason. SonarBird MiniLM must show an installed/READY package before claiming inference.
5. PenGuru Squad Settings → Beak: confirm defaults `qwen`, VAD yes, RNNoise requested, talkback yes, Piper. Set one option, open system Settings → PenGuru AI → Beak, verify same value; reverse and verify again.
6. Beak model download: use a source review checkbox. Verify progress and final **STAGED, NOT TRUSTED** receipt, no execution or runtime promotion.
7. Push-to-talk: test only after approved Qwen/Whisper runtime exists. Microphone must stop on navigation, OFF and Stop. Transcription requires review before Send.
8. Continuous foreground wake: explicitly enable, confirm visible mic indicator, test noisy/quiet rooms. Hiding the app must end capture. This is not low-power background wake-word support.
9. Talkback default is ON in config, but playback needs approved Piper binary/voice; test WAV playback only after provision.
10. Check journald and resource use without logging raw prompts. Test device sleep and battery behavior.

## 5. Rollback

If a service regresses, stop PenGuru and roll back using the latest actual receipt printed by the installer:

```bash
ssh -i "$KEY" "$HOST" 'systemctl stop nuxel-penguru-download nuxel-penguru; python3 /tmp/nuxel-penguru-v091/services/nuxel-penguru/tools/rollback-device.py /var/backups/nuxel-penguru/YOUR-RECEIPT/receipt.json; systemctl daemon-reload; systemctl restart nuxel-http-bridge'
```

**No boot partition, TWRP, modem or hardware firmware flash is authorized by this document.** Use existing independently verified flash/recovery workflows if/when a real image update becomes necessary. The release workflow's installed-image provenance checks must never be bypassed.

## Agent handoff

The root `PENGURU_ONE_SHOT_AGENT_V091.md` includes the same Wi-Fi SSH procedure in priority order. The installer is an atomic **userspace** update; these instructions do not perform or authorize a partition flash.
