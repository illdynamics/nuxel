// Nuxel Calculator (mission area 30 - core application inventory)
//
// Fully offline: a real tokenizer -> shunting-yard -> RPN evaluator lives in
// this file.  There is no eval(), no remote service and no bundled engine that
// would need a network round trip.  History and memory persist in localStorage
// only.  The shared bridge client is included by index.html for the Nuxel
// capability model, but this app declares no capabilities and never calls it.
(function () {
  'use strict';

  var HISTORY_KEY = 'nuxel-calc-history';
  var MEM_KEY = 'nuxel-calc-memory';
  var STATE_KEY = 'nuxel-calc-state';
  var MAX_HISTORY = 60;

  var el = {
    expr: document.getElementById('expr'),
    result: document.getElementById('result'),
    memFlag: document.getElementById('mem-flag'),
    angleFlag: document.getElementById('angle-flag'),
    modeFlag: document.getElementById('mode-flag'),
    history: document.getElementById('history'),
    historyList: document.getElementById('history-list'),
    toast: document.getElementById('toast')
  };

  var state = {
    tokens: [],        // completed token strings
    current: '',       // number currently being typed
    memory: 0,
    lastResult: '0',
    angle: 'DEG',
    mode: 'BASIC',
    history: loadJSON(HISTORY_KEY, [])
  };
  try {
    var mem = localStorage.getItem(MEM_KEY);
    if (mem !== null && mem !== '') state.memory = Number(mem) || 0;
    var saved = JSON.parse(localStorage.getItem(STATE_KEY) || 'null');
    if (saved && (saved.angle === 'DEG' || saved.angle === 'RAD')) state.angle = saved.angle;
  } catch (e) { /* storage unavailable - calculator still works, just without history */ }

  function loadJSON(key, dflt) {
    try {
      var raw = localStorage.getItem(key);
      if (!raw) return dflt;
      var v = JSON.parse(raw);
      return (v === null || v === undefined) ? dflt : v;
    } catch (e) { return dflt; }
  }
  function saveJSON(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
  }

  /* ---------- expression engine ---------- */

  var OPS = {
    '+': { prec: 1, assoc: 'L', arity: 2 },
    '-': { prec: 1, assoc: 'L', arity: 2 },
    '*': { prec: 2, assoc: 'L', arity: 2 },
    '/': { prec: 2, assoc: 'L', arity: 2 },
    '^': { prec: 4, assoc: 'R', arity: 2 }
  };
  var FUNCS = {
    sqrt: function (x) { if (x < 0) throw new Error('sqrt of a negative number'); return Math.sqrt(x); },
    ln: function (x) { if (x <= 0) throw new Error('ln needs a positive number'); return Math.log(x); },
    log: function (x) { if (x <= 0) throw new Error('log needs a positive number'); return Math.log10(x); },
    sin: function (x) { return Math.sin(toRad(x)); },
    cos: function (x) { return Math.cos(toRad(x)); },
    tan: function (x) { return Math.tan(toRad(x)); },
    fact: function (x) {
      if (x < 0 || Math.abs(x - Math.round(x)) > 1e-9) throw new Error('n! needs a whole number >= 0');
      if (x > 170) throw new Error('n! is too large');
      var r = 1; for (var i = 2; i <= x; i++) r *= i; return r;
    }
  };

  function toRad(x) { return state.angle === 'DEG' ? x * Math.PI / 180 : x; }

  // Tokenise the token list built from the keypad into RPN, then evaluate.
  function tokenize(tokens) {
    var out = [];
    for (var i = 0; i < tokens.length; i++) {
      var t = tokens[i];
      if (t === '') continue;
      if (typeof t === 'number') { out.push({ t: 'num', v: t }); continue; }
      if (t === 'x') { out.push({ t: 'op', v: '*' }); continue; }
      if (t === '(' || t === ')') { out.push({ t: 'paren', v: t }); continue; }
      if (OPS[t]) { out.push({ t: 'op', v: t }); continue; }
      if (FUNCS[t]) { out.push({ t: 'func', v: t }); continue; }
      if (t === 'pi') { out.push({ t: 'num', v: Math.PI }); continue; }
      if (t === 'e') { out.push({ t: 'num', v: Math.E }); continue; }
      if (t === '%') { out.push({ t: 'pct', v: '%' }); continue; }
      if (t === 'neg') { out.push({ t: 'neg', v: '-' }); continue; }
      throw new Error('unknown token "' + t + '"');
    }
    // implicit multiplication: 2(3) and 2pi
    var fixed = [];
    for (var j = 0; j < out.length; j++) {
      var prev = out[j - 1], cur = out[j];
      if (prev && (prev.t === 'num' || prev.t === 'paren') && (cur.t === 'num' || cur.t === 'func' || (cur.t === 'paren' && cur.v === '('))) {
        fixed.push({ t: 'op', v: '*' });
      }
      fixed.push(cur);
    }
    return fixed;
  }

  function toRPN(tokens) {
    var output = [], stack = [];
    for (var i = 0; i < tokens.length; i++) {
      var tk = tokens[i];
      if (tk.t === 'num') { output.push(tk); }
      else if (tk.t === 'func' || tk.t === 'neg') { stack.push(tk); }
      else if (tk.t === 'pct') {
        output.push({ t: 'post', v: '%' });
      } else if (tk.t === 'op') {
        var o1 = tk.v;
        while (stack.length) {
          var top = stack[stack.length - 1];
          if (top.t === 'func' || top.t === 'neg' ||
              (top.t === 'op' && (OPS[top.v].prec > OPS[o1].prec ||
                (OPS[top.v].prec === OPS[o1].prec && OPS[o1].assoc === 'L')))) {
            output.push(stack.pop());
          } else break;
        }
        stack.push(tk);
      } else if (tk.t === 'paren') {
        if (tk.v === '(') stack.push(tk);
        else {
          var found = false;
          while (stack.length) {
            var s = stack.pop();
            if (s.t === 'paren' && s.v === '(') { found = true; break; }
            output.push(s);
          }
          if (!found) throw new Error('unbalanced ")"');
          if (stack.length && (stack[stack.length - 1].t === 'func' || stack[stack.length - 1].t === 'neg')) output.push(stack.pop());
        }
      }
    }
    while (stack.length) {
      var rest = stack.pop();
      if (rest.t === 'paren') throw new Error('unbalanced "("');
      output.push(rest);
    }
    return output;
  }

  function evalRPN(rpn) {
    var st = [];
    for (var i = 0; i < rpn.length; i++) {
      var tk = rpn[i];
      if (tk.t === 'num') { st.push(tk.v); continue; }
      if (tk.t === 'post') {
        if (!st.length) throw new Error('nothing to take a percentage of');
        st.push(st.pop() / 100);
        continue;
      }
      if (tk.t === 'neg') {
        if (!st.length) throw new Error('missing a number after ±');
        st.push(-st.pop());
        continue;
      }
      if (tk.t === 'func') {
        if (!st.length) throw new Error('missing a number for ' + tk.v);
        st.push(FUNCS[tk.v](st.pop()));
        continue;
      }
      if (!st.length) throw new Error('missing a number');
      var b = st.pop();
      if (!st.length && tk.v !== '-') throw new Error('missing a number');
      var a = st.length ? st.pop() : 0;
      switch (tk.v) {
        case '+': st.push(a + b); break;
        case '-': st.push(a - b); break;
        case '*': st.push(a * b); break;
        case '/':
          if (b === 0) throw new Error('division by zero');
          st.push(a / b); break;
        case '^': st.push(Math.pow(a, b)); break;
        default: throw new Error('unknown operator ' + tk.v);
      }
    }
    if (st.length !== 1) throw new Error(st.length === 0 ? 'incomplete expression' : 'incomplete expression');
    var r = st[0];
    if (!isFinite(r)) throw new Error('result is not a finite number');
    return r;
  }

  function formatNumber(n) {
    if (Number.isInteger(n) && Math.abs(n) < 1e15) return String(n);
    var s = n.toPrecision(12);
    if (s.indexOf('e') === -1) s = s.replace(/0+$/, '').replace(/\.$/, '');
    return String(Number(s));
  }

  function tokensForCurrent() {
    var t = state.tokens.slice();
    if (state.current !== '') {
      var v = Number(state.current);
      if (isNaN(v)) throw new Error('"' + state.current + '" is not a number');
      t.push(v);
    }
    return t;
  }

  function pretty(tokens) {
    return tokens.map(function (t) {
      if (typeof t === 'number') return formatNumber(t);
      return { '*': '×', '/': '÷', '-': '−', 'pi': 'π', 'x': '×', 'sqrt': '√', 'sqr': 'x²', 'pow': 'xʸ' }[t] || t;
    }).join(' ');
  }

  function render() {
    var shown = state.tokens.slice();
    if (state.current !== '') shown.push(Number(state.current));
    el.expr.textContent = shown.length ? pretty(shown) : '\u00a0';
    el.result.textContent = state.lastResult;
    el.memFlag.classList.toggle('hidden', state.memory === 0);
    el.angleFlag.textContent = state.angle;
    el.modeFlag.textContent = state.mode;
  }

  function showToast(msg) {
    el.toast.textContent = msg;
    el.toast.classList.remove('hidden');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(function () { el.toast.classList.add('hidden'); }, 2200);
  }

  function pushNumber(str) {
    if (str === '.') {
      if (state.current.indexOf('.') >= 0) return;
      state.current = state.current === '' ? '0.' : state.current + '.';
      return;
    }
    if (str === '0' && state.current === '0') return;
    if (state.current.length > 18) return;
    state.current += str;
  }
  function pushToken(t) {
    if (state.current !== '') {
      state.tokens.push(Number(state.current));
      state.current = '';
    }
    var last = state.tokens[state.tokens.length - 1];
    var isValue = (typeof last === 'number') || last === ')' || last === 'pi' || last === 'e';
    if (t === '-' && !isValue) { state.tokens.push('neg'); return; }
    if (!isValue && !(last === undefined && t === '(')) {
      if (OPS[t]) return;             // never start with a binary operator
    }
    state.tokens.push(t);
  }

  function compute(preview) {
    var tokens = tokensForCurrent();
    if (!tokens.length) return null;
    // auto-close open parentheses when evaluating
    var opens = 0;
    tokens.forEach(function (t) { if (t === '(') opens++; if (t === ')') opens--; });
    while (opens > 0) { tokens.push(')'); opens--; }
    var value = evalRPN(toRPN(tokenize(tokens)));
    return { value: value, tokens: tokens };
  }

  function livePreview() {
    // A65-11: the result line must only ever reflect the last COMMITTED
    // evaluation (Equals). Typing "9 + 8" keeps the expression visible and
    // leaves the result unchanged until Equals is pressed — no premature
    // evaluation, no unsafe eval(), the shunting-yard engine still owns
    // precedence when Equals runs.
    render();
  }

  function commit() {
    try {
      var r = compute(false);
      if (r === null) return;
      var res = formatNumber(r.value);
      state.lastResult = res;
      var entry = { expr: pretty(r.tokens), result: res, at: Date.now() };
      state.history.unshift(entry);
      if (state.history.length > MAX_HISTORY) state.history = state.history.slice(0, MAX_HISTORY);
      saveJSON(HISTORY_KEY, state.history);
      renderHistory();
      // The result becomes the start of the next expression (calculator muscle memory).
      state.tokens = []; state.current = '';
      state.tokens = [r.value];
      state.lastResult = res;
      render();
    } catch (err) {
      showToast(err.message || 'cannot evaluate that');
      el.result.textContent = 'Error';
      setTimeout(render, 1200);
    }
  }

  function applyKey(k) {
    switch (k) {
      case 'clear': state.tokens = []; state.current = ''; state.lastResult = '0'; render(); return;
      case 'back':
        if (state.current !== '') { state.current = state.current.slice(0, -1); }
        else if (state.tokens.length) {
          var t = state.tokens.pop();
          if (typeof t === 'number') state.current = String(t);
        }
        livePreview(); render(); return;
      case 'sign':
        if (state.current !== '') { state.current = state.current.charAt(0) === '-' ? state.current.slice(1) : '-' + state.current; }
        else { pushToken('neg'); }
        livePreview(); return;
      case 'percent': pushToken('%'); livePreview(); return;
      case 'paren':
        var opens = 0, closes = 0;
        state.tokens.forEach(function (t) { if (t === '(') opens++; if (t === ')') closes++; });
        var last = state.tokens[state.tokens.length - 1];
        var lastIsValue = (typeof last === 'number') || last === ')' || state.current !== '';
        pushToken((lastIsValue && opens > closes) ? ')' : '(');
        livePreview(); return;
      case 'equals': commit(); return;
      case 'add': pushToken('+'); livePreview(); return;
      case 'sub': pushToken('-'); livePreview(); return;
      case 'mul': pushToken('*'); livePreview(); return;
      case 'div': pushToken('/'); livePreview(); return;
      case 'dot': pushNumber('.'); livePreview(); return;
      case 'sqrt': pushToken('sqrt'); livePreview(); return;
      case 'sqr': pushToken('^'); pushNumber('2'); livePreview(); return;
      case 'pow': pushToken('^'); livePreview(); return;
      case 'inv': pushToken('^'); pushToken('neg'); pushNumber('1'); livePreview(); return;
      case 'fact': pushToken('fact'); livePreview(); return;
      case 'sin': case 'cos': case 'tan': case 'ln': case 'log':
        pushToken(k); livePreview(); return;
      case 'pi': pushToken('pi'); livePreview(); return;
      case 'const-e': pushToken('e'); livePreview(); return;
      case 'angle':
        state.angle = state.angle === 'DEG' ? 'RAD' : 'DEG';
        saveJSON(STATE_KEY, { angle: state.angle });
        showToast('Angle mode: ' + state.angle);
        render(); return;
      case 'm-plus': case 'm-minus': {
        var cur;
        try { var rr = compute(true); cur = rr ? rr.value : Number(state.lastResult); }
        catch (e) { cur = Number(state.lastResult); }
        if (isNaN(cur)) cur = 0;
        state.memory += (k === 'm-plus' ? cur : -cur);
        try { localStorage.setItem(MEM_KEY, String(state.memory)); } catch (e) { /* ignore */ }
        showToast('Memory = ' + formatNumber(state.memory));
        render(); return;
      }
      case 'mr': pushNumber(String(state.memory)); livePreview(); return;
      case 'mc':
        state.memory = 0;
        try { localStorage.removeItem(MEM_KEY); } catch (e) { /* ignore */ }
        showToast('Memory cleared'); render(); return;
      default:
        if (/^[0-9]$/.test(k)) { pushNumber(k); livePreview(); }
    }
  }

  function renderHistory() {
    el.historyList.innerHTML = '';
    if (!state.history.length) {
      var li = document.createElement('li');
      li.textContent = 'No calculations yet.';
      el.historyList.appendChild(li);
      return;
    }
    state.history.forEach(function (h, i) {
      var li = document.createElement('li');
      var re = document.createElement('button');
      re.className = 'link'; re.textContent = 'reuse';
      re.addEventListener('click', function () {
        state.tokens = [Number(h.result)];
        state.current = '';
        state.lastResult = h.result;
        render();
        showToast('Loaded ' + h.result + ' into the display');
      });
      li.appendChild(re);
      var ex = document.createElement('span');
      ex.className = 'h-expr'; ex.textContent = h.expr;
      var rs = document.createElement('span');
      rs.className = 'h-res'; rs.textContent = '= ' + h.result;
      li.appendChild(ex); li.appendChild(rs);
      el.historyList.appendChild(li);
      void i;
    });
  }

  /* ---------- wiring ---------- */

  document.querySelectorAll('.key').forEach(function (b) {
    b.addEventListener('click', function () { applyKey(b.dataset.k); });
  });
  document.querySelectorAll('.mode[data-pad]').forEach(function (m) {
    m.addEventListener('click', function () {
      document.querySelectorAll('.mode[data-pad]').forEach(function (x) { x.classList.remove('active'); });
      m.classList.add('active');
      document.querySelectorAll('.pad').forEach(function (p) { p.classList.remove('active'); });
      document.getElementById('pad-' + m.dataset.pad).classList.add('active');
      state.mode = m.dataset.pad === 'sci' ? 'SCI' : 'BASIC';
      render();
    });
  });
  document.getElementById('copy-btn').addEventListener('click', function () {
    var text = state.lastResult;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { showToast('Copied ' + text); },
        function () { showToast('Clipboard unavailable; the result is ' + text); });
    } else {
      showToast('Clipboard unavailable; the result is ' + text);
    }
  });
  document.getElementById('history-toggle').addEventListener('click', function () {
    var open = el.history.classList.toggle('hidden') === false;
    document.getElementById('history-toggle').setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) renderHistory();
  });
  document.getElementById('history-close').addEventListener('click', function () { el.history.classList.add('hidden'); });
  document.getElementById('history-clear').addEventListener('click', function () {
    state.history = [];
    saveJSON(HISTORY_KEY, state.history);
    renderHistory();
    showToast('History cleared');
  });

  document.addEventListener('keydown', function (ev) {
    var map = { '/': 'div', '*': 'mul', 'x': 'mul', '-': 'sub', '+': 'add', '=': 'equals', 'Enter': 'equals',
      'Backspace': 'back', 'Delete': 'clear', 'Escape': 'clear', '%': 'percent', '(': 'paren', ')': 'paren',
      '.': 'dot', ',': 'dot', '^': 'pow' };
    if (/^[0-9]$/.test(ev.key)) { applyKey(ev.key); ev.preventDefault(); return; }
    if (map[ev.key]) { applyKey(map[ev.key]); ev.preventDefault(); }
  });

  render();
  renderHistory();
  // expose a tiny hook so the headless VM smoke test can drive the engine
  window.nuxelCalculator = {
    press: applyKey,
    evaluate: function (tokens) { return evalRPN(toRPN(tokenize(tokens))); },
    state: state
  };
})();
