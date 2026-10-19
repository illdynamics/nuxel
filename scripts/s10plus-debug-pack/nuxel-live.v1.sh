#!/usr/bin/env bash
# nuxel-live.sh — run commands on the RUNNING Nuxel phone over the CDC-ACM live console.
#
#   nuxel-live.sh --run 'systemctl status nuxel-ui | head -20'
#   nuxel-live.sh --batch file.txt          # one command per line
#   nuxel-live.sh --watch                   # just stream the console
#   nuxel-live.sh --dev /dev/cu.usbmodem201 ...
#
# WHY A WRAPPER AND NOT `screen`: the console carries BOTH an interactive shell and a
# live mirror of the target's /dev/kmsg.  The kernel telemetry (battery, touch, SSP) is
# a constant byte flood, so a reader that sleeps while waiting *loses* the command's
# output to buffer pressure.  This wrapper therefore drains the port CONTINUOUSLY while
# it waits and only then extracts the answer between the @@B@@/@@rc marker pair.
set -euo pipefail
PY=${PY:-python3}
DEV=""; MODE=""; CMD=""; FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dev) DEV="$2"; shift 2 ;;
    --run) MODE=run; CMD="$2"; shift 2 ;;
    --batch) MODE=batch; FILE="$2"; shift 2 ;;
    --watch) MODE=watch; shift ;;
    --wait) WAIT="$2"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$DEV" ] || DEV=$(ls -1 /dev/cu.usbmodem* 2>/dev/null | head -1)
[ -n "$DEV" ] || { echo "no /dev/cu.usbmodem* — is the phone running Nuxel?" >&2; exit 1; }
echo "# console $DEV"
exec "$PY" - "$DEV" "$MODE" "${CMD:-}" "${FILE:-}" "${WAIT:-3}" <<'PYEOF'
import os,re,sys,termios,time,select
dev,mode,cmd,path,wait=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],float(sys.argv[5])
fd=os.open(dev,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
a=termios.tcgetattr(fd); a[0]=0; a[1]=0
a[2]=termios.CS8|termios.CREAD|termios.CLOCAL; a[3]=0; a[4]=9600; a[5]=9600
termios.tcsetattr(fd,termios.TCSANOW,a); termios.tcflush(fd,termios.TCIOFLUSH)
KMSG=re.compile(r'^\s*\d+,\d+,\d+,-[;[]')
def looks_kmsg(l):
    s=l.strip()
    if KMSG.match(l): return True
    if s.startswith(('SUBSYSTEM=','DEVICE=','ACTION=','SEQNUM=','DEVPATH=','MAJOR=','MINOR=','DEVNAME=','DEVTYPE=','MODALIAS=')): return True
    return False
def pump(secs,sink):
    t0=time.time()
    while time.time()-t0<secs:
        r,_,_=select.select([fd],[],[],0.05)
        if r:
            try: c=os.read(fd,65536)
            except OSError: return
            if c: sink.append(c)
def clean(txt):
    keep=[]
    for l in txt.splitlines():
        if not l.strip(): continue
        if looks_kmsg(l): continue
        keep.append(l.rstrip())
    return keep
if mode=='watch':
    while True:
        b=[]; pump(0.5,b)
        sys.stdout.write(b"".join(b).decode('utf-8','replace')); sys.stdout.flush()
    sys.exit(0)
cmds=[cmd] if mode=='run' else [l.rstrip('\n') for l in open(path) if l.strip() and not l.startswith('#')]
pump(0.8,[])
for c in cmds:
    buf=[]
    os.write(fd,b"echo @@B@@\r"); pump(0.5,buf); buf.clear()
    os.write(fd,c.encode()+b"\r"); pump(wait,buf)
    os.write(fd,b"echo @@rc=$?@@\r"); pump(1.5,buf)
    txt=b"".join(buf).decode('utf-8','replace')
    if '@@B@@' in txt: txt=txt.split('@@B@@',1)[1]
    rc=''
    m=re.search(r'@@rc=(\d+)@@',txt)
    if m: rc=m.group(1); txt=txt[:m.start()]
    # drop the echoed command line itself
    lines=clean(txt)
    if lines and lines[0].strip().rstrip()==c.strip(): lines=lines[1:]
    print(f"===== {c}   [rc={rc or '?'}]")
    for l in lines[:80]: print('   ',l)
    sys.stdout.flush()
PYEOF
