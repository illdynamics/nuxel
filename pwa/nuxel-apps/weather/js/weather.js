/* Nuxel Weather (PWNAGE-30000)
 * Live online weather from Open-Meteo.  Geocoding + forecast run over HTTPS.
 * A manual city lookup (including Eindhoven) works even when automatic
 * location is disabled; the last successful result is cached and clearly
 * marked stale when the provider cannot be reached.
 */
(function () {
  'use strict';
  var CACHE_KEY = 'nuxel-weather-cache';
  var SETTINGS_KEY = 'nuxel-weather-settings';
  var GEO_URL = 'https://geocoding-api.open-meteo.com/v1/search';
  var WX_URL = 'https://api.open-meteo.com/v1/forecast';

  var el = {
    city: document.getElementById('city'),
    search: document.getElementById('search'),
    placeResults: document.getElementById('place-results'),
    autoLoc: document.getElementById('auto-loc'),
    useLocation: document.getElementById('use-location'),
    nowTemp: document.getElementById('now-temp'),
    nowPlace: document.getElementById('now-place'),
    nowCond: document.getElementById('now-cond'),
    nowUpdated: document.getElementById('now-updated'),
    nowSrc: document.getElementById('now-src'),
    nowGlyph: document.getElementById('now-glyph'),
    unit: document.getElementById('unit'),
    refresh: document.getElementById('refresh'),
    forecast: document.getElementById('forecast'),
    ioReport: document.getElementById('io-report'),
    netBadge: document.getElementById('net-badge'),
    toast: document.getElementById('toast')
  };

  var settings = loadSettings();
  el.autoLoc.checked = settings.autoLoc !== false;
  el.unit.value = settings.unit === 'F' ? 'F' : 'C';

  function loadSettings() {
    try { var raw = localStorage.getItem(SETTINGS_KEY); return raw ? JSON.parse(raw) : { autoLoc: true, unit: 'C' }; }
    catch (e) { return { autoLoc: true, unit: 'C' }; }
  }
  function saveSettings() {
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch (e) {}
  }
  function cacheGet() {
    try { var raw = localStorage.getItem(CACHE_KEY); return raw ? JSON.parse(raw) : null; }
    catch (e) { return null; }
  }
  function cacheSet(doc) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(doc)); } catch (e) {}
  }

  var codes = {0:'Clear',1:'Mostly clear',2:'Partly cloudy',3:'Cloudy',45:'Fog',48:'Frost fog',
    51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',61:'Light rain',63:'Rain',65:'Heavy rain',
    71:'Light snow',73:'Snow',75:'Heavy snow',80:'Rain showers',81:'Rain showers',82:'Violent rain showers',
    85:'Snow showers',86:'Snow showers',95:'Thunderstorm',96:'Thunderstorm + hail',99:'Thunderstorm + hail'};
  var glyphs = {0:'☀',1:'🌤',2:'⛅',3:'☁',45:'🌫',48:'🌫',51:'🌦',53:'🌧',55:'🌧',61:'🌧',63:'🌧',65:'🌧',
    71:'🌨',73:'🌨',75:'🌨',80:'🌦',81:'🌦',82:'🌧',85:'🌨',86:'🌨',95:'⛈',96:'⛈',99:'⛈'};
  function condLabel(c) { return codes[c] || 'Unknown'; }
  function glyph(c) { return glyphs[c] || '☁'; }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  // permD has ONE decision contract: `check` answers either a JSON decision
  // ({capability:{decision:"allow"|"deny"}}) or a CLI envelope
  // ({success:true, stdout:"allowed: <app> <cap> ..."}).  A CLI success is not
  // an object with `granted`, and treating it as "not granted" used to send a
  // perfectly allowed check down the request path.
  function permAllowed(res) {
    if (!res || typeof res !== 'object') return false;
    if (res.granted === true) return true;
    if (res.denied === true || res.granted === false) return false;
    if (res.success === true && typeof res.stdout === 'string') {
      return /^\s*allowed:/i.test(res.stdout);
    }
    return false;
  }

  function permDenied(res) {
    if (!res || typeof res !== 'object') return false;
    if (res.denied === true || res.granted === false) return true;
    if (res.success === false) return true;
    if (typeof res.stdout === 'string' && /^\s*denied:/i.test(res.stdout)) return true;
    return false;
  }

  function bridgeApi() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    try { if (window.parent && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    return null;
  }

  function bridgeCall(ns, verb, params) {
    var b = bridgeApi();
    if (b) {
      return b.call(ns, verb, params).catch(function (e) { return { success: false, error: e && e.message }; });
    }
    return Promise.resolve({ success: false, offline: true });
  }

  // Run a bridge RPC only after the shared client has finished initialising.
  // The client used to answer from mock mode ("provider unavailable") when an
  // early call raced its own boot; this wrapper makes the ordering explicit and
  // retries once if that race still happened.  A real refusal is not retried.
  function bridgeCallReady(ns, verb, params) {
    var b = bridgeApi();
    var ready = (b && typeof b.whenReady === 'function')
      ? Promise.resolve(b.whenReady(15000)) : Promise.resolve(true);
    return ready.then(function () { return bridgeCall(ns, verb, params); })
      .then(function (res) {
        var raced = res && res.success === false && res.offline === true &&
          /provider is unavailable/.test(String(res.error || ''));
        if (!raced || !b) return res;
        if (b.mockMode) b.mockMode = false;
        return bridgeCall(ns, verb, params);
      });
  }

  // Ask permD for this app's own location read grant.  The grant is per app and
  // revocable in Settings > Permissions; a refusal is surfaced, never assumed.
  function requestLocationAccess() {
    var b = bridgeApi();
    if (!b) return Promise.resolve({ granted: false, error: 'Nuxel bridge is not available in this view' });
    // Wait (bounded) for the shared bridge module to finish INITIALISING.  Its
    // `call()` reports "provider unavailable" until _init resolves, which is
    // NOT a permission denial and must not be shown as one.
    function ready(n) {
      if (b && typeof b.whenReady === 'function') return b.whenReady(15000);
      var settled = b && (b.connected || b.mockMode || b.versionMismatch);
      var initing = !!(b && b._initPromise) && !settled;
      if (!initing || n <= 0) return Promise.resolve();
      return sleep(250).then(function () { return ready(n - 1); });
    }
    return ready(40).then(function () {
      return bridgeCallReady('permissions', 'check', { capability: 'location:read' });
    }).then(function (check) {
      if (permAllowed(check)) return { granted: true };
      if (permDenied(check)) {
        return { granted: false, error: 'Location read is denied for Weather (enable it in Settings > Permissions)' };
      }
      if (!b.requestCapability) return { granted: false, error: 'This build cannot request permissions' };
      return Promise.resolve(b.requestCapability('location:read', 'Show weather for my current location'))
        .then(function (res) {
          if (res === true || (res && res.granted === true)) return { granted: true };
          return { granted: false, error: (res && (res.detail || res.error)) || 'Location read was not granted' };
        }, function (e) {
          return { granted: false, error: (e && e.message) || 'Location read request failed' };
        });
    }, function (e) {
      return { granted: false, error: (e && e.message) || 'Location permission check failed' };
    });
  }

  // Enabling the global location policy is a device-wide action; Weather only
  // does it on an explicit owner tap and only when it holds location:manage.
  function ensureLocationPolicy() {
    return bridgeCallReady('location', 'get-status', {}).then(function (status) {
      if (status && status.enabled) return { enabled: true };
      return bridgeCall('permissions', 'check', { capability: 'location:manage' }).then(function (check) {
        if (!permAllowed(check)) {
          return { enabled: false, error: 'Location control is not granted for Weather (Settings > Permissions)' };
        }
        return bridgeCall('location', 'set-enabled', { enabled: true }).then(function (res) {
          if (res && res.success === true && res.enabled !== false) return { enabled: true };
          return { enabled: false, error: (res && (res.error || res.detail)) || 'Location policy did not confirm' };
        });
      });
    });
  }

  function fetchJson(url, timeoutMs) {
    var ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, timeoutMs || 12000);
    return fetch(url, { signal: ctl && ctl.signal, headers: { 'Accept': 'application/json' } })
      .then(function (r) {
        clearTimeout(timer);
        if (!r.ok) throw new Error('provider HTTP ' + r.status);
        return r.json();
      })
      .catch(function (e) {
        clearTimeout(timer);
        throw new Error((e && e.name === 'AbortError') ? 'request timed out' : ('network error: ' + (e && e.message)));
      });
  }

  function toast(msg) {
    el.toast.textContent = msg;
    el.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.toast.classList.add('hidden'); }, 2400);
  }

  function statusText(lines) { el.ioReport.textContent = lines.join('\n'); }

  function round(n) { return Math.round(n * 10) / 10; }
  function toDisplayC(v) { return settings.unit === 'F' ? round(v * 9 / 5 + 32) : round(v); }
  function unitChar() { return settings.unit === 'F' ? '°F' : '°C'; }

  async function geocode(name) {
    var url = GEO_URL + '?name=' + encodeURIComponent(name) + '&count=5&language=en&format=json';
    var doc = await fetchJson(url);
    var results = doc && doc.results;
    if (!Array.isArray(results) || !results.length) return [];
    return results.map(function (r) {
      return { name: r.name, admin: [r.admin1, r.admin2, r.country].filter(Boolean).join(', '),
               latitude: r.latitude, longitude: r.longitude, timezone: r.timezone };
    });
  }

  async function weatherFor(place) {
    var url = WX_URL + '?latitude=' + encodeURIComponent(place.latitude) +
      '&longitude=' + encodeURIComponent(place.longitude) +
      '&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m' +
      '&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto&forecast_days=7';
    var doc = await fetchJson(url);
    var cur = doc && doc.current;
    var daily = doc && doc.daily;
    if (!cur || !daily) throw new Error('provider returned no current conditions');
    return {
      place: place.name + (place.admin ? ', ' + place.admin : ''),
      latitude: place.latitude,
      longitude: place.longitude,
      timezone: doc.timezone || place.timezone,
      source: place.source || 'place',
      current: {
        temp_c: cur.temperature_2m,
        feels_c: cur.apparent_temperature,
        humidity: cur.relative_humidity_2m,
        wind: cur.wind_speed_10m,
        code: cur.weather_code,
        at: Date.now()
      },
      forecast: daily.time.map(function (day, i) {
        return { day: day, high_c: daily.temperature_2m_max[i], low_c: daily.temperature_2m_min[i], code: daily.weather_code[i] };
      })
    };
  }

  function render(data) {
    el.nowPlace.textContent = data.place;
    el.nowTemp.textContent = toDisplayC(data.current.temp_c) + '°';
    el.nowCond.textContent = condLabel(data.current.code) +
      (data.current.humidity != null ? ' · ' + data.current.humidity + '% humidity' : '') +
      (data.current.wind != null ? ' · ' + round(data.current.wind) + ' km/h wind' : '');
    el.nowGlyph.textContent = glyph(data.current.code);
    el.nowUpdated.textContent = 'Updated ' + new Date(data.current.at).toLocaleString() +
      (data.current.at + 3 * 3600 * 1000 < Date.now() ? ' · stale cache' : '');
    el.nowSrc.textContent = 'Source: Open-Meteo (HTTPS) · ' + (data.timezone || 'auto timezone');
    el.netBadge.textContent = 'online';
    el.netBadge.classList.remove('warn');

    el.forecast.innerHTML = '';
    data.forecast.forEach(function (d) {
      var li = document.createElement('li');
      var day = document.createElement('span');
      day.textContent = new Date(d.day + 'T12:00:00').toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
      var cond = document.createElement('span');
      cond.textContent = glyph(d.code) + ' ' + condLabel(d.code);
      var temps = document.createElement('span');
      temps.className = 'mono';
      temps.textContent = toDisplayC(d.high_c) + '° / ' + toDisplayC(d.low_c) + '°';
      li.appendChild(day); li.appendChild(cond); li.appendChild(temps);
      el.forecast.appendChild(li);
    });
  }

  function renderCache() {
    var c = cacheGet();
    if (!c) {
      el.nowPlace.textContent = 'No cached weather';
      el.nowTemp.textContent = '--°';
      el.nowCond.textContent = 'Offline — no cached result';
      el.nowUpdated.textContent = 'Never updated';
      el.netBadge.textContent = 'offline';
      el.netBadge.classList.add('warn');
      el.forecast.innerHTML = '';
      return;
    }
    render(c);
    el.netBadge.textContent = 'offline · showing cache';
    el.netBadge.classList.add('warn');
  }

  async function searchCity(name) {
    if (!name) { toast('Enter a city name'); return; }
    el.placeResults.innerHTML = '';
    statusText(['Searching for “' + name + '”…']);
    try {
      var results = await geocode(name);
      if (!results.length) {
        statusText(['No matching place found for “' + name + '”.']);
        return;
      }
      el.placeResults.innerHTML = results.map(function (r, i) {
        return '<button data-i="' + i + '" class="result">' + esc(r.name + (r.admin ? ', ' + r.admin : '')) + '</button>';
      }).join('');
      el.placeResults.querySelectorAll('.result').forEach(function (b) {
        b.addEventListener('click', function () { loadPlace(results[+b.dataset.i]); });
      });
      statusText(['Found ' + results.length + ' place(s). Choose one to load its weather.']);
    } catch (e) {
      renderCache();
      statusText(['Lookup failed: ' + e.message, 'Showing the last cached result if present.']);
      el.netBadge.textContent = 'offline';
      el.netBadge.classList.add('warn');
    }
  }

  async function loadPlace(place) {
    el.placeResults.innerHTML = '';
    statusText(['Loading weather for ' + place.name + '…']);
    try {
      var data = await weatherFor(place);
      cacheSet(data);
      render(data);
      statusText(['Loaded ' + data.place + '.', 'Provider: Open-Meteo (HTTPS).']);
    } catch (e) {
      renderCache();
      statusText(['Weather fetch failed: ' + e.message, 'Showing the last cached result if present.']);
    }
  }

  function locationFix(res) {
    var lat = res && (res.latitude != null ? res.latitude : res.lat);
    var lon = res && (res.longitude != null ? res.longitude : res.lon);
    if (res && res.success !== false && lat != null && lon != null) return { lat: lat, lon: lon };
    return null;
  }


  // Poll the SAME acquisition GeoClue was asked to start.  Only a provider
  // 'fixed' state is accepted; a slow first fix (cold Wi-Fi/GNSS) is waited for
  // a bounded time and never replaced with an invented coordinate.
  async function acquireFix(timeoutMs) {
    var deadline = Date.now() + (timeoutMs || 45000);
    var last = null;
    while (Date.now() < deadline) {
      last = await bridgeCallReady('location', 'acquire', {});
      var fix = locationFix(last);
      if (fix) return { fix: fix, res: last };
      if (last && last.error_code === 'CAPABILITY_DENIED') return { denied: true, res: last };
      if (last && (last.error_code === 'LOCATION_DISABLED' || last.enabled === false)) return { disabled: true, res: last };
      statusText(['Waiting for a provider fix…',
        (last && last.state) ? ('state: ' + last.state) : 'no provider answer yet']);
      await sleep(1500);
    }
    return { fix: null, res: last };
  }

  async function useMyLocation() {
    var btn = el.useLocation;
    if (btn) btn.disabled = true;
    try {
      statusText(['Asking the Nuxel location provider for a fix…']);
      var access = await requestLocationAccess();
      if (!access.granted) {
        renderCache();
        statusText(['Location permission is required.', access.error]);
        toast('Location unavailable — search for a city');
        return;
      }
      var policy = await ensureLocationPolicy();
      if (!policy.enabled) {
        renderCache();
        statusText(['Location is switched off.', policy.error || 'Turn on Location to use your current position.']);
        toast('Location is off — search for a city');
        return;
      }
      var got = await acquireFix(45000);
      var res = got.res;
      if (got.denied) {
        var retry = await requestLocationAccess();
        if (retry.granted) {
          got = await acquireFix(45000);
          res = got.res;
        } else {
          res = { error: retry.error || res.error };
        }
      }
      if (got.disabled) {
        renderCache();
        statusText(['Location was switched off while waiting.', 'Turn Location on and try again.']);
        toast('Location is off');
        return;
      }
      var fix = got.fix;
      if (fix) {
        await loadPlace({ name: 'Current location', admin: '', latitude: fix.lat, longitude: fix.lon,
                          timezone: res.timezone, source: 'provider' });
        if (el.nowPlace) el.nowPlace.title = 'Provider fix: ' + (res.fix_source || 'provider') +
          (res.accuracy != null ? ' ±' + Math.round(res.accuracy) + ' m' : '');
      } else {
        renderCache();
        statusText(['No usable location fix is available.',
          (res && res.error) ? 'Provider said: ' + res.error : 'Search for a city instead.',
          'Weather never invents coordinates; a manual city search always works.']);
        toast('Location unavailable — search for a city');
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  el.search.addEventListener('click', function () { searchCity(el.city.value.trim()); });
  el.city.addEventListener('keydown', function (e) { if (e.key === 'Enter') searchCity(el.city.value.trim()); });
  if (el.useLocation) el.useLocation.addEventListener('click', useMyLocation);
  el.refresh.addEventListener('click', function () {
    var c = cacheGet();
    if (c && c.latitude != null) {
      // A "Current location" result re-asks the provider only when the owner
      // has auto-location enabled; otherwise the exact cached coordinates are
      // re-fetched (they are real provider/picked coordinates, not invented).
      if (c.source === 'provider' && settings.autoLoc !== false) { useMyLocation(); return; }
      loadPlace({ name: c.place.split(',')[0], admin: '', latitude: c.latitude, longitude: c.longitude });
    } else searchCity(el.city.value.trim() || 'Eindhoven');
  });
  el.unit.addEventListener('change', function () {
    settings.unit = el.unit.value; saveSettings();
    var c = cacheGet(); if (c) render(c);
  });
  el.autoLoc.addEventListener('change', function () {
    settings.autoLoc = el.autoLoc.checked; saveSettings();
  });

  function esc(s) { var d = document.createElement('div'); d.textContent = String(s == null ? '' : s); return d.innerHTML; }

  function bootWeather() {
    renderCache();
    // On first open, if auto-location is enabled, attempt it (honest failure
    // falls back to a manual city prompt rather than inventing coordinates).
    if (settings.autoLoc !== false) useMyLocation();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bootWeather, { once: true });
  else bootWeather();

  window.nuxelWeather = { geocode: geocode, weatherFor: weatherFor, condLabel: condLabel, toDisplayC: toDisplayC };
})();
