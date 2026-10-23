#!/usr/bin/env python3
"""Real Android WebView execution on an explicitly selected ADB device.
Synthetic CDP pointer events + native ADB Back/Home. Never physical acceptance.
Five-minute performance mode: --soak 300. No uninstall or storage reset.
"""
import argparse,json,subprocess,time,urllib.request,websocket,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/a58-snakepwn-7000/evidence'
class CDP:
    def __init__(self,port=9229):
        pages=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'))
        endpoint=next(p['webSocketDebuggerUrl'] for p in pages if p['url'].startswith('https://localhost'))
        self.ws=websocket.create_connection(endpoint,suppress_origin=True,timeout=15);self.id=0
    def call(self,method,**params):
        self.id+=1;self.ws.send(json.dumps(dict(id=self.id,method=method,params=params)))
        while True:
            msg=json.loads(self.ws.recv())
            if msg.get('id')==self.id:
                if 'error' in msg:raise RuntimeError(msg)
                return msg.get('result',{})
    def js(self,expression):
        r=self.call('Runtime.evaluate',expression=expression,returnByValue=True,awaitPromise=True)
        if 'exceptionDetails' in r:raise RuntimeError(r)
        return r.get('result',{}).get('value')
    def click(self,selector,release=True):
        p=self.js('(function(){var r=document.querySelector('+json.dumps(selector)+').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()')
        self.call('Input.dispatchMouseEvent',type='mousePressed',button='left',buttons=1,clickCount=1,**p)
        if release:self.call('Input.dispatchMouseEvent',type='mouseReleased',button='left',buttons=0,clickCount=1,**p)
    def snap(self):return self.js('SnekByteDebug.snapshot()')
    def screenshot(self,path):
        import base64
        path.write_bytes(base64.b64decode(self.call('Page.captureScreenshot',format='png')['data']))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--serial',default='emulator-5554');ap.add_argument('--soak',type=int,default=0)
    ap.add_argument('--expected-prefs',type=Path);args=ap.parse_args()
    adb=['adb','-s',args.serial]
    def shell(*cmd):return subprocess.check_output(adb+['shell',*cmd],text=True).strip()
    shell('am','start','-W','-n','com.illdynamics.snekbyte/.MainActivity')
    pid=shell('pidof','com.illdynamics.snekbyte')
    subprocess.run(adb+['forward','tcp:9229','localabstract:webview_devtools_remote_'+pid],check=True,capture_output=True)
    for attempt in range(50):
        try:
            c=CDP()
            if c.js('document.readyState')=='complete':break
            c.ws.close()
        except Exception:
            if attempt==49:raise
        time.sleep(.2)
    original=c.js("localStorage.getItem('nuxel-snekbyte-settings-v2')")
    c.call('Page.enable');c.call('Page.addScriptToEvaluateOnNewDocument',source='window.__SNEK_DEBUG__=true')
    c.call('Page.reload',ignoreCache=True)
    for _ in range(50):
        try:
            if c.js('!!window.SnekByteDebug'):break
        except Exception:pass
        time.sleep(.1)
    report={'device':args.serial,'physical':not args.serial.startswith('emulator-'),'input':'synthetic CDP + ADB','originalPrefs':original,'checks':[]}
    def check(name,ok,detail=None):
        report['checks'].append({'name':name,'pass':bool(ok),'detail':detail});print(name,ok,flush=True)
        (OUT/'android-acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
        if not ok:raise AssertionError(name)
    if args.expected_prefs:
        check('APK update retained previous saved preferences and score',json.loads(original)==json.loads(args.expected_prefs.read_text()))
    check('saved speed/WoNQ/grid/highscore retained through cold WebView load',all(c.js("JSON.parse(localStorage.getItem('nuxel-snekbyte-settings-v2'))").get(k)==v for k,v in json.loads(original).items()))
    c.screenshot(OUT/'android-menu.png')
    if args.soak:
        c.js("document.querySelector('#settings-button').click();document.querySelector('#speed-setting').value='2';document.querySelector('#speed-setting').dispatchEvent(new Event('input'));document.querySelector('#settings-done').click();document.querySelector('#overlay-buttons button').click()")
        c.call('Performance.enable');start=time.monotonic();samples=[];traces=[];work=[];turns=0;restarts=0;prev_ticks=0;total_ticks=0
        initial=c.call('Performance.getMetrics')
        while time.monotonic()-start<args.soak:
            time.sleep(1)
            state=c.snap();delta=state['game']['tick']-prev_ticks;total_ticks+=max(0,delta);prev_ticks=state['game']['tick']
            if state['mode']=='over':c.click('#overlay-buttons button');restarts+=1;prev_ticks=0
            c.click('[data-dir='+['down','left','up','right'][turns%4]+']');turns+=1
            if turns%10==0:
                state=c.snap();traces.extend(t for t in state['traces'] if t.get('drawnAt') is not None);work+=state['frameWorkMs']
                samples.append({'seconds':round(time.monotonic()-start,2),'ticks':total_ticks,'droppedMs':state['droppedMs'],
                    'metrics':c.call('Performance.getMetrics')['metrics']})
                print('soak',samples[-1]['seconds'],'ticks',total_ticks,flush=True)
            if turns%30==0:
                (OUT/f'android-meminfo-{turns}.txt').write_text(shell('dumpsys','meminfo','com.illdynamics.snekbyte'))
                (OUT/f'android-cpuinfo-{turns}.txt').write_text(shell('dumpsys','cpuinfo'))
        elapsed=time.monotonic()-start
        def stats(values):
            values=sorted(values);return {'n':len(values),'median':statistics.median(values),'p95':values[min(len(values)-1,int(len(values)*.95))]} if values else None
        unique={t['id']:t for t in traces};traces=list(unique.values())
        perf={'device':args.serial,'seconds':elapsed,'ticks':total_ticks,'turns':turns,'restarts':restarts,'softwareOnly':True,
              'recognitionMs':stats([t['recognizedAt']-t['eventAt'] for t in traces if t.get('eventAt') is not None]),
              'acceptedToTickMs':stats([t['appliedAt']-t['recognizedAt'] for t in traces]),
              'acceptedToDrawSubmissionMs':stats([t['drawnAt']-t['recognizedAt'] for t in traces]),
              'frameWorkMs':stats(work),'initialMetrics':initial,'samples':samples,'traces':traces}
        (OUT/'android-five-minute-performance.json').write_text(json.dumps(perf,indent=2)+'\n')
        shell('input','keyevent','3');time.sleep(2);hidden=c.snap();time.sleep(10)
        check('native background stops simulation and RAF',hidden['game']['tick']==c.snap()['game']['tick'] and not c.snap()['rafPending'])
        stat1=shell('run-as','com.illdynamics.snekbyte','cat','/proc/'+pid+'/stat');time.sleep(10)
        stat2=shell('run-as','com.illdynamics.snekbyte','cat','/proc/'+pid+'/stat')
        def cpu(stat):
            fields=stat[stat.rindex(')')+2:].split();return int(fields[11])+int(fields[12])
        (OUT/'android-background-counters.json').write_text(json.dumps({'intervalSeconds':10,'pid':pid,'cpuJiffiesDelta':cpu(stat2)-cpu(stat1),'rafPending':c.snap()['rafPending'],'ticksChanged':c.snap()['game']['tick']-hidden['game']['tick']},indent=2)+'\n')
        (OUT/'android-background-cpuinfo.txt').write_text(shell('dumpsys','cpuinfo'))
        return
    c.click('#overlay-buttons button');check('offline bundled game launches',c.snap()['mode']=='playing')
    c.click('[data-dir=up]',release=False);press=c.snap();check('D-pad acknowledges on mouse press',any(t['source']=='dpad' and t['result']=='accepted' for t in press['traces']))
    c.call('Input.dispatchMouseEvent',type='mouseReleased',x=0,y=0,button='left',buttons=0,clickCount=1)
    time.sleep(.15);check('accepted turn applied/drawn',any('drawnAt' in t for t in c.snap()['traces']))
    before=c.snap()['game'];c.click('#speed-down');after=c.snap();check('live speed changes without resetting score/tick',after['period']>50 and after['game']['score']==before['score'] and after['game']['tick']>=before['tick'])
    shell('input','keyevent','4');time.sleep(.2);check('native Back pauses',c.snap()['paused'])
    paused=c.snap()['game']['tick'];time.sleep(.2);check('paused remains motionless',c.snap()['game']['tick']==paused)
    c.click('#pause-button');shell('input','keyevent','3');time.sleep(.5)
    check('native Home suspends loop',c.snap()['paused'] and not c.snap()['rafPending'])
    shell('am','start','-n','com.illdynamics.snekbyte/.MainActivity');time.sleep(.5);check('foreground requires deliberate resume',c.snap()['paused'])
    c.screenshot(OUT/'android-paused.png')
    prefs=c.js("localStorage.getItem('nuxel-snekbyte-settings-v2')");c.call('Page.reload');time.sleep(.5)
    check('preferences survive WebView reload',c.js("localStorage.getItem('nuxel-snekbyte-settings-v2')")==prefs)
    report['finalPrefs']=prefs;report['traces']=press['traces'];report['physical']=False
    (OUT/'android-acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
