#!/usr/bin/env python3
import os

STATE_DIR = os.environ.get("NUXEL_PENGURU_STATE", "/var/lib/nuxel-penguru")
MODELS_DIR = os.path.join(STATE_DIR, "models")
QUEUE_DB = os.environ.get("NUXEL_PENGURU_QUEUE", os.path.join(STATE_DIR, "queue.db"))
MANIFESTS_DIR = os.environ.get("NUXEL_PENGURU_MANIFESTS",
                               "/usr/share/nuxel-penguru/manifests")
CONFIG_DIR = os.environ.get("NUXEL_PENGURU_CONFIG_DIR", "/etc/nuxel/penguru")
CONFIG_PATH = os.path.join(CONFIG_DIR, "penguru.toml")
MANIFEST_PUBKEY = os.environ.get("NUXEL_PENGURU_MANIFEST_KEY",
                                 "/etc/nuxel/penguru/manifest-pubkey.pem")
ALLOW_TEST_KEYS = os.environ.get("NUXEL_PENGURU_ALLOW_TEST_KEYS", "0") == "1"
LLAMA_WORKER = os.environ.get("NUXEL_LLAMA_WORKER",
                              "/opt/nuxel-penguru/runtime/llama_cpp/penguru-llama-worker")
LLAMA_LIB = os.environ.get("NUXEL_LLAMA_LIB", "/opt/nuxel-llama/libllama.so")
PACKAGE_BIN_DIR = "/var/lib/nuxel-penguru/bin"
DOWNLOAD_ROOT = os.path.join(STATE_DIR, "downloads")
