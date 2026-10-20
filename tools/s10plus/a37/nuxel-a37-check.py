#!/usr/bin/env python3
"""A37 read-only brand/audio deployment audit; does NOT prove audible speaker output."""
import argparse, hashlib, json, os, pathlib, subprocess, sys, urllib.request, urllib.error
P=argparse.ArgumentParser();P.add_argument('--root',default='/usr/share/nuxel');P.add_argument('--url',default='http://127.0.0.1:8000');P.add_argument('--offline',action='store_true');A=P.parse_args()
root=pathlib.Path(A.root);urls=['assets/button-left.png','assets/button-middle.png','assets/button-right.png','assets/nuxel-applications-icon-pack/01-01_terminal.png','assets/nuxel-quicksettings-icon-pack/01-wifi.png']
urls += ['pwa/nuxel-home/'+p for p in ('index.html','js/apps.js','sw.js','js/touch-keyboard.js','js/qs.js')]
failures=0
for name in urls:
    path=root/name
    valid=path.is_file() and path.stat().st_size>100
    digest=hashlib.sha256(path.read_bytes()).hexdigest() if valid else None
    code='OFFLINE';remote_ok=True
    if not A.offline:
        try:
            with urllib.request.urlopen(A.url+'/'+name,timeout=4) as r:
                data=r.read();code=r.status
                remote_ok=code==200 and hashlib.sha256(data).hexdigest()==digest
        except Exception as e:code=str(e);remote_ok=False
    ok=valid and remote_ok
    failures += not ok
    print(json.dumps({'path':name,'exists':valid,'sha256':digest,'http':code,'matches_server':remote_ok,'pass':ok}))
for name in ('assets/nuxel-boot-audio.mp3','assets/nuxel-pow.mp3'):
    p=root/name;ok=p.is_file() and p.stat().st_size>1000;failures+=not ok
    print(json.dumps({'path':name,'exists':ok,'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if ok else None,'pass':ok}))
for path in ('/run/nuxel-anim-handoff','/run/nuxel-haptics/state','/proc/asound/cards'):
    p=pathlib.Path(path)
    print(json.dumps({'evidence':path,'text':p.read_text(errors='replace')[:1200] if p.is_file() else 'UNAVAILABLE'}))
for name,cmd in [('aplay_devices',['aplay','-l']),('alsa_pcms',['aplay','-L']),('mixer',['amixer','-c','0','scontents']),('boot_sound',['systemctl','is-enabled','nuxel-boot-sound.service']),('button_manager',['systemctl','is-active','nuxel-button-manager.service']),('haptics',['systemctl','is-active','nuxel-haptics.service'])]:
    try:
        r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=6)
        print(json.dumps({'probe':name,'code':r.returncode,'output':r.stdout[-2500:]}))
    except (OSError,subprocess.TimeoutExpired) as e:print(json.dumps({'probe':name,'error':str(e)}))
print('A37 FILE/HTTP AUDIT:', 'PASS' if failures==0 else 'FAIL', 'speaker audibility = NEEDS PHYSICAL TEST')
sys.exit(1 if failures else 0)
