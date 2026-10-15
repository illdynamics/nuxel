#!/usr/bin/env bash
# nuxel-live-deploy.sh — atomically deploy a Nuxel userspace binary to the RUNNING phone
# over the CDC-ACM live console.  No flash, no reboot, no TWRP.
#
#   nuxel-live-deploy.sh build/out/s10plus/nuxel-ui            [--to /usr/bin/nuxel-ui]
#                                                            [--restart nuxel-ui]
#
# Framing (mission section 11: never stream a binary through a terminal unverifiably):
#   1. the payload is gzip'd, base64'd and its byte length is counted here;
#   2. the target runs `head -c <exact length> | base64 -d | gzip -dc > <staging>`,
#      so the transfer is bounded by BYTES, not by a terminator the data could forge;
#   3. the target prints sha256sum of the staging file, which must equal the local hash;
#   4. only then is the target path replaced (previous file kept as *.prev), and the
#      service restarted.
set -euo pipefail
LOCAL=""; TO=""; RESTART=""
while [ $# -gt 0 ]; do
  case "$1" in
    --to) TO="$2"; shift 2 ;;
    --restart) RESTART="$2"; shift 2 ;;
    --dev) DEV="$2"; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) LOCAL="$1"; shift ;;
  esac
done
[ -n "$LOCAL" ] || { echo "usage: $0 <binary> [--to /usr/bin/x] [--restart unit]" >&2; exit 2; }
[ -f "$LOCAL" ] || { echo "missing $LOCAL" >&2; exit 2; }
[ -n "$TO" ] || TO="/usr/bin/$(basename "$LOCAL")"
DEV="${DEV:-$(ls -1 /dev/cu.usbmodem* 2>/dev/null | head -1)}"
[ -n "$DEV" ] || { echo "no /dev/cu.usbmodem*" >&2; exit 1; }
echo "# target $DEV -> $TO"
exec python3 - "$DEV" "$LOCAL" "$TO" "$RESTART" <<'PYEOF'
import base64,gzip,hashlib,os,re,sys,termios,time,select
dev,local,to,restart=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
raw=open(local,'rb').read()
sha=hashlib.sha256(raw).hexdigest()
payload=base64.b64encode(gzip.compress(raw,9))
payload+=b"\n"
fd=os.open(dev,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
a=termios.tcgetattr(fd); a[0]=0;a[1]=0
a[2]=termios.CS8|termios.CREAD|termios.CLOCAL;a[3]=0;a[4]=9600;a[5]=9600
termios.tcsetattr(fd,termios.TCSANOW,a); termios.tcflush(fd,termios.TCIOFLUSH)
def pump(secs):
    out=b""; t0=time.time()
    while time.time()-t0<secs:
        r,_,_=select.select([fd],[],[],0.05)
        if r:
            try: c=os.read(fd,65536)
            except OSError: return out
            if c: out+=c
    return out
def send(line,wait=3.0):
    os.write(fd,line.encode()+b"\r"); return pump(wait)
staging="/var/lib/nuxel/deploy.tmp"
print(f"# local {len(raw)} bytes sha256 {sha}")
print(f"# framed payload {len(payload)} base64 bytes")
pump(0.8)
send("echo DEPLOY_BEGIN",1.0)
# exact-length framed transfer
cmd=f"head -c {len(payload)} | base64 -d | gzip -dc > {staging}; echo DEPLOY_RC=$?; sha256sum {staging}"
os.write(fd,cmd.encode()+b"\r")
time.sleep(0.6)
os.write(fd,payload)
out=pump(6.0)
txt=out.decode('utf-8','replace')
m=re.search(r'([0-9a-f]{64})\s+\S*deploy\.tmp',txt)
got=m.group(1) if m else "(no hash seen)"
print(f"# target staging sha256 {got}")
if got!=sha:
    print("# VERIFY FAILED - staging file NOT installed"); print(txt[-1200:]); sys.exit(1)
print("# VERIFY OK - installing atomically")
cmds=[f"cp -f {to} {to}.prev 2>/dev/null; echo prev_kept=$?",
      f"install -m 0755 {staging} {to} && echo INSTALLED || echo INSTALL_FAILED",
      f"sha256sum {to}"]
for c in cmds:
    t=send(c,2.5).decode('utf-8','replace')
    print("   "+" | ".join(l.strip() for l in t.splitlines() if l.strip() and not re.match(r'^\s*\d+,\d+,\d+,-[;[]',l))[:200])
if restart:
    t=send(f"systemctl restart {restart}; sleep 2; systemctl is-active {restart}",5.0).decode('utf-8','replace')
    print("   restart: "+" | ".join(l.strip() for l in t.splitlines() if l.strip() and not re.match(r'^\s*\d+,\d+,\d+,-[;[]',l))[:200])
print("# DEPLOY COMPLETE")
PYEOF
