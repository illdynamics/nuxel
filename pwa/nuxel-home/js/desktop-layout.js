/* Nuxel unified desktop layout (PWNAGE-84000).
 *
 * One authoritative, DOM-free model owns app icons and widgets.  Storage uses
 * ZERO-BASED desktops and grid coordinates.  CSS Grid is only a renderer; every
 * position has already been collision-checked here before it reaches the DOM.
 */
(function (global) {
  'use strict';
  var KEY = 'nuxel.desktopLayout.v1';
  var SCHEMA = 1;
  var MAX_DESKTOPS = 8;
  var MAX_SPAN = 6;

  function clampInt(value, lo, hi, fallback) {
    value = Number(value);
    if (!Number.isFinite(value)) return fallback;
    return Math.max(lo, Math.min(hi, Math.round(value)));
  }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function idOf(value) { return String(value || '').replace(/[^A-Za-z0-9._:-]/g, '-').slice(0, 120); }
  function appEntityId(appId) { return 'app:' + idOf(appId); }

  class DesktopLayout {
    constructor(saved, options) {
      options = options || {};
      this.columns = clampInt(options.columns, 3, 6, 4);
      this.rows = clampInt(options.rows, 4, 7, 5);
      this.desktopCount = clampInt(options.desktopCount, 1, MAX_DESKTOPS, 2);
      this.migration = {};
      this.widgetsEnabled = !saved || saved.widgets_enabled !== false;
      this.entities = this._migrate(saved, options);
      this._normalise();
    }

    _migrate(saved, options) {
      if (saved && Number(saved.schema_version) === SCHEMA && Array.isArray(saved.entities)) {
        this.migration = saved.migration || { source: 'schema-1' };
        return clone(saved.entities);
      }
      var out = [];
      var appOrder = Array.isArray(options.appOrder) ? options.appOrder.slice() : [];
      var assignments = options.pageAssignments || {};
      var legacyWidgets = options.legacyWidgets && Array.isArray(options.legacyWidgets.items)
        ? options.legacyWidgets.items : [];
      // Reserve legacy widgets first so apps flow around them.
      legacyWidgets.forEach(function (w, index) {
        if (!w || typeof w !== 'object' || !w.type) return;
        out.push({
          id: idOf(w.id || ('widget-' + index + '-' + Date.now().toString(36))),
          type: 'widget',
          widget_type: String(w.type),
          desktop: clampInt(Number(w.desktop) - 1, 0, MAX_DESKTOPS - 1, 0),
          x: clampInt(w.x, 0, 5, 0),
          y: clampInt(w.y, 0, 6, 0),
          w: clampInt(w.w, 1, 4, 2),
          h: clampInt(w.h, 1, 4, 2),
          config: clone(w)
        });
      });
      var order = appOrder.length ? appOrder : (options.apps || []);
      order.forEach(function (appId) {
        if (!appId) return;
        var desktop = clampInt(assignments[appId], 0, MAX_DESKTOPS - 1, 0);
        // A legacy install can legitimately carry more shortcuts than the
        // configured grids hold.  Expand the desktop count and keep every
        // shortcut instead of dereferencing a null placement (the P84000 boot
        // regression: one extra app left the launcher without a dock or swipe
        // handlers because _migrate threw before _renderAll ran).
        var slot = this._placeFree(desktop, 1, 1, 0, 0, out);
        out.push({
          id: appEntityId(appId), type: 'app', ref: String(appId),
          desktop: slot.desktop, x: slot.x, y: slot.y, w: 1, h: 1
        });
      }, this);
      this.migration = {
        source: 'legacy',
        from_widgets: legacyWidgets.length,
        from_apps: out.filter(function (e) { return e.type === 'app'; }).length
      };
      return out;
    }

    _normalise() {
      var seen = new Set();
      var out = [];
      this.entities.forEach(function (entity) {
        if (!entity || !entity.id || seen.has(entity.id)) return;
        if (entity.type !== 'app' && entity.type !== 'widget' && entity.type !== 'folder') return;
        seen.add(entity.id);
        entity.desktop = clampInt(entity.desktop, 0, this.desktopCount - 1, 0);
        entity.w = clampInt(entity.w, 1, entity.type === 'widget' ? this.columns : 1, 1);
        entity.h = clampInt(entity.h, 1, entity.type === 'widget' ? this.rows : 1, 1);
        entity.x = clampInt(entity.x, 0, Math.max(0, this.columns - entity.w), 0);
        entity.y = clampInt(entity.y, 0, Math.max(0, this.rows - entity.h), 0);
        out.push(entity);
      }, this);
      this.entities = out;
      for (var d = 0; d < this.desktopCount; d++) this._reflowDesktop(d);
    }

    _occupancy(entities, desktop, columns, rows) {
      var map = new Map();
      columns = columns || this.columns;
      rows = rows || this.rows;
      (entities || this.entities).forEach(function (e) {
        if (!e || e.desktop !== desktop) return;
        for (var yy = e.y; yy < e.y + e.h; yy++) {
          for (var xx = e.x; xx < e.x + e.w; xx++) {
            if (xx >= 0 && yy >= 0 && xx < columns && yy < rows) map.set(xx + ',' + yy, e.id || e.ref || '?');
          }
        }
      });
      return map;
    }

    occupancy(desktop, ignoreId) {
      var map = new Map();
      var d = clampInt(desktop, 0, this.desktopCount - 1, 0);
      this.entities.forEach(function (e) {
        if (e.desktop !== d || e.id === ignoreId) return;
        for (var yy = e.y; yy < e.y + e.h; yy++) {
          for (var xx = e.x; xx < e.x + e.w; xx++) {
            if (xx >= 0 && yy >= 0 && xx < this.columns && yy < this.rows) map.set(xx + ',' + yy, e.id);
          }
        }
      }, this);
      return map;
    }

    canPlace(desktop, x, y, w, h, ignoreId) {
      var d = clampInt(desktop, 0, this.desktopCount - 1, 0);
      w = clampInt(w, 1, this.columns, 1);
      h = clampInt(h, 1, this.rows, 1);
      if (x < 0 || y < 0 || x + w > this.columns || y + h > this.rows) return false;
      var occ = this.occupancy(d, ignoreId);
      for (var yy = y; yy < y + h; yy++) {
        for (var xx = x; xx < x + w; xx++) if (occ.has(xx + ',' + yy)) return false;
      }
      return true;
    }

    findFree(desktop, w, h, ignoreId, startX, startY) {
      return this.findFreeWith(desktop, w, h, startX || 0, startY || 0, ignoreId, this.entities);
    }

    findFreeWith(desktop, w, h, startX, startY, ignoreId, entities) {
      var columns = this.columns, rows = this.rows;
      w = clampInt(w, 1, columns, 1);
      h = clampInt(h, 1, rows, 1);
      var occ = this._occupancy((entities || this.entities).filter(function (e) { return e.id !== ignoreId; }),
                                desktop, columns, rows);
      var sy = clampInt(startY, 0, rows - h, 0);
      var sx = clampInt(startX, 0, columns - w, 0);
      var best = [];
      for (var y = sy; y <= rows - h; y++) {
        for (var x = sx; x <= columns - w; x++) {
          var ok = true;
          for (var yy = y; yy < y + h && ok; yy++) {
            for (var xx = x; xx < x + w; xx++) {
              if (occ.has(xx + ',' + yy)) { ok = false; break; }
            }
          }
          if (ok) best.push({ x: x, y: y, distance: Math.abs(x - sx) + Math.abs(y - sy) });
        }
      }
      // Keep normal reading order when the preferred area is already full.
      if (!best.length) {
        for (var ay = 0; ay <= rows - h; ay++) {
          for (var ax = 0; ax <= columns - w; ax++) {
            var free = true;
            for (var by = ay; by < ay + h && free; by++) {
              for (var bx = ax; bx < ax + w; bx++) if (occ.has(bx + ',' + by)) { free = false; break; }
            }
            if (free) return { x: ax, y: ay };
          }
        }
      }
      best.sort(function (a, b) { return a.distance - b.distance || a.y - b.y || a.x - b.x; });
      return best.length ? { x: best[0].x, y: best[0].y } : null;
    }

    /* Place an entity without ever returning null.  Migration runs before the
       first render, so a full grid must expand to another desktop (or degrade
       to a legal cell at the eight-desktop ceiling), never throw. */
    _placeFree(desktop, w, h, startX, startY, entities) {
      var target = clampInt(desktop, 0, this.desktopCount - 1, 0);
      var spot = this.findFreeWith(target, w, h, startX || 0, startY || 0, null, entities);
      // An earlier overflow may already have added a desktop that still has
      // empty cells.  Fill those before growing the page count again.
      for (var d = 0; !spot && d < this.desktopCount; d++) {
        if (d === target) continue;
        spot = this.findFreeWith(d, w, h, 0, 0, null, entities);
        if (spot) target = d;
      }
      if (!spot && this.desktopCount < MAX_DESKTOPS) {
        target = this.desktopCount++;
        spot = this.findFreeWith(target, w, h, 0, 0, null, entities);
      }
      if (!spot) {
        spot = { x: 0, y: 0 };
        this.migration.overflow = true;
      }
      return { desktop: target, x: spot.x, y: spot.y };
    }

    _reflowDesktop(desktop) {
      var rows = this.entities.filter(function (e) { return e.desktop === desktop; });
      // Widgets keep their anchor first; apps then fill the remaining cells.
      rows.sort(function (a, b) {
        if (a.type !== b.type) return a.type === 'widget' ? -1 : 1;
        return a.y - b.y || a.x - b.x;
      });
      var placed = [];
      rows.forEach(function (e) {
        var occ = this._occupancy(placed, e.desktop, this.columns, this.rows);
        var fits = e.x >= 0 && e.y >= 0 && e.x + e.w <= this.columns && e.y + e.h <= this.rows;
        if (fits) {
          for (var yy = e.y; yy < e.y + e.h && fits; yy++) {
            for (var xx = e.x; xx < e.x + e.w; xx++) if (occ.has(xx + ',' + yy)) { fits = false; break; }
          }
        }
        if (!fits) {
          var spot = this.findFreeWith(e.desktop, e.w, e.h, e.x, e.y, null, placed);
          if (spot) { e.x = spot.x; e.y = spot.y; }
        }
        placed.push(e);
      }, this);
    }

    entity(id) { return this.entities.find(function (e) { return e.id === id || e.ref === id; }) || null; }
    apps(desktop) { return this.entities.filter(function (e) { return e.type === 'app' && e.desktop === desktop; }); }
    widgets(desktop) { return this.entities.filter(function (e) { return e.type === 'widget' && e.desktop === desktop; }); }
    entitiesOn(desktop) { return this.entities.filter(function (e) { return e.desktop === desktop; }); }

    ensureApps(appIds, pageAssignments, hiddenIds) {
      var wanted = new Set((appIds || []).filter(Boolean).map(String));
      var hidden = new Set(hiddenIds || []);
      appIds = Array.from(wanted);
      // Remove app entities for apps that are gone or deliberately hidden.
      this.entities = this.entities.filter(function (e) {
        return e.type !== 'app' || (wanted.has(String(e.ref)) && !hidden.has(String(e.ref)));
      });
      var self = this;
      appIds.forEach(function (appId, index) {
        if (hidden.has(appId)) return;
        var e = self.entity(appId);
        if (!e) {
          var desktop = clampInt(pageAssignments && pageAssignments[appId], 0, self.desktopCount - 1, Math.floor(index / (self.columns * self.rows)));
          var spot = self.findFree(desktop, 1, 1, null);
          if (!spot) {
            // Add a desktop rather than dropping the user's shortcut.
            if (self.desktopCount < MAX_DESKTOPS) desktop = self.desktopCount++;
            spot = self.findFree(desktop, 1, 1, null) || { x: 0, y: 0 };
          }
          self.entities.push({ id: appEntityId(appId), type: 'app', ref: appId, desktop: desktop, x: spot.x, y: spot.y, w: 1, h: 1 });
        } else if (pageAssignments && pageAssignments[appId] !== undefined) {
          var assigned = clampInt(pageAssignments[appId], 0, self.desktopCount - 1, e.desktop);
          if (assigned !== e.desktop) {
            var free = self.findFree(assigned, e.w, e.h, e.id);
            if (free) { e.desktop = assigned; e.x = free.x; e.y = free.y; }
          }
        }
      });
      this._normalise();
      return this;
    }

    addWidget(type, config, defaults) {
      config = clone(config || {});
      defaults = defaults || { w: 2, h: 2 };
      var desktop = clampInt(Number(config.desktop || 1) - 1, 0, this.desktopCount - 1, 0);
      var w = clampInt(config.w || defaults.w || 2, 1, this.columns, 2);
      var h = clampInt(config.h || defaults.h || 2, 1, this.rows, 2);
      var spot = this.findFree(desktop, w, h, null);
      if (!spot) {
        if (this.desktopCount < MAX_DESKTOPS) desktop = this.desktopCount++;
        spot = this.findFree(desktop, w, h, null);
      }
      if (!spot) return null;
      var id = idOf(config.id || ('widget-' + type + '-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 7)));
      var entity = {
        id: id, type: 'widget', widget_type: type, desktop: desktop,
        x: spot.x, y: spot.y, w: w, h: h, config: config
      };
      this.entities.push(entity);
      return entity;
    }

    remove(id) {
      var before = this.entities.length;
      this.entities = this.entities.filter(function (e) { return e.id !== id; });
      return this.entities.length !== before;
    }

    move(id, desktop, x, y) {
      var e = this.entity(id); if (!e) return null;
      desktop = clampInt(desktop, 0, this.desktopCount - 1, e.desktop);
      if (this.canPlace(desktop, x, y, e.w, e.h, e.id)) {
        e.desktop = desktop; e.x = x; e.y = y; return e;
      }
      var spot = this.findFree(desktop, e.w, e.h, e.id, x, y);
      if (!spot) return null;
      e.desktop = desktop; e.x = spot.x; e.y = spot.y;
      return e;
    }

    resize(id, w, h) {
      var e = this.entity(id); if (!e) return null;
      w = clampInt(w, 1, this.columns, e.w);
      h = clampInt(h, 1, this.rows, e.h);
      if (!this.canPlace(e.desktop, e.x, e.y, w, h, e.id)) {
        var spot = this.findFree(e.desktop, w, h, e.id, e.x, e.y);
        if (!spot) return null;
        e.x = spot.x; e.y = spot.y;
      }
      e.w = w; e.h = h;
      return e;
    }

    setGeometry(columns, rows, desktopCount) {
      this.columns = clampInt(columns, 3, 6, this.columns);
      this.rows = clampInt(rows, 4, 7, this.rows);
      var oldCount = this.desktopCount;
      this.desktopCount = clampInt(desktopCount, 1, MAX_DESKTOPS, this.desktopCount);
      this.entities.forEach(function (e) {
        if (e.desktop >= this.desktopCount) e.desktop = this.desktopCount - 1;
        e.w = Math.min(e.w, this.columns);
        e.h = Math.min(e.h, this.rows);
      }, this);
      this._normalise();
      return this;
    }

    snapshot() {
      return {
        schema_version: SCHEMA,
        columns: this.columns,
        rows: this.rows,
        desktop_count: this.desktopCount,
        widgets_enabled: this.widgetsEnabled !== false,
        entities: clone(this.entities),
        migration: clone(this.migration || {})
      };
    }

    save(storage) {
      try { (storage || global.localStorage).setItem(KEY, JSON.stringify(this.snapshot())); return true; }
      catch (e) { return false; }
    }

    asWidgets() {
      return this.entities.filter(function (e) { return e.type === 'widget'; }).map(function (e) {
        var cfg = Object.assign({}, e.config || {});
        cfg.id = e.id;
        cfg.type = e.widget_type;
        cfg.desktop = e.desktop + 1;
        cfg.x = e.x; cfg.y = e.y; cfg.w = e.w; cfg.h = e.h;
        return cfg;
      });
    }

    static load(options) {
      options = options || {};
      var storage = options.storage || global.localStorage;
      var saved = null;
      try { saved = JSON.parse(storage.getItem(options.key || KEY) || 'null'); } catch (e) {}
      var layout = new DesktopLayout(saved, options);
      if (!saved) layout.save(storage);
      return layout;
    }
  }

  DesktopLayout.KEY = KEY;
  DesktopLayout.SCHEMA = SCHEMA;
  DesktopLayout.appEntityId = appEntityId;
  DesktopLayout.clampInt = clampInt;
  global.NuxelDesktopLayout = DesktopLayout;
})(typeof window !== 'undefined' ? window : this);
