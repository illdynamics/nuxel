// Nuxel shared-bridge helper with graceful offline fallback.
async function nuxelBridgeCall(namespace, verb, params, fallback) {
    try {
        const b = window.NuxelBridge;
        if (!b) { window.__nuxelBridgeOffline = true; return fallback; }
        const res = await b.call(namespace, verb, params);
        if (!res || res.success === false) {
            window.__nuxelBridgeOffline = true;
            return fallback;
        }
        window.__nuxelBridgeOffline = false;
        return res;
    } catch (e) {
        window.__nuxelBridgeOffline = true;
        return fallback;
    }
}

function nuxelBridgeOfflineBanner() {
    if (!window.__nuxelBridgeOffline) return;
    if (document.getElementById('bridge-offline-banner')) return;
    const el = document.createElement('div');
    el.id = 'bridge-offline-banner';
    el.textContent = '🔌 Bridge offline — showing local data';
    el.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:#ef6c00;color:#fff;font-size:13px;padding:6px 12px;z-index:9999;text-align:center;';
    document.body.appendChild(el);
}

// Nuxel Notes - Markdown Notes PWA

class NotesApp {
    constructor() {
        this.notes = [];
        this.currentNote = null;
        this._init();
    }

    async _init() {
        await this._loadNotes();
        this._renderList();
        this._bindEvents();
    }

    _renderList() {
        const list = document.getElementById('notes-list');
        
        if (this.notes.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📝</div>
                    <h3>No notes yet</h3>
                    <p>Tap + to create your first note</p>
                </div>`;
            return;
        }

        this.notes.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));

        list.innerHTML = this.notes.map(note => `
            <div class="note-card" data-id="${note.id}">
                <div class="note-card-title">${this._escapeHtml(note.title || 'Untitled')}</div>
                <div class="note-card-preview">${this._escapeHtml((note.body || '').substring(0, 100))}</div>
                <div class="note-card-date">${this._formatDate(note.updatedAt)}</div>
            </div>
        `).join('');

        list.querySelectorAll('.note-card').forEach(card => {
            card.addEventListener('click', () => {
                const id = card.dataset.id;
                const note = this.notes.find(n => n.id === id);
                if (note) this._openEditor(note);
            });
        });
    }

    _openEditor(note = null) {
        const editor = document.getElementById('note-editor');
        editor.classList.remove('hidden');
        
        if (note) {
            this.currentNote = note;
            document.getElementById('note-title').value = note.title || '';
            document.getElementById('note-body').value = note.body || '';
            document.getElementById('note-meta').textContent = 
                `Last edited: ${new Date(note.updatedAt).toLocaleString()}`;
        } else {
            this.currentNote = {
                id: `note-${Date.now()}`,
                title: '',
                body: '',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
            };
            document.getElementById('note-title').value = '';
            document.getElementById('note-body').value = '';
            document.getElementById('note-meta').textContent = 'New note';
        }

        document.getElementById('note-title').focus();
    }

    _saveCurrentNote() {
        if (!this.currentNote) return;

        this.currentNote.title = document.getElementById('note-title').value.trim() || 'Untitled';
        this.currentNote.body = document.getElementById('note-body').value;
        this.currentNote.updatedAt = new Date().toISOString();

        const existingIdx = this.notes.findIndex(n => n.id === this.currentNote.id);
        if (existingIdx >= 0) {
            this.notes[existingIdx] = this.currentNote;
        } else {
            this.notes.push(this.currentNote);
        }

        this._saveNotes();
        this._renderList();
    }

    _deleteNote(id) {
        this.notes = this.notes.filter(n => n.id !== id);
        this._saveNotes();
        this._renderList();
    }

    _bindEvents() {
        // New note
        document.getElementById('new-note-btn').addEventListener('click', () => this._openEditor(null));

        // Editor back
        document.getElementById('editor-back').addEventListener('click', () => {
            this._saveCurrentNote();
            document.getElementById('note-editor').classList.add('hidden');
        });

        // Editor save/done
        document.getElementById('editor-save').addEventListener('click', () => {
            this._saveCurrentNote();
            document.getElementById('note-editor').classList.add('hidden');
        });

        // Auto-save on typing (with debounce)
        let saveTimer;
        document.getElementById('note-body').addEventListener('input', () => {
            clearTimeout(saveTimer);
            saveTimer = setTimeout(() => this._saveCurrentNote(), 1000);
        });
        document.getElementById('note-title').addEventListener('input', () => {
            clearTimeout(saveTimer);
            saveTimer = setTimeout(() => this._saveCurrentNote(), 1000);
        });

        // Menu button for future use
        document.getElementById('menu-btn').addEventListener('click', () => {
            if (this.currentNote) {
                if (confirm('Delete this note?')) {
                    this._deleteNote(this.currentNote.id);
                    document.getElementById('note-editor').classList.add('hidden');
                    this.currentNote = null;
                }
            }
        });

        // Keyboard shortcut for new note
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                this._openEditor(null);
            }
        });

        // Toolbar buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                const body = document.getElementById('note-body');
                const start = body.selectionStart;
                const end = body.selectionEnd;
                const text = body.value;
                const selected = text.substring(start, end);

                let replacement = '';
                switch (cmd) {
                    case 'bold': replacement = `**${selected || 'bold'}**`; break;
                    case 'italic': replacement = `*${selected || 'italic'}*`; break;
                    case 'heading': replacement = `## ${selected || 'Heading'}\n`; break;
                    case 'list': replacement = `- ${selected || 'item'}\n`; break;
                    case 'code': replacement = '```\n' + (selected || 'code') + '\n```'; break;
                }

                body.setRangeText(replacement, start, end, 'end');
                body.focus();
            });
        });
    }

    async _loadNotes() {
        const fallback = () => {
            try {
                const raw = localStorage.getItem('nuxel-notes');
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                return [];
            }
        };
        try {
            const res = await nuxelBridgeCall('storage', 'read', { key: 'nuxel-notes' }, null);
            if (res && Array.isArray(res.data)) {
                this.notes = res.data;
            } else if (res && Array.isArray(res.notes)) {
                this.notes = res.notes;
            } else {
                this.notes = fallback();
            }
            nuxelBridgeOfflineBanner();
        } catch (e) {
            this.notes = fallback();
        }
    }

    _saveNotes() {
        // Always keep the local copy as an offline fallback.
        try {
            localStorage.setItem('nuxel-notes', JSON.stringify(this.notes));
        } catch (e) {
            console.warn('Failed to save notes locally:', e);
        }
        // Persist via the shared bridge (best effort).
        nuxelBridgeCall('storage', 'write', { key: 'nuxel-notes', data: this.notes }, null);
    }

    _formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now - d;
        if (diff < 3600000) return 'Just now';
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.notesApp = new NotesApp();
});
