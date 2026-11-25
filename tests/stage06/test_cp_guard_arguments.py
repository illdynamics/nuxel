from pathlib import Path
import hashlib,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'services/nuxel-modem/bin/nuxel-cpbootd-stage04-guard').read_text()
def test_preflight_and_argument_rejection_never_execute_cp(tmp_path):
 td=str(tmp_path)
 p=Path(td); marker=p/'boot-executed'; binary=p/'cpboot';binary.write_text('#!/bin/sh\ntouch '+str(marker)+'\n');binary.chmod(0o700)
 fw=p/'fw';fw.touch();env=p/'env';env.write_text('STAGE04_MANIFEST_SHA256='+('a'*64)+'\nSTAGE04_FIRMWARE_PATH='+str(fw)+'\n')
 script=source.replace('/etc/nuxel/modem/stage04-trial.env',str(env)).replace('/usr/lib/nuxel/nuxel-modem/nuxel-cpbootd.aarch64.hw',str(binary)).replace('/dev/umts_boot0','/dev/null').replace('86de42aa9c0657791f6fe67d443d0231c51162e01880cd85708e27220a679402',hashlib.sha256(binary.read_bytes()).hexdigest())
 path=p/'guard';path.write_text(script)
 for args,expected in [(['--check'],0),(['--bad'],2),(['--check','extra'],2)]:
  r=subprocess.run(['bash',str(path),*args],capture_output=True,text=True);assert r.returncode==expected,(args,r.stderr);assert not marker.exists()
 r=subprocess.run(['bash',str(path)],capture_output=True,text=True);assert r.returncode==0 and marker.exists()
 print('PASS: check-only never executes CP; invalid arguments rejected; service invocation unchanged')
