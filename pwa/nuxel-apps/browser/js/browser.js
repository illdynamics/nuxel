// Nuxel Browser (mission area 30)
//
// A page viewer, not a search engine.  Policy:
//   * local paths (/pwa/..., about:start, app:<registry id>) always load;
//   * http(s) URLs are BLOCKED until the user enables external navigation, and
//     the app mirrors the manifest's "network": "opt-in" declaration;
//   * history and bookmarks are local (localStorage) and searchable offline.
// No content is fetched by this file on startup; there is no analytics, no
// prefetch and no remote configuration.
(function () {
  'use strict';
  var K_HIST = 'nuxel-browser-history';
  var K_BM = 'nuxel-browser-bookmarks';
  var K_EXT = 'nuxel-browser-external';

  // Static local index so the start page works even with no launcher context.
  var LOCAL_PAGES = [
    { id: 'org.nuxel.Home', name: 'Nuxel Home', url: '/pwa/nuxel-home/index.html' },
    { id: 'nuxel-settings', name: 'Settings', url: '/pwa/nuxel-apps/settings/index.html' },
    { id: 'org.nuxel.Terminal', name: 'Terminal', url: '/pwa/nuxel-apps/terminal/index.html' },
    { id: 'org.nuxel.Notes', name: 'Notes', url: '/pwa/nuxel-apps/notes/index.html' },
    { id: 'org.nuxel.Files', name: 'Files', url: '/pwa/nuxel-apps/files/index.html' },
    { id: 'org.nuxel.Clock', name: 'Clock', url: '/pwa/nuxel-apps/clock/index.html' },
    { id: 'org.nuxel.Calculator', name: 'Calculator', url: '/pwa/nuxel-apps/calculator/index.html' },
    { id: 'org.nuxel.Calendar', name: 'Calendar', url: '/pwa/nuxel-apps/calendar/index.html' },
    { id: 'org.nuxel.Mail', name: 'Mail', url: '/pwa/nuxel-apps/mail/index.html' },
    { id: 'org.nuxel.Photos', name: 'Photos', url: '/pwa/nuxel-apps/photos/index.html' },
    { id: 'org.nuxel.Weather', name: 'Weather', url: '/pwa/nuxel-apps/weather/index.html' },
    { id: 'org.nuxel.Maps', name: 'Maps', url: '/pwa/nuxel-apps/maps/index.html' },
    { id: 'org.nuxel.Recorder', name: 'Recorder', url: '/pwa/nuxel-apps/recorder/index.html' },
    { id: 'org.nuxel.Camera', name: 'Camera', url: '/pwa/nuxel-apps/camera-gallery/index.html' }
  ];

  var els = {
    view: document.getElementById('view'),
    start: document.getElementById('start'),
    blocked: document.getElementById('blocked'),
    blockedUrl: document.getElementById('blocked-url'),
    url: document.getElementById('url'),
    badge: document.getElementById('net-badge'),
    pageInfo: document.getElementById('page-info'),
    locals: document.getElementById('locals'),
    bookmarks: document.getElementById('bookmarks'),
    drawerBookmarks: document.getElementById('drawer-bookmarks'),
    history: document.getElementById('history'),
    drawer: document.getElementById('drawer'),
    allowExternal: document.getElementById('allow-external'),
    toast: document.getElementById('toast')
  };

  var state = {
    history: load(K_HIST, []),
    bookmarks: load(K_BM, []),
    allowExternal: false,
    stack: [],
    pos: -1
  };
  try { state.allowExternal = localStorage.getItem(K_EXT) === '1'; } catch (e) { /* default off */ }
  els.allowExternal.checked = state.allowExternal;

  function load(k, d) {
    try { return JSON.parse(localStorage.getItem(k) || 'null') || d; } catch (e) { return d; }
  }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* ignore */ } }
  function toast(m) {
    els.toast.textContent = m;
    els.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { els.toast.classList.add('hidden'); }, 2400);
  }

  function syncBadge() {
    els.badge.textContent = state.allowExternal ? 'external navigation: enabled (opt-in)' : 'external navigation: blocked';
    els.badge.className = 'badge ' + (state.allowExternal ? 'ok' : 'warn');
  }

  function isExternal(u) { return /^https?:\/\//i.test(u); }
  function isLocal(u) {
    return /^\/pwa\//.test(u) || /^about:/.test(u) || /^app:/.test(u) || /^file:\/\//.test(u);
  }

  function resolve(u) {
    var v = (u || '').trim();
    if (!v) return null;
    if (/^app:/.test(v)) {
      var id = v.slice(4);
      var found = LOCAL_PAGES.filter(function (p) { return p.id === id; })[0];
      if (found) return found.url;
      return null;
    }
    if (v === 'about:start' || v === 'nuxel:start' || v === 'home') return 'about:start';
    if (/^[a-z0-9-]+$/i.test(v) && v.indexOf('.') === -1) {
      // a bare word: treat it as a local app id, never as a search query
      var hit = LOCAL_PAGES.filter(function (p) { return p.id === v || p.name.toLowerCase() === v.toLowerCase(); })[0];
      if (hit) return hit.url;
    }
    if (!/^[a-z]+:/i.test(v)) return v; // relative path -> same origin
    return v;
  }

  function navigate(raw, opts) {
    opts = opts || {};
    var target = resolve(raw);
    if (target === null) { toast('Not a local Nuxel page: ' + raw); return; }
    if (target === 'about:start') { showStart(); return; }
    if (isExternal(target) && !state.allowExternal) {
      els.blockedUrl.textContent = target;
      showPanel('blocked');
      els.url.value = target;
      els.pageInfo.textContent = 'blocked pending opt-in';
      return;
    }
    if (!isLocal(target) && !isExternal(target)) {
      toast('Only local Nuxel pages and (opt-in) http(s) URLs can be opened');
      return;
    }
    els.view.classList.remove('hidden');
    els.start.classList.add('hidden');
    els.blocked.classList.add('hidden');
    els.view.src = target;
    els.url.value = target;
    els.pageInfo.textContent = (isLocal(target) ? 'local' : 'external') + ' · ' + target;
    if (!opts.silent) {
      state.history.unshift({ url: target, at: Date.now() });
      if (state.history.length > 200) state.history = state.history.slice(0, 200);
      save(K_HIST, state.history);
      renderLists();
    }
    if (!opts.noStack) {
      state.stack = state.stack.slice(0, state.pos + 1);
      state.stack.push(target);
      state.pos = state.stack.length - 1;
    }
  }

  function showStart() {
    els.view.classList.add('hidden');
    els.view.removeAttribute('src');
    els.start.classList.remove('hidden');
    els.blocked.classList.add('hidden');
    els.url.value = '';
    els.pageInfo.textContent = 'start page (local)';
  }
  function showPanel(which) {
    els.view.classList.add('hidden');
    els.start.classList.toggle('hidden', which !== 'start');
    els.blocked.classList.toggle('hidden', which !== 'blocked');
  }

  function renderLocals() {
    els.locals.innerHTML = '';
    var registry = null;
    try { registry = window.parent && window.parent.appRegistry; } catch (e) { registry = null; }
    var pages = LOCAL_PAGES.slice();
    if (registry && typeof registry.getAllApps === 'function') {
      try {
        registry.getAllApps().forEach(function (a) {
          if (a.type === 'pwa' && /^\/pwa\//.test(a.url) && !pages.some(function (p) { return p.url === a.url; })) {
            pages.push({ id: a.id, name: a.name, url: a.url });
          }
        });
      } catch (e) { /* launcher registry not readable from here */ }
    }
    pages.forEach(function (p) {
      var d = document.createElement('div');
      d.className = 'local';
      d.textContent = p.name;
      var s = document.createElement('span');
      s.className = 'path';
      s.textContent = p.url;
      d.appendChild(s);
      d.addEventListener('click', function () { navigate(p.url); });
      els.locals.appendChild(d);
    });
    els.pageInfo.textContent = 'start page · ' + pages.length + ' local pages indexed';
  }

  function renderLists() {
    function paint(node, rows, kind) {
      node.innerHTML = '';
      if (!rows.length) {
        var li0 = document.createElement('li');
        li0.textContent = kind === 'bookmarks' ? 'No bookmarks yet.' : 'No history yet.';
        li0.style.cursor = 'default';
        node.appendChild(li0);
        return;
      }
      rows.forEach(function (row, i) {
        var li = document.createElement('li');
        var left = document.createElement('div');
        var name = document.createElement('div');
        name.textContent = row.title || row.url;
        var meta = document.createElement('div');
        meta.className = 'mono';
        meta.textContent = new Date(row.at).toLocaleString() + ' · ' + row.url;
        left.appendChild(name); left.appendChild(meta);
        var right = document.createElement('div');
        var del = document.createElement('button');
        del.textContent = '✕';
        del.addEventListener('click', function (ev) {
          ev.stopPropagation();
          rows.splice(i, 1);
          save(kind === 'bookmarks' ? K_BM : K_HIST, rows);
          state[kind === 'bookmarks' ? 'bookmarks' : 'history'] = rows;
          renderLists();
        });
        right.appendChild(del);
        li.appendChild(left); li.appendChild(right);
        li.addEventListener('click', function () { navigate(row.url); });
        node.appendChild(li);
      });
    }
    var bm = state.bookmarks;
    var hists = state.history.slice(0, 30);
    paint(els.bookmarks, bm, 'bookmarks');
    paint(els.drawerBookmarks, bm, 'bookmarks');
    paint(els.history, hists, 'history');
  }

  document.getElementById('go').addEventListener('click', function () { navigate(els.url.value); });
  els.url.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') navigate(els.url.value); });
  document.getElementById('back').addEventListener('click', function () {
    if (state.pos > 0) { state.pos--; navigate(state.stack[state.pos], { noStack: true, silent: true }); }
  });
  document.getElementById('forward').addEventListener('click', function () {
    if (state.pos < state.stack.length - 1) { state.pos++; navigate(state.stack[state.pos], { noStack: true, silent: true }); }
  });
  document.getElementById('menu').addEventListener('click', function () { els.drawer.classList.remove('hidden'); renderLists(); });
  document.getElementById('drawer-close').addEventListener('click', function () { els.drawer.classList.add('hidden'); });
  els.allowExternal.addEventListener('change', function (ev) {
    state.allowExternal = !!ev.target.checked;
    try { localStorage.setItem(K_EXT, state.allowExternal ? '1' : '0'); } catch (e) { /* ignore */ }
    syncBadge();
    toast(state.allowExternal ? 'External navigation enabled by you (opt-in)' : 'External navigation blocked again');
  });
  document.getElementById('enable-now').addEventListener('click', function () {
    state.allowExternal = true;
    els.allowExternal.checked = true;
    try { localStorage.setItem(K_EXT, '1'); } catch (e) { /* ignore */ }
    syncBadge();
    navigate(els.blockedUrl.textContent);
  });
  document.getElementById('copy-url').addEventListener('click', function () {
    var u = els.blockedUrl.textContent;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(u).then(function () { toast('URL copied'); }, function () { toast(u); });
    } else { toast(u); }
  });
  document.getElementById('clear-bookmarks').addEventListener('click', function () {
    state.bookmarks = []; save(K_BM, state.bookmarks); renderLists(); toast('Bookmarks cleared');
  });
  document.getElementById('clear-history').addEventListener('click', function () {
    state.history = []; save(K_HIST, state.history); renderLists(); toast('History cleared');
  });

  window.addEventListener('load', function () {
    syncBadge();
    renderLocals();
    renderLists();
    showStart();
    // Bookmark the current page with a long press on the menu button.
    document.getElementById('menu').addEventListener('dblclick', function () {
      var cur = els.url.value || window.location.href;
      state.bookmarks.unshift({ url: cur, title: cur, at: Date.now() });
      save(K_BM, state.bookmarks);
      renderLists();
      toast('Bookmarked ' + cur);
    });
  });

  // headless smoke-test hook
  window.nuxelBrowser = {
    state: state, resolve: resolve, isLocal: isLocal, isExternal: isExternal,
    navigate: navigate, renderLocals: renderLocals, localPages: LOCAL_PAGES, sync: syncBadge
  };
})();
