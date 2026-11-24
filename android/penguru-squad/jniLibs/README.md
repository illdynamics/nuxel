# Bundled Whisper speech engine

`libwhisper-cli.so` is the whisper.cpp `whisper-cli` executable packaged under a
native-library name so Android extracts it into the read-only
`nativeLibraryDir`. Executing binaries from writable app data is blocked on
Android 10+, while the extracted native-library directory is executable.

- Source: <https://github.com/ggml-org/whisper.cpp> tag `v1.9.6`
- License: MIT (see `WHISPER_CPP_LICENSE.txt`)
- ABIs: `arm64-v8a`, `x86_64`
- NDK: r27c (`27.2.12479018`), `android-26`, `c++_static`
- Build: `BUILD_SHARED_LIBS=OFF`, `GGML_OPENMP=OFF`, `GGML_NATIVE=OFF`,
  `GGML_BACKEND_DL=OFF`, stripped with `llvm-strip --strip-unneeded`
- SHA-256:
  - `arm64-v8a`: `3c4b8f8c83a57a29f3408a9289e7abab93ee6113b7226531c5d19903e2a28a7b`
  - `x86_64`: `9e0f774521d5bc117e85435d9778d7c74df8ab25e73af082ea51bb1c3216b0c0`

The `ggml-tiny.en.bin` model is not bundled. It is downloaded from the pinned
`ggerganov/whisper.cpp` revision through the Model library, verified by SHA-256,
and used only on the handset.
