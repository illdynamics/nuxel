#!/bin/sh
# Native ARM64 build from an immutable upstream revision, no model weights.
set -eu
output=${1:?Usage: build-runtime.sh OUTPUT_DIRECTORY}
source_dir=${2:?Source checkout directory required}
revision=de32b268c4ad55d45f3b7b16c029f4e077f4ba74
if [ ! -d "$source_dir/.git" ]; then
    git init "$source_dir"
    git -C "$source_dir" remote add origin https://github.com/ggml-org/llama.cpp.git
    git -C "$source_dir" fetch --depth 1 origin "$revision"
    git -C "$source_dir" checkout --detach FETCH_HEAD
fi
test "$(git -C "$source_dir" rev-parse HEAD)" = "$revision"
test -z "$(git -C "$source_dir" status --porcelain --untracked-files=no)"
cmake -S "$source_dir" -B "$source_dir/build" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
    -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8-a \
    -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_OPENMP=OFF \
    -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF
cmake --build "$source_dir/build" --target llama -j "${NUXEL_BUILD_JOBS:-2}"
mkdir -p "$output"
cp -a "$source_dir/build/bin/"*.so* "$output/"
worker_dir=$(CDPATH= cd -- "$(dirname -- "$0")/../runtime/llama_cpp" && pwd)
cc -std=c11 -O2 -Wall -Wextra -Werror \
    -I"$source_dir/include" -I"$source_dir/ggml/include" \
    "$worker_dir/worker.c" -L"$output" -Wl,-rpath,/opt/nuxel-llama \
    -lllama -o "$output/penguru-llama-worker"
printf '%s\n' "$revision" > "$output/SOURCE_REVISION"
(cd "$output" && sha256sum *.so* penguru-llama-worker > SHA256SUMS)
