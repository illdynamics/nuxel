#!/usr/bin/env python3
"""Nuxel S10+ UI acceptance helper (root console; verification only).

Subcommands
-----------
  snap OUT.png                 capture the live Phoc screen (grim) to the host
  tap X Y                      trusted tap (host `test-tap`, CSS pixels)
  probe EXPR                   evaluate a restricted read-only expression in the
                               launcher and print the JSON result
  kill-lock                    ask the bridge to lock the device

`probe` is answered by the launcher's `ui-probe` control-FIFO action, which
only accepts property paths and simple calls (no eval/fetch/assignments).
This tool never ships in the OS image; it is how the acceptance matrix drives
the phone without a finger on the glass.
"""
import json
import subprocess
import sys
import time

KEY = "/Users/wicked/.ssh/wicked_wqn_id_rsa"
HOST = "root@192.168.178.167"


def ssh(cmd, **kw):
    return subprocess.run(["ssh", "-i", KEY, HOST, cmd], capture_output=True,
                          text=True, **kw).stdout


def snap(out):
    ssh("export XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0; "
        "grim -t png /tmp/nuxel-ui.png")
    subprocess.run(["scp", "-q", "-i", KEY, HOST + ":/tmp/nuxel-ui.png", out], check=True)
    print("saved", out)


def host_action(action):
    ssh("printf '%s\\n' " + shq(action) + " > /run/nuxel-pwa-host.cmd")


def shq(s):
    return '"' + s.replace('"', '\\"') + '"'


def tap(x, y):
    host_action("action test-tap %d %d" % (int(x), int(y)))
    time.sleep(0.35)


def probe(expr):
    before = int(ssh("wc -l < /run/nuxel-home.state").strip() or 0)
    host_action("action ui-probe " + expr)
    time.sleep(1.0)
    out = ssh("tail -n +%d /run/nuxel-home.state | grep -a 'A80_PROBE '" % (before + 1))
    for line in out.splitlines():
        i = line.find("A80_PROBE ")
        if i >= 0:
            body = line[i + len("A80_PROBE "):]
            try:
                print(json.dumps(json.loads(body), indent=1))
                return 0
            except ValueError:
                print(body)
                return 0
    print("NO_RESULT")
    return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "snap":
        snap(args[0])
    elif cmd == "tap":
        tap(args[0], args[1])
    elif cmd == "probe":
        return probe(" ".join(args))
    elif cmd == "kill-lock":
        ssh("curl -s -X POST http://127.0.0.1:8080/api/v1/rpc -H 'Content-Type: application/json' "
            "-H 'X-Nuxel-Bridge-Version: 1' -d '{\"app_id\":\"org.nuxel.Home\","
            "\"namespace\":\"security\",\"verb\":\"lock\",\"params\":{}}'")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
