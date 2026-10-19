/* Durable, deterministic home-screen layout model.  Kept DOM-free so the
 * insertion and folder invariants are testable on the host. */
(function (global) {
  'use strict';
  const isApp = value => typeof value === 'string' && value.length > 0;
  const copy = value => JSON.parse(JSON.stringify(value));
  class HomeLayout {
    constructor(appIds, saved) {
      this.appIds = Array.from(new Set((appIds || []).filter(isApp)));
      this.entries = this._migrate(saved);
      this._normalise();
    }
    _migrate(saved) {
      if (saved && Array.isArray(saved.entries)) return copy(saved.entries);
      // A37 persisted only a flat order.  It is a lossless migration.
      if (saved && Array.isArray(saved.order)) return saved.order.slice();
      return this.appIds.slice();
    }
    _normalise() {
      const seen = new Set();
      const valid = entry => {
        if (isApp(entry)) { if (seen.has(entry) || !this.appIds.includes(entry)) return null; seen.add(entry); return entry; }
        if (!entry || entry.type !== 'folder' || !Array.isArray(entry.items)) return null;
        const items = entry.items.filter(id => isApp(id) && this.appIds.includes(id) && !seen.has(id) && (seen.add(id), true));
        if (!items.length) return null;
        return { type: 'folder', id: entry.id || 'folder-' + Date.now().toString(36), name: String(entry.name || 'Folder').slice(0, 40), items };
      };
      this.entries = this.entries.map(valid).filter(Boolean);
      this.appIds.forEach(id => { if (!seen.has(id)) this.entries.push(id); });
    }
    snapshot() { return { version: 2, entries: copy(this.entries) }; }
    _location(id) {
      for (let i = 0; i < this.entries.length; i++) {
        const e = this.entries[i];
        if (e === id) return { top: i, item: -1, entry: e };
        if (e && e.type === 'folder') { const item = e.items.indexOf(id); if (item >= 0) return { top: i, item, entry: e }; }
      }
      return null;
    }
    remove(id) {
      const at = this._location(id); if (!at) return null;
      if (at.item < 0) this.entries.splice(at.top, 1);
      else { at.entry.items.splice(at.item, 1); if (!at.entry.items.length) this.entries.splice(at.top, 1); }
      return at;
    }
    insertApp(id, index) {
      if (!this.appIds.includes(id)) return false;
      this.remove(id);
      const slot = Math.max(0, Math.min(Number(index) || 0, this.entries.length));
      this.entries.splice(slot, 0, id); this._normalise(); return true;
    }
    createFolder(dragId, targetId) {
      if (dragId === targetId || !this.appIds.includes(dragId) || !this.appIds.includes(targetId)) return false;
      const target = this._location(targetId); if (!target || target.item >= 0) return false;
      this.remove(dragId);
      const targetAfter = this._location(targetId); if (!targetAfter) return false;
      this.entries.splice(targetAfter.top, 1, { type: 'folder', id: 'folder-' + Date.now().toString(36), name: 'Folder', items: [targetId, dragId] });
      this._normalise(); return true;
    }
    addToFolder(appId, folderId, index) {
      const folder = this.entries.find(e => e && e.type === 'folder' && e.id === folderId);
      if (!folder || !this.appIds.includes(appId)) return false;
      this.remove(appId);
      const pos = Math.max(0, Math.min(Number.isInteger(index) ? index : folder.items.length, folder.items.length));
      folder.items.splice(pos, 0, appId); this._normalise(); return true;
    }
    removeFromFolder(appId, folderId, topIndex) {
      const folder = this.entries.find(e => e && e.type === 'folder' && e.id === folderId);
      if (!folder || !folder.items.includes(appId)) return false;
      this.remove(appId); this.insertApp(appId, topIndex); return true;
    }
    renameFolder(folderId, name) {
      const folder = this.entries.find(e => e && e.type === 'folder' && e.id === folderId);
      if (!folder) return false; folder.name = String(name || 'Folder').trim().slice(0, 40) || 'Folder'; return true;
    }
  }
  global.NuxelHomeLayout = HomeLayout;
})(window);
