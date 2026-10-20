#!/usr/bin/env python3
"""HTTP/MIME/SHA verification of every registered icon on the live phone."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/beta/live"))
import nuxel_live as nl  # noqa: E402

REMOTE = r'''
import hashlib, json, urllib.request, urllib.error
REG='/usr/share/nuxel/nuxel-home/icon-registry.json'
BASE='http://127.0.0.1:8000'
reg=json.load(open(REG))
out={'registry':REG,'registry_sha256':hashlib.sha256(open(REG,'rb').read()).hexdigest(),
     'base':BASE,'assets':[],'failures':[]}
def get(url):
    req=urllib.request.Request(url,headers={'Cache-Control':'no-store'})
    try:
        r=urllib.request.urlopen(req,timeout=10)
        return r.status,r.headers.get('Content-Type','').split(';')[0].strip(),r.read()
    except urllib.error.HTTPError as e:
        return e.code,e.headers.get('Content-Type','').split(';')[0].strip(),e.read()
for a in reg['assets']:
    status,ctype,body=get(BASE+a['url'])
    dep='/usr/share/nuxel/'+a['source']
    try: depdata=open(dep,'rb').read()
    except OSError: depdata=b''
    rec={'id':a['id'],'kind':a['kind'],'url':a['url'],'status':status,'mime':ctype,
         'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),
         'expected_bytes':a['bytes'],'expected_sha256':a['sha256'],
         'deployed_sha256':hashlib.sha256(depdata).hexdigest() if depdata else None}
    rec['ok']=(status==200 and ctype=='image/png' and rec['bytes']==a['bytes']
               and rec['sha256']==a['sha256'] and rec['deployed_sha256']==a['sha256'])
    if not rec['ok']: out['failures'].append(rec)
    out['assets'].append(rec)
# Negative: absent and wrong-case URLs must not be served.
s,ct,_=get(BASE+'/assets/nuxel-applications-icon-pack/a44-does-not-exist.png')
out['missing_status']=s
a0=reg['assets'][0]
s2,_,_=get(BASE+a0['path'].replace('/assets/','/ASSETS/'))
out['wrong_case_status']=s2
if s!=404: out['failures'].append({'negative':'missing','status':s})
if s2!=404: out['failures'].append({'negative':'wrong-case','status':s2})
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if not out['failures'] else 1)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="/dev/ttyACM0")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--lock-wait", type=float, default=30)
    args = ap.parse_args()
    out_path = Path(args.json_out) if args.json_out else ROOT / "docs/live/v0.6.3-beta-20261020-a44/http-icons.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with nl.Console(args.dev, timeout=35, lock_wait=args.lock_wait) as c:
        probe = c.probe(6.0)
        if not probe.reachable:
            raise SystemExit("console byte-silent")
        nl.push_bytes(c, REMOTE.encode(), "/var/tmp/nuxel-a44-verify-icons.py", mode="0755")
        r = c.run("python3 /var/tmp/nuxel-a44-verify-icons.py", timeout=120)
        text = r.output.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            raise SystemExit("remote verifier produced no JSON: " + text[-1000:])
        data = json.loads(text[start:end])
        data["console_frame_ok"] = r.ok
        data["console_rc"] = r.rc
        out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"json": str(out_path), "assets": len(data.get("assets", [])),
                          "failures": len(data.get("failures", [])),
                          "missing_status": data.get("missing_status"),
                          "wrong_case_status": data.get("wrong_case_status"),
                          "frame_ok": r.ok, "rc": r.rc}, indent=2))
        return 0 if r.ok and r.rc == 0 and not data.get("failures") else 1


if __name__ == "__main__":
    sys.exit(main())
