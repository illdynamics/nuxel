/* Nuxel Settings — Theme + Haptics (PWNAGE-30000).
   The theme picker applies immediately (this frame, the launcher and open
   apps share one localStorage document), and haptics toggles are persisted
   through the shared NuxelHaptics settings object. */
(function () {
  'use strict';

  function parentTheme() {
    try {
      if (window.parent && window.parent !== window && window.parent.NuxelTheme) return window.parent.NuxelTheme;
    } catch (e) { /* cross-origin parent */ }
    return window.NuxelTheme;
  }

  var themeBox = document.getElementById('theme-cards');
  if (themeBox && window.NuxelTheme) {
    var current = window.NuxelTheme.current().id;
    window.NuxelTheme.THEMES.forEach(function (t) {
      var card = document.createElement('button');
      card.className = 'theme-card' + (t.id === current ? ' selected' : '');
      card.dataset.theme = t.id;
      card.innerHTML = '<span class="swatch" style="background:' + t.accent + '"></span>' +
        '<span class="tname">' + t.name + '</span>' +
        '<span class="tnote">' + (t.default ? 'Default' : 'Optional') + '</span>';
      card.addEventListener('click', function () {
        var api = parentTheme() || window.NuxelTheme;
        api.apply(t.id);
        document.querySelectorAll('.theme-card').forEach(function (c) {
          c.classList.toggle('selected', c.dataset.theme === t.id);
        });
        document.getElementById('theme-report').textContent = 'Theme applied: ' + t.name + '.';
      });
      themeBox.appendChild(card);
    });
  }

  function haptics() {
    return window.NuxelHaptics ? window.NuxelHaptics.settings() : { enabled: true, keyboard: true, alarm: true, intensity: 30 };
  }
  var hEnabled = document.getElementById('haptics-enabled');
  var hKeyboard = document.getElementById('haptics-keyboard');
  var hAlarm = document.getElementById('haptics-alarm');
  var hIntensity = document.getElementById('haptics-intensity');
  var hOut = document.getElementById('haptics-intensity-val');
  var hTest = document.getElementById('haptics-test');
  var hReport = document.getElementById('haptics-report');

  function syncHaptics() {
    var s = haptics();
    if (hEnabled) hEnabled.checked = s.enabled !== false;
    if (hKeyboard) hKeyboard.checked = s.keyboard !== false;
    if (hAlarm) hAlarm.checked = s.alarm !== false;
    if (hIntensity) hIntensity.value = String(s.intensity == null ? 30 : s.intensity);
    if (hOut) hOut.textContent = (s.intensity == null ? 30 : s.intensity) + '%';
  }
  function saveHaptics() {
    if (!window.NuxelHaptics) return;
    window.NuxelHaptics.update({
      enabled: hEnabled.checked,
      keyboard: hKeyboard.checked,
      alarm: hAlarm.checked,
      intensity: Number(hIntensity.value || 30)
    });
    if (hReport) hReport.textContent = 'Haptics settings saved.';
    if (hOut) hOut.textContent = hIntensity.value + '%';
  }
  [hEnabled, hKeyboard, hAlarm].forEach(function (el) { if (el) el.addEventListener('change', saveHaptics); });
  if (hIntensity) hIntensity.addEventListener('input', function () { if (hOut) hOut.textContent = hIntensity.value + '%'; });
  if (hIntensity) hIntensity.addEventListener('change', saveHaptics);
  if (hTest) {
    hTest.addEventListener('click', function () {
      if (window.NuxelHaptics) window.NuxelHaptics.tap();
      if (hReport) hReport.textContent = 'Test request dispatched (a dispatched request is not proof the motor moved).';
    });
  }
  syncHaptics();

  // headless hook
  window.nuxelThemeSettings = { syncHaptics: syncHaptics, haptics: haptics };
})();
