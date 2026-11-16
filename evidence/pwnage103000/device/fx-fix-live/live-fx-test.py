#!/usr/bin/env python3
import json,sys,time,subprocess
import gi
gi.require_version('Gtk','3.0'); gi.require_version('WebKit2','4.1')
from gi.repository import Gtk, WebKit2
BASE='http://127.0.0.1:8000/pwa/nuxel-home/index.html?fxver=p103000b5'
def run(v,s,ms=10000):
    box={};done=[]
    def cb(_v,res,_d=None):
        try:
            r=_v.evaluate_javascript_finish(res); box['v']=r.to_string() if r else None
        except Exception as e: box['e']=str(e)
        done.append(1)
    v.evaluate_javascript(s,-1,None,None,None,cb,None)
    end=time.time()+ms/1000
    while not done and time.time()<end:
        Gtk.main_iteration_do(False); time.sleep(.01)
    return box.get('v') if 'v' in box else 'ERR '+(box.get('e') or 'timeout')
def pump(sec):
    end=time.time()+sec
    while time.time()<end: Gtk.main_iteration_do(False); time.sleep(.01)
w=Gtk.OffscreenWindow(); w.set_default_size(360,760)
v=WebKit2.WebView.new(); v.set_size_request(360,760); w.add(v); w.show_all()
v.load_uri(BASE)
end=time.time()+30
while v.get_estimated_load_progress()<1 and time.time()<end: Gtk.main_iteration_do(False); time.sleep(.02)
pump(4)
out={}
run(v, r"""(function(){var x=document.querySelector('.pwa-frame');return 'pre'})()""")
out['boot']=json.loads(run(v,"JSON.stringify({engine:!!window.NuxelEdgeLighting,reg:!!window.appRegistry,ver:!!(window.NuxelEdgeLighting&&document.querySelector('#nuxel-edge-lighting'))})"))
out['launch']=run(v,"(function(){window.appRegistry.launchApp('nuxel-edge-fx');return 'ok'})()")
pump(5)
# make Edge FX the only active iframe; the real app is fullscreen over Home
out['frame']=json.loads(run(v,r"""JSON.stringify((function(){var f=document.querySelector('.pwa-frame');if(!f)return {frame:false};var x=f.contentWindow,d=x.document;return {src:f.src,script:[].map.call(d.scripts,function(s){return s.src}).filter(function(s){return /edge-fx/.test(s)}),hasEmpty:!!d.getElementById('sources-empty'),preview:!!d.getElementById('preview'),state:d.getElementById('state')?d.getElementById('state').textContent:'-',checked:Array.from(d.querySelectorAll('#sources input')).filter(function(e){return e.checked}).length,total:d.querySelectorAll('#sources input').length,emptyShown:!!(d.getElementById('sources-empty')&&!d.getElementById('sources-empty').hidden),summary:d.getElementById('sources-summary')?d.getElementById('sources-summary').textContent:null};})())"""))
# click Preview selected exactly as a user would, from inside the app frame
out['preview_click']=json.loads(run(v,r"""JSON.stringify((function(){var x=document.querySelector('.pwa-frame').contentWindow,d=x.document;d.getElementById('preview').click();return {clicked:true,buttonDisabled:d.getElementById('preview').disabled};})())"""))
pump(1)
out['preview_after']=json.loads(run(v,r"""JSON.stringify((function(){var x=document.querySelector('.pwa-frame').contentWindow,p=x.parent,d=x.document;var r=p.document.getElementById('nuxel-edge-lighting');var css=r?p.getComputedStyle(r):null;var f=x.frameElement;var fs=f?p.getComputedStyle(f):null;return {fx_state:d.getElementById('state').textContent,preview_btn_disabled:d.getElementById('preview').disabled,home_last_preview:p.NuxelEdgeLighting.status().lastPreview,root:!!r,active:!!(r&&r.classList.contains('active')),visibility:css?css.visibility:null,zIndex:css?css.zIndex:null,frameZ:fs?fs.zIndex:null,bands:r?r.querySelectorAll('.edge-band').length:0,trace:r?r.querySelectorAll('.edge-wave-trace,.edge-multicolor,.edge-heart,.edge-bubble,.edge-spark,.edge-crescent,.edge-echo-band').length:0,opacities:r?Array.from(r.querySelectorAll('.edge-band,.edge-particle')).slice(0,6).map(function(e){return p.getComputedStyle(e).opacity}):[]};})())"""))
pump(2)
out['preview_done']=json.loads(run(v,r"""JSON.stringify((function(){var p=document.querySelector('.pwa-frame').contentWindow.parent;var r=p.document.getElementById('nuxel-edge-lighting');return {active:!!(r&&r.classList.contains('active')),visibility:r?p.getComputedStyle(r).visibility:null};})())"""))
# Select one real app to enter allowlist mode, then Allow all must clear it.
out['pick_one']=json.loads(run(v,r"""JSON.stringify((function(){var x=document.querySelector('.pwa-frame').contentWindow,d=x.document;var cb=Array.from(d.querySelectorAll('#sources input')).find(function(e){return !e.checked})||d.querySelectorAll('#sources input')[0];cb.click();return {label:(cb.parentNode.textContent||'').slice(0,40)};})())"""))
pump(2)
out['after_pick_one']=json.loads(run(v,r"""JSON.stringify((function(){var x=document.querySelector('.pwa-frame').contentWindow,d=x.document;return {checked:Array.from(d.querySelectorAll('#sources input')).filter(function(e){return e.checked}).length,summary:d.getElementById('sources-summary').textContent,emptyShown:!d.getElementById('sources-empty').hidden,state:d.getElementById('state').textContent};})())"""))
# click the allow-all button
out['allowall_click']=json.loads(run(v,r"""JSON.stringify((function(){var x=document.querySelector('.pwa-frame').contentWindow,d=x.document;d.getElementById('sources-clear').click();return {clicked:true};})())"""))
pump(2)
out['allowall_after']=json.loads(run(v,r"""JSON.stringify((function(){var x=document.querySelector('.pwa-frame').contentWindow,d=x.document;return {state:d.getElementById('state').textContent,checked:Array.from(d.querySelectorAll('#sources input')).filter(function(e){return e.checked}).length,total:d.querySelectorAll('#sources input').length,emptyShown:!!(d.getElementById('sources-empty')&&!d.getElementById('sources-empty').hidden),summary:d.getElementById('sources-summary')?d.getElementById('sources-summary').textContent:null};})())"""))
out['provider']=json.loads(run(v,"JSON.stringify((function(){var st=window.NuxelEdgeLighting.status();return {effect:st.settings.effect,provider:st.provider,preview:st.lastPreview,previewError:st.lastPreviewError};})())"))
# confirm the persisted file independently (provider restart persistence is covered elsewhere)
out['settings_file_allowed']=subprocess.run(['python3','-c','import json;print(json.dumps(json.load(open("/var/lib/nuxel/edge-lighting/settings.json"))["allowed_apps"]))'],capture_output=True,text=True).stdout.strip()
print(json.dumps(out,indent=1,sort_keys=True))
ok = (out['preview_after']['active'] and out['preview_after']['visibility']=='visible'
      and (out['preview_after']['zIndex'] or '') != '' and out['preview_after']['bands']==2
      and out['after_pick_one']['checked']>=1 and out['allowall_after']['checked']==0
      
      and out['allowall_after']['emptyShown'] and out['settings_file_allowed']=='[]')
print('LIVE_EDGE_FX_TEST:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
