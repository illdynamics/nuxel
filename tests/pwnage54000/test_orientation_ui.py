#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
expected={
 'auto':'Auto (FULL)','auto-portrait':'Auto (PT)','auto-landscape':'Auto (LS)',
 'portrait':'Locked (PT)','landscape':'Locked (LS)','reverse-portrait':'Locked (RPT)',
 'reverse-landscape':'Locked (RLS)'}
fails=[]
def check(n,c,e=''):
 print(('PASS ' if c else 'FAIL ')+n+('' if c else '  '+str(e)))
 if not c: fails.append(n)
cfg=json.loads((ROOT/'configs/nuxel/orientation/orientation.json').read_text())
for k,v in expected.items(): check('config label '+k,cfg['modes'][k]['label']==v,cfg['modes'][k]['label'])
qs=(ROOT/'pwa/nuxel-home/js/qs.js').read_text()
for k,v in expected.items(): check('QS key/label '+k, ("['%s', '%s']"%(k,v)) in qs)
st=(ROOT/'pwa/nuxel-apps/settings/settings.js').read_text()
for k,v in expected.items(): check('Settings key/label '+k, ("['%s', '%s']"%(k,v)) in st)
check('QS short tap never selects Auto', "cur.mode === 'auto' ? 'portrait' : 'auto'" not in qs and 'rotate 90 degrees' in qs)
check('QS renders Auto degraded when no sensor', "data-degraded" in qs or "dataset.degraded" in qs)
print('\n%d failing check(s)'%len(fails)); sys.exit(1 if fails else 0)
