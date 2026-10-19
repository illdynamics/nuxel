exec                                                                                                                                   
/bin/bash -lc 'git diff --check; echo DIFF_CHECK_RC=$?; node --check pwa/nuxel-home/js/app.js && node --check pwa/nuxel-home/js/status-bar.js && echo JS_OK; python3 tools/s10plus/a33/tests/test-button-fsm.py >/tmp/btn-test.log 2>&1; echo btn_rc=$?; tail -2 /tmp/btn-test.log; node tools/s10plus
/a33/tests/launcher-registry-test.js >/tmp/launcher-test.log 2>&1; echo launcher_rc=$?; tail -2 /tmp/launcher-test.log' in /x/nuxel                
 succeeded in 181ms:                                               
btn_rc=0                                                           

== 0 failing check(s), 0 skipped leg(s) ==                                                                                                                                                                                                                                                            launcher_rc=0                    

launcher registry/parity tests passed (1 warning(s))               

codex                                                                                                                                                                                                                                             
## Touchscreen is working — the “frozen GUI” was an app surface covering Home                                                                                                                                                                                                                         
                                                                                                                                                                                                                                                  
I correlated real finger contacts end-to-end. This is not a driver-registration claim:                                                                                                                                                            
                                                                                                                                                                                                                                                                                                      | Time (local) | Physical action | Result |                        
|---|---|---|                                                                                                                                      
| 12:13:01 | tapped Mail tile | raw `TOUCH_POINT` + IRQ → WebKit `pointerdown`/`touchstart` → **`app:launch org.nuxel.Mail`** → Mail rendered |
| 12:23:11 | tapped status bar | WebKit `pointerdown`/`touchstart`/`pointerup`/`click` at `(26,31)` |                   
| 12:23:39 | tapped Calendar tile | **`app:launch org.nuxel.Calendar`** → Calendar rendered |                                                      
                                                                   
Screenshots are in `docs/s10plus-autonomous-boot-repair/TOUCHDOWN/evidence/a34/`:                                                                  
                                 
- `mail-open-physical-tap-1213.png`                                      
- `calendar-open-physical-tap-1223.png`                            
- `home-after-host-home-action.png`                                      
                                                                   
The GUI was **not frozen**: the bridge is presenting at ~22.7 fps with `failures=0`, and the volume OSD appeared within 2 s without any Power press. What happened is that tapping an app opens it fullscreen; the Home launcher is behind it, and the Mail/Calendar pages are sparse and mostly dark.
 That looked like a dead GUI.                                                                                                          
                                                                   
## Fixes deployed                                                        
                                                                   
- **A34 display bridge** — screen-off now writes `bl_power=4` (`FB_BLANK_POWERDOWN`), not just brightness 0. Measured: OFF `bl_power=4`, ON `bl_power=0` in one action.                                                                                                                               
- **A34 button manager** — touch contacts are translated on `SYN_REPORT` after coordinates are known, eliminating the spurious `action=back`. Power now cancels a deferred Bixby short, so a pending `open-terminal` can no longer fire after Power. Edge-back now maps to the host `home` action.
- **Power menu** — **Cancel is now entry 0** and initially selected; Restart/Power Off are gated; Recovery/Download Mode are hard-refused. `MENU_COUNT 11`, `--config-check` reports `decide=ALLOW`.                                                                                                  
- **Quick Settings pull-down** — the existing `qs.js` listened for `gesture:qs`, but nothing dispatched it. The status bar now wires a real vertical pull-down. Deterministic test passes.                                                                                                            
- **Return Home from an app** — the host `home` action now removes the app iframe. `nuxel:action` is listened for on `window` as well as `document` (the host dispatches on window). Verified on-device: launch Mail → `action home` → screenshot changes from the Mail frame (295 colours) back to Ho
me (23,547 colours).             
- **Diagnostics deployed** — `nuxel-wl-snapshot`, `nuxel-usb-input-audit.sh`, `nuxel-display-frame-trace.sh`, `nuxel-button-trace.sh`.
                                                                         
The phone is currently on **Home**, with A34 status bar `0.4.3-a34`, display bridge A34, and button manager `f5f9c6f8…`.                           

## Please run these physical tests now

### Test B — the decisive T9 test                                                                                                      
                                                                         
On Home:                                                                 

1. Tap **Settings** (gear). Wait 3 seconds.
2. Tap the small **✕** at the **top right** to return Home.              
3. Tap **Settings** again, then **swipe up from the bottom edge** to return Home.                                                                                                                                                                 
4. Tap **Terminal**. Wait 3 seconds.                                     
                                                                                                                                                                                                                                                  
Tell me exactly what appeared after each step.                     
                                 
### Test B2 — notification pull-down                  
                                                             
From Home, put a finger on the **top status bar** and drag **down** at least 24 CSS px. Quick Settings should open.                                

From Home, put a finger on the **top status bar** and drag **down** at least 24 CSS px. Quick Settings should open.

### Test C — Power

1. Press **Power once**, wait 3 seconds. The AMOLED should be fully dark.
2. Press **Power once**, wait 3 seconds. Home should return in one press.

### Test D — long-press Power menu

