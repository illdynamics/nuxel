import json,time,sys
import gi
gi.require_version("Gtk","3.0"); gi.require_version("WebKit2","4.1")
from gi.repository import Gtk, WebKit2
mode=sys.argv[1]
win=Gtk.OffscreenWindow(); view=WebKit2.WebView.new_with_context(WebKit2.WebContext.get_default())
view.set_size_request(360,760); win.add(view); win.show_all(); view.load_uri("http://127.0.0.1:8011/pwa/nuxel-home/index.html?b=%s&%s"%(mode,time.time()))
def pump(s):
    end=time.time()+s
    while time.time()<end: Gtk.main_iteration_do(False); time.sleep(0.01)
def js(sc,t=20):
    b={}
    def cb(_v,r,_d=None):
        try: b["v"]=_v.evaluate_javascript_finish(r).to_string()
        except Exception as e: b["e"]=str(e)
    view.evaluate_javascript(sc,-1,None,None,None,cb,None); end=time.time()+t
    while not b and time.time()<end: Gtk.main_iteration_do(False); time.sleep(0.01)
    return b.get("v","ERR "+str(b.get("e") or "timeout"))
pump(9)
if mode=="before":
    js("NuxelBridge.call('edge-lighting','status',{})")
elif mode=="after":
    js("(function(){var a=appRegistry.getApp('nuxel-edge-fx'); document.dispatchEvent(new CustomEvent('pwa:open',{detail:{app:a,url:a.url},bubbles:true})); return 1})()"); pump(6)
pump(1)
js("""window.__o=null;(async function(){ var out={}; function j(x){try{return JSON.stringify(x).slice(0,80)}catch(e){return String(x)}}
 try{ var r=await fetch('http://127.0.0.1:8080/api/v1/ping',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}); out.raw=[r.status,(await r.text()).slice(0,40)]; }catch(e){ out.raw='ERR '+e }
 try{ await NuxelBridge._init(); out.init={c:NuxelBridge.connected,m:NuxelBridge.mockMode}; }catch(e){ out.init='ERR '+e }
 try{ out.call=j(await NuxelBridge.call('edge-lighting','status',{})); }catch(e){ out.call='ERR '+e }
 window.__o=j(out); })()""")
pump(4)
print(mode, js("window.__o"))
