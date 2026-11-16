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
SNAP=r"""JSON.stringify((function(){var p=document.querySelector('.pwa-frame').contentWindow.parent,L=p.NuxelEdgeLighting,r=p.document.getElementById('nuxel-edge-lighting');return {active:!!(r&&r.classList.contains('active')),visible:r?p.getComputedStyle(r).visibility:null,z:r?p.getComputedStyle(r).zIndex:null,bands:r?r.querySelectorAll('.edge-band').length:0,particles:r?r.querySelectorAll('.edge-particle').length:0,last:L.status().lastPreview,err:L.status().lastPreviewError,roots:p.document.querySelectorAll('#nuxel-edge-lighting').length};})())"""
w=Gtk.OffscreenWindow();w.set_default_size(360,760);v=WebKit2.WebView.new();w.add(v);w.show_all();v.load_uri('http://127.0.0.1:8000/pwa/nuxel-home/index.html?effects=final3')
end=time.time()+30
while v.get_estimated_load_progress()<1 and time.time()<end:Gtk.main_iteration_do(False);time.sleep(.02)
pump(4);run(v,"window.appRegistry.launchApp('nuxel-edge-fx');'ok'");pump(4)
out={}
for eff in ['basic','wave','bubble','multicolor','heart','fireworks','eclipse','echo']:
    run(v,"(function(){var p=document.querySelector('.pwa-frame').contentWindow.parent;return String(p.NuxelEdgeLighting.preview('%s'));})()"%eff)
    pump(.25)
    out[eff]=json.loads(run(v,SNAP))
    pump(2.0)
out['after_bounds']=json.loads(run(v,SNAP))
run(v,"(function(){var x=document.querySelector('.pwa-frame').contentWindow;var b=x.document.getElementById('preview');b.click();b.click();return 'ok';})()")
pump(.4)
out['double_click']=json.loads(run(v,SNAP))
print(json.dumps(out,indent=1))
eff={k:v for k,v in out.items() if k in ('basic','wave','bubble','multicolor','heart','fireworks','eclipse','echo')}
ok=all(v['active'] and v['visible']=='visible' and v['last'] and v['last']['ok'] and v['err'] is None for v in eff.values()) and len(eff)==8
ok=ok and not out['after_bounds']['active'] and out['after_bounds']['roots']==1 and out['double_click']['roots']==1
print('LIVE_EFFECT_PREVIEWS:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