1. Hold **Power** ~2.5 s and release. The menu may take up to 1.5 s to appear.
2. Use **Volume Up/Down** to move; short-press **Power** to confirm.
3. Choose **Cancel** first. Test **Restart** only if you want a reboot.

### Optional Test E — USB mouse/keyboard

Unplug the Fedora cable, plug the mouse/adapter for ~20 s, then the Keychron in wired mode for ~20 s, then reconnect the Fedora cable. The console will re-enumerate; dmesg will show whether the phone attempted host mode.

After you report, I’ll pull the correlated logs and screenshots and mark the evidence ladder through **T9** — or identify the exact remaining layer. The current honest verdict is **TOUCHSCREEN_READY_FOR_OWNER_TEST**, not yet VERIFIED.
## Touchscreen is working — the “frozen GUI” was an app surface covering Home

I correlated real finger contacts end-to-end. This is not a driver-registration claim:

| Time (local) | Physical action | Result |
|---|---|---|
| 12:13:01 | tapped Mail tile | raw `TOUCH_POINT` + IRQ → WebKit `pointerdown`/`touchstart` → **`app:launch org.nuxel.Mail`** → Mail rendered |
| 12:23:11 | tapped status bar | WebKit `pointerdown`/`touchstart`/`pointerup`/`click` at `(26,31)` |
| 12:23:39 | tapped Calendar tile | **`app:launch org.nuxel.Calendar`** → Calendar rendered |

Screenshots are in `docs/s10plus-autonomous-boot-repair/TOUCHDOWN/evidence/a34/`:

- `mail-open-physical-tap-1213.png`
- `calendar-open-physical-tap-1223.png`
- `home-after-host-home-action.png`

The GUI was **not frozen**: the bridge is presenting at ~22.7 fps with `failures=0`, and the volume OSD appeared within 2 s without any Power press. What happened is that tapping an app opens it fullscreen; the Home launcher is behind it, and the Mail/Calendar pages are sparse and mostly dark. That looked like a dead GUI.

## Fixes deployed

- **A34 display bridge** — screen-off now writes `bl_power=4` (`FB_BLANK_POWERDOWN`), not just brightness 0. Measured: OFF `bl_power=4`, ON `bl_power=0` in one action.
- **A34 button manager** — touch contacts are translated on `SYN_REPORT` after coordinates are known, eliminating the spurious `action=back`. Power now cancels a deferred Bixby short, so a pending `open-terminal` can no longer fire after Power. Edge-back now maps to the host `home` action.    
- **Power menu** — **Cancel is now entry 0** and initially selected; Restart/Power Off are gated; Recovery/Download Mode are hard-refused. `MENU_COUNT 11`, `--config-check` reports `decide=ALLOW`.
- **Quick Settings pull-down** — the existing `qs.js` listened for `gesture:qs`, but nothing dispatched it. The status bar now wires a real vertical pull-down. Deterministic test passes.
- **Return Home from an app** — the host `home` action now removes the app iframe. `nuxel:action` is listened for on `window` as well as `document` (the host dispatches on window). Verified on-device: launch Mail → `action home` → screenshot changes from the Mail frame (295 colours) back to Home (23,547 colours).
- **Diagnostics deployed** — `nuxel-wl-snapshot`, `nuxel-usb-input-audit.sh`, `nuxel-display-frame-trace.sh`, `nuxel-button-trace.sh`.

The phone is currently on **Home**, with A34 status bar `0.4.3-a34`, display bridge A34, and button manager `f5f9c6f8…`.

## Please run these physical tests now

### Test B — the decisive T9 test

On Home:

1. Tap **Settings** (gear). Wait 3 seconds.
2. Tap the small **✕** at the **top right** to return Home.
3. Tap **Settings** again, then **swipe up from the bottom edge** to return Home.
4. Tap **Terminal**. Wait 3 seconds.

Tell me exactly what appeared after each step.

### Test B2 — notification pull-down

From Home, put a finger on the **top status bar** and drag **down** at least 24 CSS px. Quick Settings should open.

### Test C — Power

1. Press **Power once**, wait 3 seconds. The AMOLED should be fully dark.
2. Press **Power once**, wait 3 seconds. Home should return in one press.

### Test D — long-press Power menu

1. Hold **Power** ~2.5 s and release. The menu may take up to 1.5 s to appear.
2. Use **Volume Up/Down** to move; short-press **Power** to confirm.
3. Choose **Cancel** first. Test **Restart** only if you want a reboot.

### Optional Test E — USB mouse/keyboard

Unplug the Fedora cable, plug the mouse/adapter for ~20 s, then the Keychron in wired mode for ~20 s, then reconnect the Fedora cable. The console will re-enumerate; dmesg will show whether the phone attempted host mode.

After you report, I’ll pull the correlated logs and screenshots and mark the evidence ladder through **T9** — or identify the exact remaining layer. The current honest verdict is **TOUCHSCREEN_READY_FOR_OWNER_TEST**, not yet VERIFIED.
tokens used
40,063,444
[codeseeq] stopping owned bridge process (pid=2589897)
wicked@dextronux:/x/nuxel$ csf "all tests did nothing^C
wicked@dextronux:/x/nuxel$ vim tests.md
wicked@dextronux:/x/nuxel$ 

