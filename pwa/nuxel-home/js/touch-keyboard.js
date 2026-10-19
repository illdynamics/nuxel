// Nuxel Home text keyboard for the headless phone host. Terminal retains its
// PTY keyboard. This edits the focused field and emits normal input events;
// no input device is opened, no keys are injected into another application.
(function (global) {
    'use strict';
    const letters = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
    const symbols = ['1234567890', '@#$%&*()-', '!?.,:/_+='];
    const editable = el => !!el && !el.disabled && !el.readOnly &&
        (el.tagName === 'TEXTAREA' || (el.tagName === 'INPUT' &&
         /^(text|search|email|url|tel|password|number)$/.test(el.type || 'text')));

    function edit(el, key) {
        if (!editable(el)) return false;
        const doc = el.ownerDocument, win = doc.defaultView;
        const start = el.selectionStart === null ? el.value.length : el.selectionStart;
        const end = el.selectionEnd === null ? start : el.selectionEnd;
        let a = start, b = end, text = key, inputType = 'insertText';
        if (key === 'Backspace') {
            inputType = 'deleteContentBackward'; text = '';
            if (a === b && a > 0) {
                // Delete a complete Unicode code point, including surrogate pairs.
                const previous = Array.from(el.value.slice(0, a)).pop();
                a -= previous.length;
            }
        } else if (key === 'Enter') {
            if (el.tagName !== 'TEXTAREA') {
                el.dispatchEvent(new win.KeyboardEvent('keydown', {key:'Enter', bubbles:true, cancelable:true}));
                el.dispatchEvent(new win.KeyboardEvent('keyup', {key:'Enter', bubbles:true}));
                return true;
            }
            text = '\n'; inputType = 'insertLineBreak';
        }
        const before = new win.InputEvent('beforeinput', {inputType, data: text || null, bubbles:true, cancelable:true});
        if (!el.dispatchEvent(before)) return false;
        if (el.maxLength >= 0 && el.value.length - (b - a) + text.length > el.maxLength) return false;
        try { el.setRangeText(text, a, b, 'end'); }
        catch (e) { el.value = el.value.slice(0, a) + text + el.value.slice(b); }
        el.dispatchEvent(new win.InputEvent('input', {inputType, data:text || null, bubbles:true}));
        return true;
    }

    const keyboard = {
        target: null, panel: null, shifted: false, symbols: false,
        enabled: /Nuxel\/.*S10\+/.test((global.navigator && global.navigator.userAgent) || ''),
        attach(doc) {
            if (!doc || doc.__nuxelKeyboard) return;
            doc.__nuxelKeyboard = true;
            doc.addEventListener('focusin', e => {
                if (this.enabled && editable(e.target)) this.show(e.target);
            });
            doc.addEventListener('pointerdown', e => {
                if (this.enabled && editable(e.target)) this.show(e.target);
            }, {passive:true});
        },
        show(target) {
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
            if (target.scrollIntoView) target.scrollIntoView({block:'nearest'});
        },
        hide() {
            if (this.panel) this.panel.hidden = true;
            document.body.classList.remove('touch-keyboard-open');
            this.target = null;
        },
        render() {
            this.panel.replaceChildren();
            const button = (row, label, action, wide) => {
                const key = document.createElement('button');
                key.type = 'button'; key.textContent = label;
                key.setAttribute('aria-label', label);
                if (wide) key.className = 'wide';
                key.addEventListener('click', action);
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
            button(row, 'Space', () => edit(this.target, ' '), true);
            button(row, 'Backspace', () => edit(this.target, 'Backspace'));
            this.panel.appendChild(row);
            const last = document.createElement('div'); last.className = 'key-row';
            button(last, 'Hide keyboard', () => this.hide(), true);
            button(last, 'Enter', () => edit(this.target, 'Enter'), true);
            this.panel.appendChild(last);
        },
        edit,
    };
    global.NuxelTouchKeyboard = keyboard;
    if (typeof document !== 'undefined') {
        keyboard.attach(document);
        document.addEventListener('app:lifecycle', () => keyboard.hide());
    }
})(window);
