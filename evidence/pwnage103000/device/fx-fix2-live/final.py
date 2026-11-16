import json,time,sys,functools
print=functools.partial(print, flush=True)
sys.stderr = sys.stdout
import gi
gi.require_version("Gtk","3.0"); gi.require_version("WebKit2","4.1")
from gi.repository import Gtk, WebKit2
PORT=sys.argv[1]
RESULTS={}
win=Gtk.OffscreenWindow(); view=WebKit2.WebView.new_with_context(WebKit2.WebContext.get_default())
view.set_size_request(360,760); win.add(view); win.show_all(); view.load_uri("http://127.0.0.1:%s/pwa/nuxel-home/index.html?final=%s"%(PORT,time.time()))
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
def J(label, script, wait=0):
    if wait: pump(wait)
    v=js(script)
    try: RESULTS[label]=json.loads(v)
    except Exception: RESULTS[label]=v
    print(label, RESULTS[label])
FD="(function(){var i=document.querySelector('.pwa-frame'); return i&&i.contentDocument;})()"
pump(9)
J("boot", "JSON.stringify({engine:!!NuxelEdgeLighting, dflt:NuxelEdgeLighting.DEFAULTS.effect, accent:NuxelEdgeLighting.themeAccent(), cache:document.querySelector('link[rel=manifest]')?1:0})")
js("NuxelEdgeLighting.applySettings({source_mode:'allowlist',allowed_apps:['nuxel-dialer'],enabled:true})"); pump(1.5)
J("seeded","JSON.stringify({m:NuxelEdgeLighting.status().settings.source_mode,a:NuxelEdgeLighting.status().settings.allowed_apps})")
js("(function(){var a=appRegistry.getApp('nuxel-edge-fx'); document.dispatchEvent(new CustomEvent('pwa:open',{detail:{app:a,url:a.url},bubbles:true})); return 1})()"); pump(6)
# custom colour then Preview
js("(function(){var d=%s; d.getElementById('color-mode').value='custom'; d.getElementById('color-mode').dispatchEvent(new Event('change',{bubbles:true})); d.getElementById('custom-color').value='#ff8fab'; d.getElementById('custom-color').dispatchEvent(new Event('change',{bubbles:true})); return 1})()" % FD); pump(1.5)
js("%s.getElementById('preview').click()" % FD); pump(0.45)
J("preview", """(function(){var r=document.getElementById('nuxel-edge-lighting'); var p=r&&r.querySelector('.edge-particle'); var c=p&&getComputedStyle(p); var br=p&&p.getBoundingClientRect(); return JSON.stringify({active:!!(r&&r.classList.contains('active')), visible:r&&getComputedStyle(r).visibility, z:r&&getComputedStyle(r).zIndex, clipped:r&&getComputedStyle(r).overflow, colour:c&&(c.borderRightColor+'|'+c.backgroundColor), particleBox:br&&[Math.round(br.width),Math.round(br.height)], sides:r&&r.querySelectorAll('.edge-side').length, last:NuxelEdgeLighting.status().lastPreview, msg:%s.getElementById('state').textContent});})()""" % FD, wait=0)
pump(2.4)
J("preview_stops","JSON.stringify({active:document.getElementById('nuxel-edge-lighting').classList.contains('active'), hidden:getComputedStyle(document.getElementById('nuxel-edge-lighting')).visibility})")
effs=[]
for eff in ["basic","wave","bubble","multicolor","heart","fireworks","eclipse","echo"]:
    js("%s.querySelector('.effect-tile[data-effect=%s]').click()" % (FD,eff)); pump(0.5)
    effs.append(json.loads(js("""(function(){var r=document.getElementById('nuxel-edge-lighting'); var parts=r?r.querySelectorAll('.edge-particle,.edge-band').length:0; return JSON.stringify({effect:'%s', persisted:NuxelEdgeLighting.status().settings.effect, previewed:(NuxelEdgeLighting.status().lastPreview||{}).effect, ok:(NuxelEdgeLighting.status().lastPreview||{}).ok, active:!!(r&&r.classList.contains('active')), nodes:parts});})()""" % eff)))
    pump(1.6)
RESULTS["effects"]=effs; print("effects", json.dumps(effs))
js("%s.getElementById('sources-clear').click()" % FD); pump(2.5)
J("allow_all", """(function(){var d=%s; return JSON.stringify({home_mode:NuxelEdgeLighting.status().settings.source_mode, home_allowed:NuxelEdgeLighting.status().settings.allowed_apps, summary:d.getElementById('sources-summary').textContent, checked:[].filter.call(d.querySelectorAll('#sources input'),function(c){return c.checked}).length, msg:d.getElementById('state').textContent});})()""" % FD)
# row edit after allow-all: check one app -> allowlist of 1 in provider AND Home
js("%s.querySelector('#sources input').click()" % FD); pump(2.5)
J("row_edit", """(function(){var d=%s; return JSON.stringify({home_mode:NuxelEdgeLighting.status().settings.source_mode, n:NuxelEdgeLighting.status().settings.allowed_apps.length, summary:d.getElementById('sources-summary').textContent});})()""" % FD)
js("%s.getElementById('sources-clear').click()" % FD); pump(2.5)
J("allow_all2", "JSON.stringify({home_mode:NuxelEdgeLighting.status().settings.source_mode, home_allowed:NuxelEdgeLighting.status().settings.allowed_apps})")
# lifecycle: uninstall -> inventory -> reinstall
js("(function(){window.confirm=function(){return true}; %s.getElementById('uninstall').click(); return 1})()" % FD); pump(3)
J("after_uninstall", "(async function(){await NuxelBridge._init(); var r=await NuxelBridge.call('apps','inventory',{}); var me=(r.apps||[]).filter(function(a){return a.id==='nuxel-edge-fx'})[0]; window.__x=JSON.stringify({inInventory:!!me, state: me&&(me.state||'registered')}); return 1})()")
J("uninstall_result","window.__x")
js("%s.getElementById('reinstall').click()" % FD); pump(3)
J("after_reinstall", "(async function(){await NuxelBridge._init(); var r=await NuxelBridge.call('apps','inventory',{}); var me=(r.apps||[]).filter(function(a){return a.id==='nuxel-edge-fx'})[0]; window.__y=JSON.stringify({inInventory:!!me, state: me&&(me.state||'registered'), msg:%s.getElementById('install-state').textContent}); return 1})()" % FD)
J("reinstall_result","window.__y")
# restore defaults for the owner: wave is the default effect; keep their enabled state
js("NuxelEdgeLighting.applySettings({effect:'wave'})"); pump(1)
J("final","JSON.stringify(NuxelEdgeLighting.status().settings)")
json.dump(RESULTS, open(sys.argv[2] if len(sys.argv)>2 else "/tmp/p103-final.json","w"), indent=1)
print("WROTE /tmp/p103-final.json")
