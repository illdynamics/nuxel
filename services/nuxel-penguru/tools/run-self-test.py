#!/usr/bin/env python3
"""Run the real llama.cpp self-test for an installed package and record it.

Writes <package>/self-test.json ONLY after the worker loaded the model and
generated tokens.  A failure writes a fail record; it never writes pass.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SVC = os.path.dirname(HERE)
sys.path.insert(0, SVC)

from common import paths, registry as reg  # noqa: E402
from common.runtime_api import RuntimeProfile  # noqa: E402
from runtime.llama_cpp.adapter import LlamaCppRuntime  # noqa: E402


def main(model_id, variant_id, prompt="Reply with the single word READY."):
    r = reg.ModelRegistry(paths.MANIFESTS_DIR, paths.MODELS_DIR,
                          trusted_key=paths.MANIFEST_PUBKEY,
                          allow_test_keys=paths.ALLOW_TEST_KEYS)
    m = next((x for x in r.manifests() if x["model_id"] == model_id
              and x["variant_id"] == variant_id), None)
    if m is None:
        print("unknown package")
        return 2
    pkg = r.package_dir(m)
    rt = LlamaCppRuntime(paths.LLAMA_LIB, runner=False)
    prof = RuntimeProfile(engine="llama.cpp", package_format="GGUF",
                          threads=int(os.environ.get("NUXEL_PENGURU_THREADS", "4")),
                          context_limit=int(m["runtime"].get("context_limit", 4096)),
                          memory_budget_bytes=0)
    res = rt.self_test(m, pkg, prof, prompt=prompt, max_tokens=16)
    rec = {"result": res.get("result"), "engine": "llama.cpp",
           "version": "de32b268c4ad55d45f3b7b16c029f4e077f4ba74",
           "at": time.time(), "load_ms": (res.get("loaded") or {}).get("load_ms"),
           "prompt": prompt,
           "output_sha256": __import__("hashlib").sha256(
               (res.get("output") or "").encode()).hexdigest()}
    with open(os.path.join(pkg, "self-test.json"), "w") as fh:
        json.dump(rec, fh, indent=2)
    print(json.dumps(rec))
    return 0 if rec["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
