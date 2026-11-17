#!/bin/sh
set -eu
source_dir=${1:?Usage: build-worker.sh PINNED_LLAMA_SOURCE OUTPUT}
output=${2:?Output worker path required}
expected=de32b268c4ad55d45f3b7b16c029f4e077f4ba74
test "$(git -C "$source_dir" rev-parse HEAD)" = "$expected"
test -z "$(git -C "$source_dir" status --porcelain --untracked-files=no)"
case "$(uname -m)" in aarch64) ;; *) echo 'Build on the ARM64 Nuxel target' >&2; exit 1;; esac
worker_dir=$(CDPATH= cd -- "$(dirname -- "$0")/../runtime/llama_cpp" && pwd)
cc -std=c11 -O2 -Wall -Wextra -Werror \
  -I"$source_dir/include" -I"$source_dir/ggml/include" \
  "$worker_dir/worker.c" -L/opt/nuxel-llama -Wl,-rpath,/opt/nuxel-llama \
  -lllama -o "$output"
readelf -h "$output"
sha256sum "$output"
