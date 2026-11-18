#!/usr/bin/env python3
"""Explicit, non-promoting test of an installed model; never writes READY state."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, '/opt/nuxel-penguru')
from common import paths
from common.registry import ModelRegistry, STATUS_READY, STATUS_VERIFIED_SIGNED
from common.runtime_api import RuntimeProfile
from runtime.llama_cpp.adapter import LlamaCppRuntime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model_id', choices=['chatbird', 'codebird'])
    parser.add_argument('--test-signature', action='store_true', help='Accept the already installed test key for this isolated test only')
    args = parser.parse_args()
    registry = ModelRegistry(paths.MANIFESTS_DIR, paths.MODELS_DIR,
                            trusted_key=paths.MANIFEST_PUBKEY,
                            allow_test_keys=args.test_signature)
    manifest = next(item for item in registry.manifests() if item['model_id'] == args.model_id)
    state = registry.verify_installed(manifest)
    if state.status not in (STATUS_VERIFIED_SIGNED, STATUS_READY):
        raise SystemExit('Refused: ' + state.detail)
    runtime = LlamaCppRuntime(paths.LLAMA_LIB, runner=False)
    result = runtime.self_test(manifest, registry.package_dir(manifest),
        RuntimeProfile(engine='llama.cpp', package_format='GGUF', threads=4, context_limit=4096),
        prompt='Reply with the word READY.', max_tokens=16)
    architecture = (result.get('loaded') or {}).get('architecture')
    success = result.get('result') == 'pass' and architecture == manifest['architecture'] and bool(result.get('output'))
    print(json.dumps({'test_passed': success, 'production_activated': False,
        'trust_scope': manifest.get('trust'), 'architecture': architecture,
        'revision': manifest['source_revision'], 'loaded': result.get('loaded'),
        'done': result.get('done'), 'error': result.get('code'), 'detail': result.get('detail'),
        'output_characters': len(result.get('output', '')),
        'output_sha256': hashlib.sha256(result.get('output', '').encode()).hexdigest()}))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
