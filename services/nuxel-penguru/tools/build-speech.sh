#!/bin/sh
set -eu
out=${1:?output directory}; src=${2:?source checkout}
revision=5f9823760117f500ebce2527cbb2314572f5fcd6
if [ ! -d "$src/.git" ]; then
 git init "$src"
 git -C "$src" remote add origin https://github.com/ggml-org/whisper.cpp.git
 git -C "$src" fetch --depth 1 origin "$revision"
 git -C "$src" checkout --detach FETCH_HEAD
fi
test "$(git -C "$src" rev-parse HEAD)" = "$revision"
test -z "$(git -C "$src" status --porcelain --untracked-files=no)"
cmake -S "$src" -B "$src/build" -DCMAKE_BUILD_TYPE=Release \
 -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8-a \
 -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_OPENMP=OFF -DWHISPER_BUILD_TESTS=OFF
cmake --build "$src/build" --target whisper-cli -j "${NUXEL_BUILD_JOBS:-2}"
mkdir -p "$out"
cp "$src/build/bin/whisper-cli" "$out/whisper-cli"
printf '%s\n' "$revision" > "$out/SOURCE_REVISION"
