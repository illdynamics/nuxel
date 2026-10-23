#!/usr/bin/env python3
"""Drive the real final APK by CDP pointer events. No engine/food mutation.
Observe four seams, eat five actual randomly placed foods, then collide with poop.
"""
import collections,importlib.util,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/a58-snakepwn-7000/evidence'
spec=importlib.util.spec_from_file_location('acceptance',Path(__file__).with_name('android-acceptance.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
adb=['adb','-s','emulator-5554']
subprocess.run(adb+['shell','am','start','-W','-n','com.illdynamics.snekbyte/.MainActivity'],check=True,capture_output=True)
pid=subprocess.check_output(adb+['shell','pidof','com.illdynamics.snekbyte'],text=True).strip();subprocess.run(adb+['forward','tcp:9229','localabstract:webview_devtools_remote_'+pid],check=True,capture_output=True)
c=m.CDP();report={'device':'emulator-5554','input':'synthetic CDP pointer events; unmodified simulation and random foods','wraps':[],'meals':[]}
for _ in range(3):c.js('SnekByteUI.handleBack()')
c.js("document.querySelector('#settings-button').click();document.querySelector('#speed-setting').value='2';document.querySelector('#speed-setting').dispatchEvent(new Event('input'));for(const id of ['wonq-setting','wrap-setting']){const e=document.getElementById(id);e.checked=true;e.dispatchEvent(new Event('change'));}document.querySelector('#settings-done').click()")
c.click('#overlay-buttons button')
for direction,axis,from_edge,to_edge in [('right',0,39,0),('down',1,29,0),('left',0,0,39),('up',1,0,29)]:
 if direction!='right':c.click('[data-dir='+direction+']')
 previous=c.snap()['game'];deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  game=c.snap()['game'];assert not game['gameOver'],game
  if previous['snake']['positions'][0][axis]==from_edge and game['snake']['positions'][0][axis]==to_edge:
   report['wraps'].append({'direction':direction,'from':previous['snake']['positions'][0],'to':game['snake']['positions'][0],'tick':game['tick']});print('wrap',direction,flush=True);break
  previous=game;time.sleep(.012)
 else:raise AssertionError('wrap timeout '+direction)
c.js('SnekByteUI.handleBack();SnekByteUI.handleBack()');c.click('#overlay-buttons button')
dirs=[(1,0,'right'),(0,1,'down'),(-1,0,'left'),(0,-1,'up')]
def next_turn(game,target,allow_poop):
 head=tuple(game['snake']['positions'][0]);heading=tuple(game['snake']['direction'])
 body={tuple(x) for x in game['snake']['positions'][1:]}
 blocked=body|{tuple(p) for p in game['poops'] if not (allow_poop and tuple(p)==target)}
 todo=collections.deque([(head,heading,None)]);seen={(head,heading)}
 while todo:
  pos,d,first=todo.popleft()
  if pos==target:return first
  for dx,dy,name in dirs:
   if (dx,dy)==(-d[0],-d[1]):continue
   p=((pos[0]+dx)%40,(pos[1]+dy)%30);state=(p,(dx,dy))
   if p in blocked or state in seen:continue
   seen.add(state);todo.append((p,(dx,dy),first or (dx,dy,name)))
 return next((d for d in dirs if d[:2]==heading),None)
last_tick=-1;last_score=-1;deadline=time.monotonic()+90
while time.monotonic()<deadline:
 state=c.snap();g=state['game']
 if g['score']!=last_score:
  last_score=g['score'];report['meals'].append({'score':g['score'],'meter':g['shitCounter'],'poops':g['poops'],'hud':c.js("document.querySelector('#meter-count').textContent")});print('meal',g['score'],'meter',g['shitCounter'],flush=True)
 if g['gameOver']:
  assert g['score']>=5 and g['cause']=='poop',g
  report['ending']=g;break
 if g['tick']==last_tick or state['queue']:
  time.sleep(.012);continue
 last_tick=g['tick'];hazard=g['score']>=5;target=tuple(g['poops'][0] if hazard else g['food'])
 turn=next_turn(g,target,hazard)
 if turn and list(turn[:2])!=g['snake']['direction']:c.click('[data-dir='+turn[2]+']')
 time.sleep(.012)
else:raise AssertionError('food/poop timeout')
assert len(report['wraps'])==4
assert [x['meter'] for x in report['meals'][:6]]==[0,1,2,3,4,0]
c.js('SnekBytePersistence.flush()');report['nativePrefs']=c.js('Capacitor.Plugins.SnekPrefs.read()')
c.screenshot(OUT/'android-poop-gameover.png')
(OUT/'android-gameplay.json').write_text(json.dumps(report,indent=2)+'\n');print('four wraps, five real foods and fatal poop: PASS',flush=True)
c.ws.close()
