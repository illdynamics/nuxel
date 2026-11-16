import json,time,sys
import gi
gi.require_version('Gtk','3.0'); gi.require_version('WebKit2','4.1')
from gi.repository import Gtk,WebKit2
def run(v,s,ms=15000):
 box={};done=[]
 def cb(_v,res,_d=None):
  try: r=_v.evaluate_javascript_finish(res);box['v']=r.to_string() if r else None
  except Exception as e:box['e']=str(e)
  done.append(1)
 v.evaluate_javascript(s,-1,None,None,None,cb,None);end=time.time()+ms/1000
 while not done and time.time()<end:Gtk.main_iteration_do(False);time.sleep(.01)
 return box.get('v') if 'v' in box else 'ERR '+str(box.get('e'))
def pump(s):
 end=time.time()+s
 while time.time()<end:Gtk.main_iteration_do(False);time.sleep(.01)
STATE=r"""JSON.stringify((function(){var x=document.querySelector('.pwa-frame').contentWindow,d=x.document;return {checked:Array.from(d.querySelectorAll('#sources input')).filter(function(e){return e.checked}).length,total:d.querySelectorAll('#sources input').length,summary:d.getElementById('sources-summary')?d.getElementById('sources-summary').textContent:null,msg:d.getElementById('state').textContent};})())"""
w=Gtk.OffscreenWindow();w.set_default_size(360,760);v=WebKit2.WebView.new();w.add(v);w.show_all();v.load_uri('http://127.0.0.1:8000/pwa/nuxel-home/index.html?allowall=final')
end=time.time()+30
while v.get_estimated_load_progress()<1 and time.time()<end:Gtk.main_iteration_do(False);time.sleep(.02)
pump(4)
# start from provider-confirmed All apps
run(v,"(function(){window.NuxelEdgeLighting.applySettings({source_mode:'all',allowed_apps:[],blocked_apps:[]});return 'ok';})()");pump(.8)
run(v,"window.appRegistry.launchApp('nuxel-edge-fx');'ok'");pump(4)
out={}
out['start']=json.loads(run(v,STATE))
run(v,"(function(){var x=document.querySelector('.pwa-frame').contentWindow,d=x.document;var cbs=Array.from(d.querySelectorAll('#sources input'));var cb=cbs.find(function(e){return !e.checked});cb.click();return cb.parentNode.textContent;})()")
pump(1)
out['selected']=json.loads(run(v,STATE))
run(v,"(function(){var x=document.querySelector('.pwa-frame').contentWindow;x.document.getElementById('sources-clear').click();return 'ok';})()")
pump(2)
out['after_allow_all']=json.loads(run(v,STATE))
print(json.dumps(out,indent=1))
ok=out['start']['checked']==0 and out['selected']['checked']==1 and out['after_allow_all']['checked']==0 and 'All apps' in (out['after_allow_all']['summary'] or '')
print('LIVE_ALLOW_ALL:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
