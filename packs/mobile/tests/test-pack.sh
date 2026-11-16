#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
make -C "$ROOT/tools" clean all test
python3 "$ROOT/tools/acquire-s10plus-modem-evidence.py" --help >/dev/null
PACK_ROOT="$ROOT" python3 - <<'PY'
import importlib.util
import os
from pathlib import Path
p = Path(os.environ['PACK_ROOT']) / 'tools' / 'acquire-s10plus-modem-evidence.py'
spec = importlib.util.spec_from_file_location('collector', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sample = 'IMSI: 310150123456789\nICCID=8901234567890123456\nIMEI 123456789012345'
redacted = m.redact(sample)
for secret in ('310150123456789', '8901234567890123456', '123456789012345'):
    assert secret not in redacted
assert redacted.count('[REDACTED]') == 3
print('PASS: identifier redaction')
PY
PACK_ROOT="$ROOT" python3 - <<'PY'
import os
from pathlib import Path
root = Path(os.environ['PACK_ROOT'])
h = (root / 'tools' / 's5000ap_uapi.h').read_text()
c = (root / 'tools' / 's5000ap-status.c').read_text()
assert "_IO('o', 0x27)" in h
assert 'O_RDONLY' in c and 'NUXEL_IOCTL_MODEM_STATUS' in c
for forbidden in ('MODEM_ON', 'MODEM_OFF', 'MODEM_RESET', 'FW_UPDATE', 'BOOT_ON', 'BOOT_DONE', 'DUMP_START'):
    assert forbidden not in h
assert 'O_WRONLY' not in c and 'O_RDWR' not in c
print('PASS: read-only ioctl surface')
PY
