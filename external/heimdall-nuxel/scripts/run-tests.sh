#!/usr/bin/env bash
# Build and run the mocked end-session unit tests against the patched source.
#
# No device, no libusb, no root required. Exit code 0 == all classifications
# behave as documented.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

SRC="${NUXEL_HEIMDALL_SRC}/heimdall/source"
TESTS="${NUXEL_HEIMDALL_DIR}/tests"
CXX="${CXX:-c++}"

[ -d "${SRC}" ] || { err "patched source not found; run build-and-test.sh first"; exit 1; }

mkdir -p "${NUXEL_HEIMDALL_LOGS}" "${NUXEL_HEIMDALL_OUT}"

compile_and_run() {
    local name="$1"; shift
    local out="${NUXEL_HEIMDALL_OUT}/nuxel-session-tests-${name}"
    local log="${NUXEL_HEIMDALL_LOGS}/session-tests-${name}.log"

    log "compiling tests (${name}) with ${CXX}"
    if ! "${CXX}" -std=c++17 -Wall -Wextra -Werror "$@" \
            -I"${SRC}" -o "${out}" \
            "${TESTS}/test_session_handshake.cpp" "${SRC}/NuxelSession.cpp" >"${log}" 2>&1; then
        err "compilation failed (${name}); see ${log}"
        tail -20 "${log}" >&2
        return 1
    fi

    log "running tests (${name})"
    if ! "${out}" 2>&1 | tee -a "${log}" | sed 's/^/    /'; then
        err "tests failed (${name}); see ${log}"
        return 1
    fi
    return 0
}

status=0
compile_and_run plain -O1 || status=1

# AddressSanitizer/UndefinedBehaviorSanitizer are available on clang and gcc;
# treat a sanitizer failure as a test failure but do not fail merely because a
# platform lacks the runtime.
if "${CXX}" -std=c++17 -fsanitize=address,undefined -x c++ - -o /dev/null >/dev/null 2>&1 <<<'int main(){return 0;}'; then
    compile_and_run sanitized -g -O1 -fsanitize=address,undefined || status=1
else
    log "sanitizers unavailable on this toolchain; skipped"
fi

exit "${status}"
