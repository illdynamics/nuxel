#!/bin/bash
# tap.sh X Y | swipe.sh X0 Y0 X1 Y1 [steps]
if [ "$1" = swipe ]; then
  python3 - "$2" "$3" "$4" "$5" "${6:-16}" <<'PY'
import sys, time
sys.path.insert(0, '/Users/wicked/x/nuxel/tools/vnc')
from inject import Touch
x0, y0, x1, y1, n = map(float, sys.argv[1:6])
Touch().swipe(x0, y0, x1, y1, int(n))
PY
else
  python3 - "$1" "$2" <<'PY'
import sys
sys.path.insert(0, '/Users/wicked/x/nuxel/tools/vnc')
from inject import Touch
Touch().tap(int(sys.argv[1]), int(sys.argv[2]))
PY
fi
