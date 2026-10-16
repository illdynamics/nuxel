// Nuxel Weather (mission area 30)
//
// OFFLINE BY DESIGN: this app performs no network request at all - there is no
// fetch() of a weather provider anywhere in this file, and the manifest declares
// "network": "none".  Data comes from manual entry or an imported JSON file, and
// is stored in localStorage.  The UI says "manual / offline data" rather than
// implying a live forecast feed.
(function () {
  'use strict';

  var K = 'nuxel-weather';
  var doc = load();

  function load() {
    try {
      var raw = localStorage.getItem(K);
      if (raw) {
        var d = JSON.parse(raw);
        if (d && typeof d === 'object') {
          d.forecast = d.forecast || [];
          return d;
        }
      }
    } catch (e) { /* fall through to a fresh document */ }
    return { place: '', unit: 'C', now: null, forecast: [], updated: null };
  }
  function save() {
    try { localStorage.setItem(K, JSON.stringify(doc)); } catch (e) { /* ignore */ }
  }
  function toast(msg) {
    var t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.add('hidden'); }, 2400);
  }

  var glyphs = { 'Clear': '☀', 'Partly cloudy': '⛅', 'Cloudy': '☁', 'Rain': '🌧',
    'Thunderstorm': '⛈', 'Snow': '❄', 'Fog': '🌫', 'Windy': '💨' };

  function toDisplay(temp, unit) {
    if (temp === null || temp === undefined || isNaN(temp)) return '--';
    if (doc.unit === unit) return round(temp) + '°';
    return round(unit === 'F' ? temp * 9 / 5 + 32 : (temp - 32) * 5 / 9) + '°';
  }
  function round(n) { return Math.round(n * 10) / 10; }

  var els = {
    place: document.getElementById('place'),
    nowTemp: document.getElementById('now-temp'),
    nowCond: document.getElementById('now-cond'),
    nowUpdated: document.getElementById('now-updated'),
    nowSrc: document.getElementById('now-src'),
    nowGlyph: document.getElementById('now-glyph'),
    inTemp: document.getElementById('in-temp'),
    inUnit: document.getElementById('in-unit'),
    inCond: document.getElementById('in-cond'),
    inHum: document.getElementById('in-hum'),
    inWind: document.getElementById('in-wind'),
    forecast: document.getElementById('forecast'),
    chart: document.getElementById('chart'),
    fDay: document.getElementById('f-day'),
    fHigh: document.getElementById('f-high'),
    fLow: document.getElementById('f-low'),
    ioReport: document.getElementById('io-report')
  };

  function renderNow() {
    els.place.value = doc.place || '';
    els.inUnit.value = doc.unit;
    if (doc.now) {
      els.nowTemp.textContent = toDisplay(doc.now.temp, doc.unit === 'C' ? 'C' : 'F');
      els.nowCond.textContent = doc.now.cond + (doc.now.humidity != null ? '  ·  ' + doc.now.humidity + '% humidity' : '') +
        (doc.now.wind != null ? '  ·  ' + doc.now.wind + ' km/h wind' : '');
      els.nowGlyph.textContent = glyphs[doc.now.cond] || '☁';
      els.nowUpdated.textContent = 'Updated ' + new Date(doc.now.at).toLocaleString() + ' (manual entry)';
      els.nowSrc.textContent = 'Source: manual entry - no network provider is configured';
      els.inTemp.value = doc.now.temp; els.inCond.value = doc.now.cond;
      els.inHum.value = doc.now.humidity == null ? '' : doc.now.humidity;
      els.inWind.value = doc.now.wind == null ? '' : doc.now.wind;
    } else {
      els.nowTemp.textContent = '--°';
      els.nowCond.textContent = 'No data yet';
      els.nowGlyph.textContent = '☁';
      els.nowUpdated.textContent = 'Never updated';
      els.nowSrc.textContent = 'Source: manual entry (no network)';
    }
  }

  // Temperatures are stored in Celsius; display follows doc.unit.
  function toCelsius(v, unit) { return unit === 'F' ? (v - 32) * 5 / 9 : v; }

  function renderForecast() {
    doc.forecast.sort(function (a, b) { return a.day.localeCompare(b.day); });
    els.forecast.innerHTML = '';
    els.chart.innerHTML = '';
    var highs = doc.forecast.map(function (d) { return d.high; });
    var lows = doc.forecast.map(function (d) { return d.low; });
    var all = highs.concat(lows).filter(function (v) { return typeof v === 'number' && !isNaN(v); });
    var max = all.length ? Math.max.apply(null, all) : 1;
    var min = all.length ? Math.min.apply(null, all) : 0;
    var span = Math.max(1, max - min);

    doc.forecast.forEach(function (d, i) {
      var li = document.createElement('li');
      var left = document.createElement('div');
      left.textContent = new Date(d.day + 'T12:00:00').toLocaleDateString(undefined,
        { weekday: 'short', month: 'short', day: 'numeric' });
      var mid = document.createElement('div');
      mid.className = 'mono';
      mid.textContent = toDisplay(d.high, 'C') + ' / ' + toDisplay(d.low, 'C') + '  ·  ' + toDisplay(d.high, 'F') + ' / ' + toDisplay(d.low, 'F');
      var actions = document.createElement('div');
      actions.className = 'row';
      var del = document.createElement('button');
      del.textContent = 'Delete';
      del.addEventListener('click', function () {
        doc.forecast.splice(i, 1); save(); renderForecast(); toast('Removed ' + d.day);
      });
      actions.appendChild(del);
      li.appendChild(left); li.appendChild(mid); li.appendChild(actions);
      els.forecast.appendChild(li);

      var wrap = document.createElement('div');
      wrap.className = 'bar-wrap';
      var bar = document.createElement('div');
      bar.className = 'bar';
      var h = 12 + Math.round(((d.high - min) / span) * 74);
      bar.style.height = h + 'px';
      bar.title = d.day + ': ' + toDisplay(d.high, 'C') + ' / ' + toDisplay(d.low, 'C');
      var lab = document.createElement('div');
      lab.className = 'bar-label';
      lab.textContent = new Date(d.day + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'narrow' });
      wrap.appendChild(bar); wrap.appendChild(lab);
      els.chart.appendChild(wrap);
    });

    if (!doc.forecast.length) {
      var p = document.createElement('div');
      p.className = 'li-sub';
      p.textContent = 'No forecast days entered yet.';
      els.chart.appendChild(p);
    }
  }

  document.getElementById('save-place').addEventListener('click', function () {
    doc.place = (els.place.value || '').trim();
    save();
    toast(doc.place ? 'Place set to ' + doc.place : 'Place cleared');
  });

  document.getElementById('save-now').addEventListener('click', function () {
    var raw = parseFloat(els.inTemp.value);
    if (isNaN(raw)) { toast('Enter a temperature first'); return; }
    doc.unit = els.inUnit.value;
    doc.now = {
      temp: toCelsius(raw, doc.unit),
      cond: els.inCond.value,
      humidity: els.inHum.value === '' ? null : Number(els.inHum.value),
      wind: els.inWind.value === '' ? null : Number(els.inWind.value),
      at: Date.now()
    };
    save(); renderNow(); save();
    toast('Current conditions saved locally');
  });

  els.inUnit.addEventListener('change', function () {
    doc.unit = els.inUnit.value;
    save(); renderNow(); renderForecast();
  });

  document.getElementById('f-add').addEventListener('click', function () {
    var day = els.fDay.value;
    var high = parseFloat(els.fHigh.value), low = parseFloat(els.fLow.value);
    if (!day) { toast('Pick a day'); return; }
    if (isNaN(high) || isNaN(low)) { toast('Enter both a high and a low'); return; }
    if (low > high) { toast('The low cannot be above the high'); return; }
    doc.forecast = doc.forecast.filter(function (d) { return d.day !== day; });
    doc.forecast.push({ day: day, high: toCelsius(high, doc.unit), low: toCelsius(low, doc.unit) });
    save(); renderForecast();
    els.fHigh.value = ''; els.fLow.value = '';
    toast('Forecast day saved');
  });

  document.getElementById('export').addEventListener('click', function () {
    var text = JSON.stringify(doc, null, 2);
    try {
      var blob = new Blob([text], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'nuxel-weather.json';
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
      els.ioReport.textContent = 'Exported ' + text.length + ' bytes of local weather data.';
    } catch (e) {
      els.ioReport.textContent = 'Export not available in this view; the data is stored under localStorage key "nuxel-weather".';
    }
  });

  document.getElementById('import').addEventListener('click', function () {
    document.getElementById('file').click();
  });
  document.getElementById('file').addEventListener('change', function (ev) {
    var f = ev.target.files && ev.target.files[0];
    if (!f) return;
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var incoming = JSON.parse(String(reader.result));
        if (!incoming || typeof incoming !== 'object') throw new Error('not an object');
        doc.place = incoming.place || doc.place;
        doc.unit = incoming.unit === 'F' ? 'F' : 'C';
        if (incoming.now) doc.now = incoming.now;
        if (Array.isArray(incoming.forecast)) {
          incoming.forecast.forEach(function (d) {
            if (d && d.day && typeof d.high === 'number' && typeof d.low === 'number') {
              doc.forecast = doc.forecast.filter(function (x) { return x.day !== d.day; });
              doc.forecast.push({ day: d.day, high: d.high, low: d.low });
            }
          });
        }
        save(); renderNow(); renderForecast();
        els.ioReport.textContent = 'Imported ' + f.name + ' (' + doc.forecast.length + ' forecast days).';
        toast('Import complete');
      } catch (e) {
        els.ioReport.textContent = 'Import failed: ' + e.message;
      }
      ev.target.value = '';
    };
    reader.readAsText(f);
  });

  document.getElementById('clear').addEventListener('click', function () {
    doc = { place: doc.place, unit: doc.unit, now: null, forecast: [], updated: null };
    save(); renderNow(); renderForecast();
    toast('Local weather data cleared');
  });

  renderNow();
  renderForecast();

  // headless smoke-test hook
  window.nuxelWeather = { doc: doc, toCelsius: toCelsius, toDisplay: toDisplay, renderForecast: renderForecast };
})();
