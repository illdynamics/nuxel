#!/usr/bin/env python3
"""A58 browser integration: real WebKit, synthetic input, deterministic clock.
Run: python3 tools/s10plus/a58/test-browser.py
Requires Playwright + its WebKit binary. Never claims physical touch acceptance.
"""
import contextlib, functools, http.server, json, os, socket, threading, unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('SNEK_SOURCE', str(ROOT.parent/'snekbyte/reference-pwa/nuxel-dropin/pwa/nuxel-apps/snekbyte')))
EVIDENCE = ROOT/'docs/a58-snakepwn-7000/evidence'
CLOCK = """(() => {
 window.__SNEK_DEBUG__=true; let now=0,id=0;const frames=new Map();
 performance.now=()=>now;
 window.requestAnimationFrame=fn=>{frames.set(++id,fn);return id;};
 window.cancelAnimationFrame=id=>frames.delete(id);
 window.__advance=ms=>{now+=ms;const list=[...frames.values()];frames.clear();list.forEach(fn=>fn(now));};
 window.__pending=()=>frames.size;
 let engine;
 Object.defineProperty(window,'SnekEngine',{configurable:true,get:()=>engine,set:e=>{
   engine=e;const reset=e.reset;e.reset=(...args)=>{const g=reset(...args);window.__testGame=g;
     g.food.position=[2,2];return g;};
 }});
})();"""
class Handler(http.server.SimpleHTTPRequestHandler):
    offline = False
    legacy = False
    def __init__(self,*args,**kwargs):
        source=ROOT/'dist/a58-rollback/a57-pwa' if self.legacy else SOURCE
        super().__init__(*args,directory=str(source),**kwargs)
    def log_message(self,*args):pass
    def do_GET(self):
        if self.offline:
            self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
        super().do_GET()
    def end_headers(self):self.send_header('Cache-Control','no-cache');super().end_headers()

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}/'
        cls.pw=sync_playwright().start()
        cls.browser=(cls.pw.chromium.launch(channel='chrome',headless=True) if os.environ.get('SNEK_BROWSER')=='chromium'
                     else cls.pw.webkit.launch(headless=True))
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.pw.stop();cls.server.shutdown()
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':360,'height':800},device_scale_factor=2,has_touch=True)
        self.context.add_init_script(CLOCK);self.page=self.context.new_page();self.errors=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.goto(self.url);self.advance(0)
    def tearDown(self):
        self.assertEqual(self.errors,[]);self.context.close()
    def advance(self,ms):self.page.evaluate('(ms)=>__advance(ms)',ms)
    def click(self,selector):self.page.eval_on_selector(selector,'e=>e.click()')
    def start(self):self.click('#overlay-buttons button');self.advance(0)
    def snapshot(self):return self.page.evaluate('SnekByteDebug.snapshot()')
    def direction(self,d,kind='pointerdown',**kw):
        self.page.dispatch_event('[data-dir='+d+']',kind,dict(pointerId=1,pointerType='touch',isPrimary=True,button=0,**kw))
    def test_press_before_release_and_no_click_duplicate(self):
        self.start();self.direction('up');self.assertEqual(self.snapshot()['queue'],1)
        self.assertEqual(self.page.locator('#input-ack').inner_text(),'▲')
        self.direction('up','click',detail=1);self.assertEqual(len(self.snapshot()['traces']),1)
        self.advance(84);self.assertEqual(self.snapshot()['game']['snake']['direction'],[0,-1])
        self.assertEqual(self.snapshot()['queue'],0)
    def test_real_mouse_press_steers_before_release(self):
        self.start();b=self.page.locator('[data-dir=up]').bounding_box()
        self.page.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);self.page.mouse.down()
        self.assertEqual(self.snapshot()['queue'],1);self.advance(84)
        self.assertEqual(self.snapshot()['game']['snake']['direction'],[0,-1]);self.page.mouse.up()
        self.assertEqual(self.snapshot()['queue'],0)
    def test_rapid_sequence_and_projected_reverse(self):
        self.start();self.direction('up');self.direction('down');self.direction('left')
        self.assertEqual(self.snapshot()['queue'],2);self.advance(84)
        self.assertEqual(self.snapshot()['game']['snake']['positions'][0],[20,14]);self.advance(84)
        self.assertEqual(self.snapshot()['game']['snake']['positions'][0],[19,14])
        self.assertEqual([t['result'] for t in self.snapshot()['traces']],['accepted','reverse','accepted'])
    def test_swipe_move_segments_without_release(self):
        self.start()
        def event(kind,x,y,pid=5):self.page.dispatch_event('#screen',kind,dict(pointerId=pid,pointerType='touch',isPrimary=True,button=0,clientX=x,clientY=y))
        event('pointerdown',100,100);event('pointermove',101,99);event('pointermove',114,114)
        self.assertEqual(self.snapshot()['queue'],0)
        event('pointermove',100,84);event('pointermove',84,84);self.assertEqual(self.snapshot()['queue'],2)
        event('pointerup',60,60);self.assertEqual(self.snapshot()['queue'],2)
        self.advance(84);self.advance(84);self.assertEqual(self.snapshot()['game']['snake']['direction'],[-1,0])
    def test_pointercancel_capture_and_resize_clear(self):
        self.start()
        for kind in ['pointercancel','lostpointercapture']:
            self.page.dispatch_event('#screen','pointerdown',dict(pointerId=5,button=0,clientX=100,clientY=100))
            self.page.dispatch_event('#screen',kind,dict(pointerId=5))
            self.page.dispatch_event('#screen','pointermove',dict(pointerId=5,clientX=100,clientY=80))
            self.assertEqual(self.snapshot()['queue'],0)
        self.direction('up');self.page.evaluate("dispatchEvent(new Event('resize'))")
        self.assertEqual(self.snapshot()['queue'],0)
    def test_live_speed_rebases_no_reset_and_one_loop(self):
        self.start();self.advance(75);before=self.snapshot()['game']
        self.click('#speed-up');self.assertEqual(self.snapshot()['period'],62.5)
        self.assertEqual(self.snapshot()['game'],before);self.advance(62);self.assertEqual(self.snapshot()['game'],before)
        self.advance(.5);self.assertEqual(self.snapshot()['game']['tick'],1)
        for _ in range(10):self.click('#speed-down');self.click('#speed-up')
        self.assertEqual(self.page.evaluate('__pending()'),1)
        self.assertEqual(json.loads(self.page.evaluate("localStorage.getItem('nuxel-snekbyte-settings-v2')"))['speedIndex'],3)
    def test_slider_pause_resume_speed_and_back(self):
        self.start();self.direction('up');self.click('#settings-button')
        self.assertTrue(self.snapshot()['paused']);self.assertEqual(self.snapshot()['queue'],0)
        self.page.eval_on_selector('#speed-setting',"e=>{e.value='0';e.dispatchEvent(new Event('input'));}")
        self.assertEqual(self.snapshot()['period'],200);self.click('#settings-done');self.advance(1000)
        self.assertEqual(self.snapshot()['game']['tick'],0);self.click('#pause-button');self.advance(200)
        self.assertEqual(self.snapshot()['game']['tick'],1)
        self.page.evaluate('SnekByteUI.handleBack()');self.assertTrue(self.snapshot()['paused'])
        self.page.evaluate('SnekByteUI.handleBack()');self.assertEqual(self.snapshot()['mode'],'menu')
    def test_native_pause_visibility_and_pagehide_no_work(self):
        self.start();self.direction('up');self.page.evaluate('SnekByteUI.requestPause()')
        self.assertEqual(self.page.evaluate('__pending()'),0);self.assertEqual(self.snapshot()['queue'],0)
        self.advance(300000);self.assertEqual(self.snapshot()['game']['tick'],0)
        self.page.evaluate('SnekByteUI.invalidate()');self.advance(0)
        self.assertTrue(self.snapshot()['paused']);self.assertEqual(self.page.evaluate('__pending()'),0)
        self.click('#pause-button');self.advance(84);self.assertEqual(self.snapshot()['game']['tick'],1)
        self.page.evaluate("dispatchEvent(new Event('pagehide'))");self.assertEqual(self.page.evaluate('__pending()'),0)
        self.page.evaluate("dispatchEvent(new Event('pageshow'))");self.advance(0)
        self.assertTrue(self.snapshot()['paused'])
        self.page.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,value:'hidden'});document.dispatchEvent(new Event('visibilitychange'))")
        self.assertEqual(self.page.evaluate('__pending()'),0)
    def test_nuxel_hidden_iframe_lock_and_back_target(self):
        self.page.goto(self.url+'host-test.html')
        self.page.set_content('<div id="lockscreen" hidden></div><iframe id="game" src="/"></iframe>')
        frame=self.page.frame_locator('#game');frame.locator('#overlay-buttons button').first.wait_for()
        game=self.page.frames[1]
        game.evaluate('__advance(0)');self.assertFalse(game.evaluate("document.querySelector('#back-button').hasAttribute('data-action')"))
        game.evaluate("document.querySelector('#overlay-buttons button').click();__advance(0)")
        self.assertEqual(game.evaluate("document.querySelector('#back-button').dataset.action"),'back')
        self.page.eval_on_selector('#game','e=>e.hidden=true')
        game.wait_for_function('SnekByteDebug.snapshot().paused')
        self.assertEqual(game.evaluate('__pending()'),0)
        self.page.eval_on_selector('#game','e=>e.hidden=false');game.evaluate('__advance(0)')
        self.assertTrue(game.evaluate('SnekByteDebug.snapshot().paused'))
        game.evaluate("document.querySelector('#pause-button').click()")
        self.page.eval_on_selector('#lockscreen','e=>e.hidden=false')
        game.wait_for_function('SnekByteDebug.snapshot().paused');self.assertEqual(game.evaluate('__pending()'),0)
    def test_keyboard_repeats_and_assistive_button_activation(self):
        self.start();self.page.keyboard.press('w');self.assertEqual(self.snapshot()['queue'],1)
        self.page.dispatch_event('#screen','keydown',dict(key='a',repeat=True));self.assertEqual(self.snapshot()['queue'],1)
        self.advance(84);self.page.locator('[data-dir=left]').focus();self.page.keyboard.press('Enter')
        self.assertEqual(self.snapshot()['queue'],1)
    def test_preferences_migrate_corrupt_values_without_score_loss(self):
        # Seed outside the running app: its pagehide intentionally saves prefs.
        self.page.goto(self.url+'seed.html')
        self.page.evaluate("localStorage.setItem('nuxel-snekbyte-settings-v1',JSON.stringify({highScore:93,speedIndex:0,wonqMode:false}));localStorage.setItem('nuxel-snekbyte-settings-v2','broken')")
        self.page.goto(self.url);self.advance(0);self.assertEqual(self.page.locator('#best').inner_text(),'93')
        self.assertEqual(self.snapshot()['settings']['speedIndex'],0);self.assertFalse(self.snapshot()['settings']['wonqMode'])
        self.assertTrue(self.snapshot()['settings']['wrapWalls'])
        self.page.goto(self.url+'seed.html')
        self.page.evaluate("localStorage.setItem('nuxel-snekbyte-settings-v2',JSON.stringify({speedIndex:999,highScore:5,wrapWalls:false}))")
        self.page.goto(self.url);self.advance(0);self.assertEqual(self.snapshot()['settings']['speedIndex'],4)
        self.assertEqual(self.page.locator('#best').inner_text(),'93');self.assertFalse(self.snapshot()['settings']['wrapWalls'])
    def test_wrap_toggle_next_round_and_score_persistence_on_menu(self):
        self.start();self.click('#settings-button');self.page.eval_on_selector('#wrap-setting',"e=>{e.checked=false;e.dispatchEvent(new Event('change'));}")
        self.assertTrue(self.snapshot()['settings']['wrapWalls']);self.click('#settings-done');self.click('#back-button')
        self.start();self.assertFalse(self.snapshot()['settings']['wrapWalls'])
        self.page.evaluate('__testGame.score=7');self.page.evaluate('SnekByteUI.requestPause()')
        self.page.reload();self.advance(0);self.assertEqual(self.page.locator('#best').inner_text(),'7')
    def test_layout_portrait_landscape_targets_and_seam_draw(self):
        self.start();self.page.evaluate('__testGame.snake.positions=[[0,10],[39,10],[38,10]];__testGame.snake.length=3;SnekByteUI.invalidate()')
        self.advance(0)
        colors=self.page.evaluate("[10,790,400].map(x=>Array.from(document.querySelector('#screen').getContext('2d').getImageData(x,210,1,1).data).slice(0,3))")
        self.assertEqual(colors[0],[249,224,111]);self.assertEqual(colors[1],[132,239,121])
        self.assertNotEqual(colors[2],[132,239,121])
        for width,height in [(360,800),(800,360)]:
            self.page.set_viewport_size({'width':width,'height':height});self.advance(0)
            for selector in ['[data-dir=up]','[data-dir=left]','#speed-up','#speed-down']:
                b=self.page.locator(selector).bounding_box();self.assertGreaterEqual(b['width'],44);self.assertGreaterEqual(b['height'],44)
                self.assertGreaterEqual(b['x'],0);self.assertLessEqual(b['x']+b['width'],width)
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            self.page.screenshot(path=str(EVIDENCE/f'{os.environ.get("SNEK_BROWSER","webkit")}-{width}x{height}.png'),full_page=True)
    def test_repeated_gameover_retry_pause_has_no_stale_turns_or_extra_loops(self):
        self.start()
        for _ in range(5):
            self.direction('up');self.direction('left')
            self.page.evaluate('__testGame.snake.length=3;__testGame.snake.positions=[[20,15],[20,14],[19,14]]')
            self.advance(84);self.assertEqual(self.snapshot()['mode'],'over');self.assertEqual(self.snapshot()['queue'],0)
            self.assertEqual(self.snapshot()['game']['cause'],'self');self.start()
            self.assertEqual(self.snapshot()['game']['snake']['direction'],[1,0]);self.assertEqual(self.page.evaluate('__pending()'),1)
            self.click('#pause-button');self.advance(0);self.assertEqual(self.page.evaluate('__pending()'),0)
            self.click('#pause-button');self.assertEqual(self.page.evaluate('__pending()'),1)
    def test_service_worker_offline_assets_and_other_caches(self):
        # Runtime uses the real browser cache/network; virtual time only controls game ticks.
        self.page.evaluate("caches.open('other-app-preserve').then(c=>c.put('/unrelated',new Response('keep')))")
        self.page.evaluate('navigator.serviceWorker.ready');self.page.reload();self.advance(0)
        self.page.wait_for_function('!!navigator.serviceWorker.controller')
        # WebKit's automation offline flag fails navigation before SW dispatch.
        # Refuse all server connections instead: assets must actually be cached.
        Handler.offline=True
        try:
            if os.environ.get('SNEK_BROWSER')=='chromium':self.context.set_offline(True)
            self.page.reload();self.advance(0);self.start();self.advance(84)
        finally:Handler.offline=False
        self.assertEqual(self.snapshot()['game']['tick'],1)
        self.assertIn('other-app-preserve',self.page.evaluate('caches.keys()'))
        self.assertIn('nuxel-snekbyte-7000-v2',self.page.evaluate('caches.keys()'))
    def test_a57_service_worker_upgrade_preserves_scores_and_fresh_assets(self):
        context=self.browser.new_context();context.add_init_script(CLOCK)
        context.add_init_script("if(!localStorage.getItem('nuxel-snekbyte-settings-v2'))localStorage.setItem('nuxel-snekbyte-settings-v2',JSON.stringify({speedIndex:1,wonqMode:false,highScore:93,showGrid:false}))")
        page=context.new_page();Handler.legacy=True
        try:
            page.goto(self.url);page.evaluate('navigator.serviceWorker.ready');page.reload()
            page.wait_for_function('!!navigator.serviceWorker.controller')
            self.assertIn('nuxel-snekbyte-5000-v1',page.evaluate('caches.keys()'))
            self.assertEqual(page.evaluate('typeof SnekControls'),'undefined')
            Handler.legacy=False
            page.evaluate('''async () => {
              const changed=new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true}));
              await (await navigator.serviceWorker.getRegistration()).update();await changed;
            }''')
            page.wait_for_function("caches.keys().then(keys=>keys.includes('nuxel-snekbyte-7000-v2')&&!keys.includes('nuxel-snekbyte-5000-v1'))")
            page.reload();page.evaluate('__advance(0)')
            self.assertEqual(page.locator('#best').inner_text(),'93')
            self.assertEqual(page.evaluate('SnekByteDebug.snapshot().period'),125)
            self.assertTrue(page.evaluate('SnekByteDebug.snapshot().settings.wrapWalls'))
            self.assertFalse(page.evaluate('SnekByteDebug.snapshot().settings.wonqMode'))
            self.assertEqual(page.evaluate('typeof SnekControls'),'object')
        finally:Handler.legacy=False;context.close()

if __name__=='__main__':
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    unittest.main(verbosity=2)
