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

  function bridgeCall(ns, verb, params) {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
      return window.NuxelBridge.call(ns, verb, params).catch(function (e) { return { success: false, error: e && e.message }; });
    }
    return Promise.resolve({ success: false, offline: true });
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

  async function useMyLocation() {
    statusText(['Asking the Nuxel location provider for a fix…']);
    var res = await bridgeCall('location', 'request', {});
    var lat = res && (res.latitude != null ? res.latitude : res.lat);
    var lon = res && (res.longitude != null ? res.longitude : res.lon);
    if (res && res.success !== false && lat != null && lon != null) {
      await loadPlace({ name: 'Current location', admin: '', latitude: lat, longitude: lon, timezone: res.timezone });
    } else {
      renderCache();
      statusText(['No usable location fix is available.', (res && res.error) ? 'Provider said: ' + res.error : 'Search for a city instead.']);
      toast('Location unavailable — search for a city');
    }
  }

  el.search.addEventListener('click', function () { searchCity(el.city.value.trim()); });
  el.city.addEventListener('keydown', function (e) { if (e.key === 'Enter') searchCity(el.city.value.trim()); });
  el.useLocation.addEventListener('click', useMyLocation);
  el.refresh.addEventListener('click', function () {
    var c = cacheGet();
    if (c && c.latitude != null) loadPlace({ name: c.place.split(',')[0], admin: '', latitude: c.latitude, longitude: c.longitude });
    else searchCity(el.city.value.trim() || 'Eindhoven');
  });
  el.unit.addEventListener('change', function () {
    settings.unit = el.unit.value; saveSettings();
    var c = cacheGet(); if (c) render(c);
  });
  el.autoLoc.addEventListener('change', function () {
    settings.autoLoc = el.autoLoc.checked; saveSettings();
  });

  function esc(s) { var d = document.createElement('div'); d.textContent = String(s == null ? '' : s); return d.innerHTML; }

  renderCache();

  // On first open, if auto-location is enabled, attempt it (honest failure
  // falls back to a manual city prompt rather than inventing coordinates).
  if (settings.autoLoc !== false) {
    useMyLocation();
  }

  window.nuxelWeather = { geocode: geocode, weatherFor: weatherFor, condLabel: condLabel, toDisplayC: toDisplayC };
})();
