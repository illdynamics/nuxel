import json,time,sys,functools
print=functools.partial(print, flush=True)
import gi
gi.require_version("Gtk","3.0"); gi.require_version("WebKit2","4.1")
from gi.repository import Gtk, WebKit2
win=Gtk.OffscreenWindow(); view=WebKit2.WebView.new_with_context(WebKit2.WebContext.get_default())
view.set_size_request(360,760); win.add(view); win.show_all(); view.load_uri("http://127.0.0.1:8011/pwa/nuxel-home/index.html?life4=%s"%time.time())
def pump(s):
    end=time.time()+s
    while time.time()<end: Gtk.main_iteration_do(False); time.sleep(0.01)
def js(sc,t=15):
    b={}
    def cb(_v,r,_d=None):
        try: b["v"]=_v.evaluate_javascript_finish(r).to_string()
        except Exception as e: b["e"]=str(e)
    view.evaluate_javascript(sc,-1,None,None,None,cb,None); end=time.time()+t
    while not b and time.time()<end: Gtk.main_iteration_do(False); time.sleep(0.01)
    return b.get("v","ERR "+str(b.get("e") or "timeout"))
pump(9)
js("(function(){var a=appRegistry.getApp('nuxel-edge-fx'); document.dispatchEvent(new CustomEvent('pwa:open',{detail:{app:a,url:a.url},bubbles:true})); return 1})()"); pump(6)
FD="document.querySelector('.pwa-frame').contentDocument"
print("CLICK", js("(function(){window.confirm=function(){return true}; var b=%s.getElementById('uninstall'); b.click(); return 'clicked disabled='+b.disabled;})()" % FD)); pump(4)
print("UI", js("%s.getElementById('install-state').textContent" % FD))
print("MSG", js("%s.getElementById('state').textContent" % FD))
