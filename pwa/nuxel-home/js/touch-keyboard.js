// Nuxel Home text keyboard for the headless phone host.
//
// The compositor-owned OSK (phosh-osk-stevia through phoc's
// zwp_input_method_manager_v2 relay) is preferred whenever it is running.  This
// in-page keyboard is only the labelled fallback for a launcher WebKit session
// that has no input-method provider.  It edits the focused field through the
// document's own editing commands and emits the normal beforeinput/input events;
// it never opens an input device and never injects keys into another process.
(function (global) {
    'use strict';
    const letters = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
    const symbols = ['1234567890', '@#$%&*()-', '!?.,:/_+='];
    const INPUT_TYPES = /^(text|search|email|url|tel|password|number)$/;

    function editable(el) {
        if (!el || !el.isConnected || el.disabled || el.readOnly) return false;
        if (el.isContentEditable) return true;
        const tag = String(el.tagName || '').toUpperCase();
        if (tag === 'TEXTAREA') return true;
        return tag === 'INPUT' && INPUT_TYPES.test(String(el.type || 'text').toLowerCase());
    }

    function inputEvent(win, name, options) {
        try { return new win.InputEvent(name, options); }
        catch (e) { return new win.Event(name, { bubbles: true, cancelable: !!options.cancelable }); }
    }

    function keyEvent(win, name, key) {
        try {
            return new win.KeyboardEvent(name, { key, code: key, bubbles: true, cancelable: true });
        } catch (e) {
            return new win.Event(name, { bubbles: true, cancelable: true });
        }
    }

    function focusField(el) {
        if (!el || !el.isConnected) return false;
        try { el.focus({ preventScroll: true }); }
        catch (e) { try { el.focus(); } catch (_) { return false; } }
        // A focus() inside an iframe does not always move the browsing-context
        // focus on WebKitGTK.  Promote the frame only when it is not already the
        // active document; the field itself keeps the caret.
        try {
            const win = el.ownerDocument.defaultView;
            if (win && win.parent !== win && el.ownerDocument.activeElement === el) win.focus();
        } catch (e) { /* cross-origin frames cannot be reached, by design */ }
        return true;
    }

    function selectionOf(el, win) {
        const length = typeof el.value === 'string' ? el.value.length : 0;
        try {
            if (typeof el.selectionStart === 'number') {
                return { start: el.selectionStart, end: typeof el.selectionEnd === 'number' ? el.selectionEnd : el.selectionStart };
            }
        } catch (e) { /* type=number throws in some engines */ }
        const sel = win && win.getSelection ? win.getSelection() : null;
        if (sel && sel.rangeCount && sel.anchorNode && el.contains && el.contains(sel.anchorNode)) {
            return { range: sel.getRangeAt(0), start: 0, end: 0 };
        }
        return { start: length, end: length };
    }

    function setSelection(el, win, position) {
        try {
            if (typeof el.setSelectionRange === 'function' && typeof el.value === 'string') {
                el.setSelectionRange(position, position);
            }
        } catch (e) { /* contenteditable / number inputs */ }
        try {
            const sel = win && win.getSelection ? win.getSelection() : null;
            if (sel && el.contains && el.contains(sel.anchorNode) && sel.modify) {
                // The range already sits at the caret after an editing command.
            }
        } catch (e) { /* no selection API */ }
    }

    function nativeInsert(el, win, text) {
        // WebKit's editing command keeps the native caret, selection, undo stack
        // and password masking coherent.  setRangeText is the deterministic
        // fallback for engines that refuse execCommand on a detached field.
        try {
            if (el.ownerDocument.activeElement === el && win.document.execCommand) {
                if (win.document.execCommand('insertText', false, text)) return true;
            }
        } catch (e) { /* fall through */ }
        return false;
    }

    function insertText(el, text) {
        if (!editable(el)) return false;
        const doc = el.ownerDocument, win = doc.defaultView;
        if (!focusField(el)) return false;
        const sel = selectionOf(el, win);
        const before = inputEvent(win, 'beforeinput', { inputType: 'insertText', data: text, bubbles: true, cancelable: true });
        if (!el.dispatchEvent(before)) return false;
        if (typeof el.maxLength === 'number' && el.maxLength >= 0 && typeof el.value === 'string' &&
            el.value.length - ((sel.end || 0) - (sel.start || 0)) + text.length > el.maxLength) return false;
        let changed = false;
        try {
            if (el.isContentEditable) changed = nativeInsert(el, win, text);
            else if (typeof el.setRangeText === 'function') {
                const a = sel.start, b = sel.end;
                el.setRangeText(text, a, b, 'end');
                changed = true;
            }
        } catch (e) { /* use the value setter below */ }
        if (!changed) {
            if (el.isContentEditable) {
                try { changed = nativeInsert(el, win, text); } catch (e) { changed = false; }
            } else if (typeof el.value === 'string') {
                const a = sel.start, b = sel.end;
                try { el.setRangeText(text, a, b, 'end'); }
                catch (e) {
                    const proto = el.tagName === 'TEXTAREA' ? win.HTMLTextAreaElement.prototype : win.HTMLInputElement.prototype;
                    const setter = Object.getOwnPropertyDescriptor(proto, 'value');
                    const value = el.value.slice(0, a) + text + el.value.slice(b);
                    if (setter && setter.set) setter.set.call(el, value); else el.value = value;
                    setSelection(el, win, a + text.length);
                }
                changed = true;
            }
        }
        if (changed) el.dispatchEvent(inputEvent(win, 'input', { inputType: 'insertText', data: text, bubbles: true }));
        return changed;
    }

    function deleteBackward(el) {
        if (!editable(el)) return false;
        const doc = el.ownerDocument, win = doc.defaultView;
        if (!focusField(el)) return false;
        const sel = selectionOf(el, win);
        const before = inputEvent(win, 'beforeinput', { inputType: 'deleteContentBackward', data: null, bubbles: true, cancelable: true });
        if (!el.dispatchEvent(before)) return false;
        let changed = false;
        if (el.isContentEditable) {
            try { changed = win.document.execCommand('delete', false); } catch (e) { changed = false; }
        } else if (typeof el.value === 'string') {
            let a = sel.start, b = sel.end;
            if (a === b && a > 0) {
                const previous = Array.from(el.value.slice(0, a)).pop();
                a -= previous.length;
            }
            if (a !== b) {
                try { el.setRangeText('', a, b, 'end'); }
                catch (e) {
                    const proto = el.tagName === 'TEXTAREA' ? win.HTMLTextAreaElement.prototype : win.HTMLInputElement.prototype;
                    const setter = Object.getOwnPropertyDescriptor(proto, 'value');
                    const value = el.value.slice(0, a) + el.value.slice(b);
                    if (setter && setter.set) setter.set.call(el, value); else el.value = value;
                    setSelection(el, win, a);
                }
                changed = true;
            }
        }
        if (changed) el.dispatchEvent(inputEvent(win, 'input', { inputType: 'deleteContentBackward', data: null, bubbles: true }));
        return changed;
    }

    function moveCaret(el, direction) {
        if (!editable(el)) return false;
        const doc = el.ownerDocument, win = doc.defaultView;
        if (!focusField(el)) return false;
        if (typeof el.value === 'string') {
            let start = 0, end = 0;
            try { start = el.selectionStart; end = el.selectionEnd; } catch (e) { return false; }
            const pos = direction < 0 ? Math.max(0, start - 1) : Math.min(el.value.length, end + 1);
            setSelection(el, win, pos);
            return true;
        }
        try {
            const sel = win.getSelection();
            if (sel && sel.modify) { sel.modify('move', direction < 0 ? 'backward' : 'forward', 'character'); return true; }
        } catch (e) { /* no selection */ }
        return false;
    }

    function enter(el) {
        if (!editable(el)) return false;
        const doc = el.ownerDocument, win = doc.defaultView;
        if (!focusField(el)) return false;
        if (el.isContentEditable || String(el.tagName).toUpperCase() === 'TEXTAREA') return insertText(el, '\n');
        const down = keyEvent(win, 'keydown', 'Enter');
        if (!el.dispatchEvent(down)) return false;
        el.dispatchEvent(keyEvent(win, 'keyup', 'Enter'));
        const form = el.form;
        if (form) {
            try { if (form.requestSubmit) form.requestSubmit(); else form.submit(); } catch (e) { /* app-owned validation */ }
        }
        return true;
    }

    function edit(el, key) {
        if (!editable(el)) return false;
        let ok = false;
        if (key === 'Backspace') ok = deleteBackward(el);
        else if (key === 'Enter') ok = enter(el);
        else if (key === 'ArrowLeft') ok = moveCaret(el, -1);
        else if (key === 'ArrowRight') ok = moveCaret(el, 1);
        else ok = insertText(el, String(key));
        try {
            // Never log the entered character or a password value.  Length and
            // the logical key class are sufficient to prove delivery on glass.
            const keyboard = global.NuxelTouchKeyboard;
            if (keyboard && keyboard._trace) {
                const length = typeof el.value === 'string' ? el.value.length : 'contenteditable';
                const kind = /^[A-Za-z0-9@#$%&*()\-!?.,:/_+= ]$/.test(String(key)) ? 'text' : String(key);
                keyboard._trace('key kind=' + kind + ' ok=' + (ok ? 1 : 0) + ' len=' + length);
            }
        } catch (e) { /* observation only */ }
        return ok;
    }

    function injectCaretStyle(doc) {
        if (!doc || doc.__nuxelCaretStyle) return;
        try {
            const style = doc.createElement('style');
            style.id = 'nuxel-real-caret-style';
            // This styles the engine's real caret.  It is not a decorative
            // blinking element and it cannot replace focus/selection state.
            style.textContent = 'input,textarea,[contenteditable="true"],[contenteditable=""]{caret-color:#7fe3ff !important;-webkit-user-select:text !important;user-select:text !important;}';
            (doc.head || doc.documentElement).appendChild(style);
            doc.__nuxelCaretStyle = true;
        } catch (e) { /* a cross-origin or not-yet-parsed document */ }
    }

    const keyboard = {
        target: null, panel: null, shifted: false, symbols: false,
        nativeProvider: false, _providerCheckedAt: 0, _providerProbe: null, _showSeq: 0,
        _trace(message) {
            try {
                const diag = global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag;
                if (diag) diag.postMessage('OSK ' + message);
            } catch (e) { /* observation only */ }
        },
        // The software keyboard is needed whenever the Nuxel host is present;
        // keep the S10+ UA fallback for the injected handset browser.
        get enabled() {
            // Whether the fallback may be used at all.  nativeProvider is a
            // separate, asynchronous fact: deciding it before this first probe
            // resolves was how the old blue DOM keyboard appeared ON TOP of the
            // working Stevia OSK (two keyboards for one field).
            return !!(global.NuxelHost && global.NuxelHost.available) || /Nuxel\/.*S10\+/.test((global.navigator && global.navigator.userAgent) || '');
        },
        _applyProviderText(text) {
            const value = String(text || '');
            this.nativeProvider = /(^|\n)(native=1|provider=stevia)(\n|$)/i.test(value);
            return this.nativeProvider;
        },
        detectProvider(force) {
            if (this.nativeProvider) return Promise.resolve(true);
            const now = Date.now();
            if (!force && this._providerProbe && now - this._providerCheckedAt < 5000) return this._providerProbe;
            this._providerCheckedAt = now;
            const fromMarker = () => {
                try {
                    if (global.fetch) {
                        return global.fetch('/pwa/nuxel-home/keyboard-provider.json', { cache: 'no-store' })
                            .then((res) => res.ok ? res.json() : null)
                            .then((doc) => !!(doc && doc.native === true))
                            .catch(() => false);
                    }
                } catch (e) { /* fall through */ }
                return Promise.resolve(false);
            };
            const fromHost = (markerOk) => {
                if (markerOk || this.nativeProvider) return Promise.resolve(this.nativeProvider);
                try {
                    if (global.NuxelHost && global.NuxelHost.statusRead) {
                        return Promise.resolve(global.NuxelHost.statusRead('keyboard-state'))
                            .then((res) => {
                                if (res && res.ok && res.text) return this._applyProviderText(res.text);
                                return this.nativeProvider;
                            }).catch(() => this.nativeProvider);
                    }
                } catch (e) { /* no host marker */ }
                return Promise.resolve(this.nativeProvider);
            };
            this._providerProbe = fromMarker().then((ok) => {
                if (ok) this.nativeProvider = true;
                return fromHost(ok);
            }).then((native) => {
                if (native) {
                    this.nativeProvider = true;
                    try { document.body.classList.add('native-osk'); } catch (e) {}
                    this._discardFallback();
                }
                return native;
            }).catch(() => this.nativeProvider);
            return this._providerProbe;
        },
        _discardFallback() {
            if (this.panel && this.panel.parentNode) this.panel.parentNode.removeChild(this.panel);
            this.panel = null;
            this.target = null;
            try { document.body.classList.remove('touch-keyboard-open'); } catch (e) {}
        },
        attach(doc) {
            if (!doc || doc.__nuxelKeyboard) return;
            doc.__nuxelKeyboard = true;
            injectCaretStyle(doc);
            doc.addEventListener('focusin', e => {
                if (editable(e.target)) this.show(e.target);
            });
            doc.addEventListener('pointerdown', e => {
                if (editable(e.target)) this.show(e.target);
            }, { passive: true });
            doc.addEventListener('focusout', e => {
                // Moving focus inside the keyboard/field keeps it open.  A real
                // focus move to another editable is handled by focusin above.
                if (e.relatedTarget && !editable(e.relatedTarget) && !this._inPanel(e.relatedTarget)) this.target = null;
            });
            // Same-origin application iframes are part of the same WebKit view.
            const scan = () => {
                try {
                    doc.querySelectorAll('iframe').forEach(frame => {
                        try { this.attach(frame.contentDocument); } catch (e) { /* cross-origin */ }
                    });
                } catch (e) { /* no frames yet */ }
            };
            doc.addEventListener('load', e => {
                if (e.target && String(e.target.tagName).toUpperCase() === 'IFRAME') {
                    try { this.attach(e.target.contentDocument); } catch (err) { /* cross-origin */ }
                }
            }, true);
            scan();
        },
        _inPanel(node) { try { return !!(this.panel && node && this.panel.contains(node)); } catch (e) { return false; } },
        show(target) {
            if (!this.enabled || !editable(target)) { this._trace('not-shown enabled=' + this.enabled + ' editable=' + editable(target)); return; }
            const seq = ++this._showSeq;
            const reveal = (native) => {
                if (seq !== this._showSeq) return;   // focus moved on; stale probe
                if (native || this.nativeProvider) {
                    this._trace('native-provider-active');
                    this._discardFallback();
                    return;
                }
                this._showFallback(target);
            };
            const probe = this.detectProvider();
            if (probe && probe.then) probe.then(reveal, () => reveal(false));
            else reveal(this.nativeProvider);
        },
        _showFallback(target) {
            if (this.nativeProvider) { this._discardFallback(); return; }
            this.target = target;
            if (!this.panel) {
                this.panel = document.createElement('div');
                this.panel.className = 'nuxel-touch-keyboard';
                this.panel.setAttribute('role', 'group');
                this.panel.setAttribute('aria-label', 'Touch keyboard');
                // A key press must not blur the text field or lose its selection.
                this.panel.addEventListener('pointerdown', e => e.preventDefault());
                document.body.appendChild(this.panel);
            }
            this.panel.hidden = false;
            this.render();
            document.body.classList.add('touch-keyboard-open');
            this._trace('fallback-show tag=' + String(target.tagName || '?') + ' id=' + String(target.id || '-') + ' rows=' + this.panel.children.length);
            try { target.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (e) { /* optional */ }
        },
        hide() {
            if (this.panel) this.panel.hidden = true;
            document.body.classList.remove('touch-keyboard-open');
            if (this.target) this._trace('hide');
            this.target = null;
        },
        visible() { return !!(this.panel && !this.panel.hidden); },
        haptic() {
            // Centralized haptics path: the shared NuxelHaptics bridge first,
            // then the native host action, then navigator.vibrate.  Rate-limited
            // and disabled-aware so keypress feedback never stacks or blocks typing.
            if (global.NuxelHaptics && typeof global.NuxelHaptics.tap === 'function') {
                global.NuxelHaptics.tap();
                return;
            }
            if (global.NuxelHost && global.NuxelHost.available) global.NuxelHost.action('haptics-tap');
            else { try { if (global.navigator && global.navigator.vibrate) global.navigator.vibrate(12); } catch (e) {} }
        },
        render() {
            if (!this.panel) return;
            this.panel.replaceChildren();
            const button = (row, label, action, wide, aria) => {
                const key = document.createElement('button');
                key.type = 'button';
                key.textContent = label;
                key.setAttribute('aria-label', aria || label);
                if (wide) key.className = 'wide';
                // Physical haptic on DOWN, before the click and its WebKit
                // focus/selection bookkeeping. Keyboard/accessibility clicks
                // without pointerdown still get exactly one haptic request.
                let lastTouchAt = 0;
                key.addEventListener('pointerdown', e => {
                    if (e.button !== undefined && e.button !== 0) return;
                    if (this.target && this.target.isConnected) {
                        lastTouchAt = Date.now();
                        this.haptic();
                    }
                }, { passive: true });
                key.addEventListener('click', () => {
                    if (!this.target || !this.target.isConnected) { this.hide(); return; }
                    if (Date.now() - lastTouchAt > 600) this.haptic();
                    if (action() && this.shifted) { this.shifted = false; this.render(); }
                });
                row.appendChild(key);
            };
            (this.symbols ? symbols : letters).forEach(chars => {
                const row = document.createElement('div'); row.className = 'key-row';
                for (const char of chars) {
                    const value = this.shifted ? char.toUpperCase() : char;
                    button(row, value, () => edit(this.target, value));
                }
                this.panel.appendChild(row);
            });
            const row = document.createElement('div'); row.className = 'key-row';
            button(row, this.shifted ? 'SHIFT' : 'Shift', () => { this.shifted = !this.shifted; this.render(); });
            button(row, this.symbols ? 'ABC' : '123', () => { this.symbols = !this.symbols; this.render(); });
            button(row, '←', () => edit(this.target, 'ArrowLeft'), false, 'Move cursor left');
            button(row, '→', () => edit(this.target, 'ArrowRight'), false, 'Move cursor right');
            button(row, 'Backspace', () => edit(this.target, 'Backspace'), true);
            this.panel.appendChild(row);
            const last = document.createElement('div'); last.className = 'key-row';
            button(last, 'Hide keyboard', () => this.hide(), true);
            button(last, 'Space', () => edit(this.target, ' '), true);
            button(last, 'Enter', () => edit(this.target, 'Enter'), true);
            this.panel.appendChild(last);
        },
        edit,
    };
    global.NuxelTouchKeyboard = keyboard;
    if (typeof document !== 'undefined') {
        keyboard.attach(document);
        keyboard.detectProvider();
        document.addEventListener('app:lifecycle', () => keyboard.hide());
        // A provider can start after the launcher (session ordering). Re-check
        // only while no native provider is known; once Stevia is confirmed there
        // is nothing to poll and the in-page fallback must stay gone.
        try {
            global.setInterval(() => {
                if (!keyboard.nativeProvider) keyboard.detectProvider(true).then((native) => {
                    if (native) keyboard._discardFallback();
                });
            }, 15000);
        } catch (e) {}
    }
})(window);
