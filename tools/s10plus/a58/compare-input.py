#!/usr/bin/env python3
"""Synthetic WebKit comparison against the actual backed-up A57 UI."""
import http.server,threading,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/a58-snakepwn-7000/evidence'
HOOK="""window.__SNEK_DEBUG__=true;window.__events=[];window.__turns=[];
let engine;Object.defineProperty(window,'SnekEngine',{get:()=>engine,set:e=>{engine=e;const turn=e.turn;e.turn=(g,d)=>{__turns.push({at:performance.now(),dir:d});return turn(g,d);};}});
for(const type of ['pointerdown','pointermove','pointerup','click'])document.addEventListener(type,e=>__events.push({type,at:performance.now(),rawEventTimeStamp:e.timeStamp}),true);
"""
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
out={}
with sync_playwright() as p:
 browser=p.webkit.launch(headless=True)
 for label,source in [('A57',ROOT/'dist/a58-rollback/a57-pwa'),('A58',ROOT.parent/'snekbyte/reference-pwa/nuxel-dropin/pwa/nuxel-apps/snekbyte')]:
  def handler(*a,**kw):return Quiet(*a,directory=str(source),**kw)
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  results={}
  for action in ['dpad','swipe']:
   context=browser.new_context(viewport={'width':412,'height':915});context.add_init_script(HOOK)
   page=context.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/');page.locator('#overlay-buttons button').first.click()
   page.evaluate('__events=[];__turns=[]')
   if action=='dpad':
    box=page.locator('[data-dir=up]').bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
    page.mouse.move(x,y);page.mouse.down();time.sleep(.2)
    before=page.evaluate('({turns:__turns.slice(),debug:window.SnekByteDebug?SnekByteDebug.snapshot().traces:[]})');page.mouse.up()
   else:
    for typ,x,y in [('pointerdown',100,100),('pointermove',100,70)]:
     page.dispatch_event('#screen',typ,dict(pointerId=5,pointerType='touch',isPrimary=True,button=0,clientX=x,clientY=y))
    time.sleep(.2);before=page.evaluate('({turns:__turns.slice(),debug:window.SnekByteDebug?SnekByteDebug.snapshot().traces:[]})')
    page.dispatch_event('#screen','pointerup',dict(pointerId=5,clientX=100,clientY=70))
   time.sleep(.1)
   data=page.evaluate('({events:__events,turns:__turns,debug:window.SnekByteDebug?SnekByteDebug.snapshot().traces:[]})');data['beforeRelease']=before
   assert bool(before['turns'])==(label=='A58')
   results[action]=data;context.close()
  out[label]=results;server.shutdown()
 browser.close()
(OUT/'baseline-vs-a58-input.json').write_text(json.dumps(out,indent=2)+'\n')
for label,cases in out.items():
 for action,data in cases.items():
  start=next(e['at'] for e in data['events'] if e['type']==('pointerdown' if action=='dpad' else 'pointermove'))
  recognized=data['debug'][0]['recognizedAt'] if data['debug'] else data['turns'][0]['at']
  print(label,action,'software event-to-recognition ms',round(recognized-start,3),'turn before release',bool(data['beforeRelease']['turns']))
