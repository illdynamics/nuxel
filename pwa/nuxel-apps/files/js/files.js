// Helper: wrap the shared bridge call with a graceful offline fallback.
async function nuxelBridgeCall(namespace, verb, params, fallback) {
    try {
        const b = window.NuxelBridge;
        if (!b) { window.__nuxelBridgeOffline = true; return fallback; }
        const res = await b.call(namespace, verb, params);
        if (!res || res.success === false) { window.__nuxelBridgeOffline = true; return fallback; }
        window.__nuxelBridgeOffline = false;
        return res;
    } catch (e) { window.__nuxelBridgeOffline = true; return fallback; }
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

// Nuxel Files - File Browser PWA

class FilesApp {
    constructor() {
        this.currentPath = '/';
        this.files = [];
        this._init();
    }

    async _init() {
        await this._loadFiles();
        this._render();
        this._bindEvents();
    }

    async _loadFiles() {
        const fallback = () => {
            try {
                const raw = localStorage.getItem('nuxel-files-index');
                return raw ? JSON.parse(raw) : this._getDefaultFiles();
            } catch (e) {
                return this._getDefaultFiles();
            }
        };

        try {
            const res = await nuxelBridgeCall('storage', 'list-dir', { app_id: 'org.nuxel.Files', path: '/' }, null);
            if (res && Array.isArray(res.entries) && res.entries.length) {
                this.files = res.entries;
            } else {
                this.files = fallback();
            }
            nuxelBridgeOfflineBanner();
        } catch (e) {
            this.files = fallback();
        }

        // If no files exist, populate with demo structure
        if (this.files.length === 0) {
            this.files = this._getDefaultFiles();
            this._saveFiles();
        }
    }

    _getDefaultFiles() {
        const now = new Date().toISOString();
        return [
            { name: 'Documents', path: '/Documents', type: 'folder', size: 0, modified: now },
            { name: 'Downloads', path: '/Downloads', type: 'folder', size: 0, modified: now },
            { name: 'Pictures', path: '/Pictures', type: 'folder', size: 0, modified: now },
            { name: 'Music', path: '/Music', type: 'folder', size: 0, modified: now },
            { name: 'Videos', path: '/Videos', type: 'folder', size: 0, modified: now },
            { path: '/Documents/readme.txt', name: 'readme.txt', type: 'document', size: 2048, modified: now },
            { path: '/Documents/notes.md', name: 'notes.md', type: 'code', size: 1024, modified: now },
        ];
    }

    _render() {
        this._renderBreadcrumb();
        this._renderFiles();
    }

    _renderBreadcrumb() {
        const bread = document.getElementById('breadcrumb');
        const parts = this.currentPath.split('/').filter(Boolean);
        
        let html = '<span data-path="/">Files</span>';
        let cumPath = '';
        for (const part of parts) {
            cumPath += '/' + part;
            html += `<span class="sep">/</span><span data-path="${cumPath}">${part}</span>`;
        }
        bread.innerHTML = html;

        bread.querySelectorAll('span[data-path]').forEach(el => {
            el.style.cursor = 'pointer';
            el.addEventListener('click', () => {
                this._navigateTo(el.dataset.path);
            });
        });
    }

    _renderFiles() {
        const grid = document.getElementById('file-grid');
        
        // Get files in current directory
        const currentDir = this.currentPath === '/' ? '' : this.currentPath;
        const dirFiles = this.files.filter(f => {
            const parentPath = f.path.substring(0, f.path.lastIndexOf('/'));
            return parentPath === currentDir || (currentDir === '' && !f.path.includes('/'));
        });

        // Also match subdirectories
        const subdirs = this.files.filter(f => {
            if (f.type !== 'folder') return false;
            const parentDir = f.path.substring(0, f.path.lastIndexOf('/'));
            return parentDir === currentDir || (currentDir === '' && !f.path.includes('/'));
        });

        // Merge and deduplicate
        const seen = new Set();
        const allItems = [];
        
        for (const f of [...subdirs, ...dirFiles]) {
            if (!seen.has(f.path)) {
                seen.add(f.path);
                allItems.push(f);
            }
        }

        // Sort: folders first, then alphabetical
        allItems.sort((a, b) => {
            if (a.type === 'folder' && b.type !== 'folder') return -1;
            if (a.type !== 'folder' && b.type === 'folder') return 1;
            return a.name.localeCompare(b.name);
        });

        if (allItems.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📁</div>
                    <p>This folder is empty</p>
                </div>`;
            return;
        }

        grid.innerHTML = allItems.map(file => `
            <div class="file-item" data-path="${file.path}" data-type="${file.type}">
                <div class="file-icon ${file.type === 'folder' ? 'folder' : this._getFileTypeClass(file.name)}">
                    ${this._getFileIcon(file)}
                </div>
                <div class="file-name">${file.name}</div>
                ${file.type !== 'folder' ? `<div class="file-size">${this._formatSize(file.size)}</div>` : ''}
            </div>
        `).join('');

        // Bind events
        grid.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                const type = item.dataset.type;
                const file = this.files.find(f => f.path === path);
                
                if (type === 'folder') {
                    this._navigateTo(path);
                } else {
                    this._openFile(file);
                }
            });

            // Long press for context menu
            let longTimer;
            item.addEventListener('touchstart', () => {
                longTimer = setTimeout(() => this._showContextMenu(item.dataset.path), 500);
            }, { passive: true });
            item.addEventListener('touchend', () => clearTimeout(longTimer), { passive: true });
        });
    }

    _navigateTo(path) {
        this.currentPath = path;
        this._render();
    }

    _openFile(file) {
        if (!file) return;
        
        // Try to open in appropriate viewer
        const ext = file.name.split('.').pop()?.toLowerCase();
        
        if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(ext)) {
            // Show image viewer
            this._showImageViewer(file);
        } else if (['txt', 'md', 'json', 'xml', 'html', 'css', 'js'].includes(ext)) {
            // Show text viewer
            this._showTextViewer(file);
        } else {
            // Download
            this._downloadFile(file);
        }
    }

    _showImageViewer(file) {
        alert(`[Preview] ${file.name} (${this._formatSize(file.size)})\n\nImage viewer would display this file.`);
    }

    _showTextViewer(file) {
        alert(`[Text] ${file.name}\n\nText viewer would display this file's contents.`);
    }

    _downloadFile(file) {
        // Create a download from stored data
        const data = localStorage.getItem(`nuxel-file-data:${file.path}`);
        if (data) {
            const a = document.createElement('a');
            a.href = data;
            a.download = file.name;
            a.click();
        } else {
            this._showToast('File not available offline');
        }
    }

    _createFolder(name) {
        const folderPath = this.currentPath === '/' ? `/${name}` : `${this.currentPath}/${name}`;
        
        if (this.files.some(f => f.path === folderPath)) {
            this._showToast('Folder already exists');
            return;
        }

        this.files.push({
            path: folderPath,
            name: name,
            type: 'folder',
            size: 0,
            modified: new Date().toISOString(),
        });

        this._saveFiles();
        this._render();
        this._showToast(`Folder "${name}" created`);
    }

    _deleteItem(path) {
        const file = this.files.find(f => f.path === path);
        if (!file) return;
        
        // Remove file and any children (for folders)
        this.files = this.files.filter(f => {
            if (f.path === path) return false;
            if (file.type === 'folder' && f.path.startsWith(path + '/')) return false;
            return true;
        });

        // Remove stored data
        localStorage.removeItem(`nuxel-file-data:${path}`);

        this._saveFiles();
        this._render();
    }

    _showContextMenu(path) {
        const file = this.files.find(f => f.path === path);
        if (!file) return;

        const action = confirm(`Actions for "${file.name}"\n\nOK = Delete, Cancel = Cancel`);
        if (action) {
            if (confirm(`Delete "${file.name}"?`)) {
                this._deleteItem(path);
            }
        }
    }

    _bindEvents() {
        document.getElementById('back-btn').addEventListener('click', () => {
            if (this.currentPath !== '/') {
                const parent = this.currentPath.substring(0, this.currentPath.lastIndexOf('/')) || '/';
                this._navigateTo(parent);
            }
        });

        document.getElementById('new-folder-btn').addEventListener('click', () => {
            document.getElementById('folder-dialog').classList.remove('hidden');
            document.getElementById('folder-name').value = '';
            setTimeout(() => document.getElementById('folder-name').focus(), 100);
        });

        document.getElementById('dialog-cancel').addEventListener('click', () => {
            document.getElementById('folder-dialog').classList.add('hidden');
        });

        document.getElementById('dialog-create').addEventListener('click', () => {
            const name = document.getElementById('folder-name').value.trim();
            if (name) {
                this._createFolder(name);
                document.getElementById('folder-dialog').classList.add('hidden');
            }
        });

        // Handle file uploads via drag-and-drop
        document.addEventListener('dragover', (e) => {
            e.preventDefault();
            document.getElementById('upload-area').classList.remove('hidden');
        });

        document.addEventListener('dragleave', (e) => {
            e.preventDefault();
            document.getElementById('upload-area').classList.add('hidden');
        });

        document.addEventListener('drop', (e) => {
            e.preventDefault();
            document.getElementById('upload-area').classList.add('hidden');
            this._handleFileUpload(e.dataTransfer.files);
        });

        // Handle file input via input element
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.multiple = true;
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);

        // Long press on empty area to upload
        document.getElementById('file-grid').addEventListener('touchstart', (e) => {
            if (e.target === document.getElementById('file-grid') || 
                e.target.classList.contains('empty-state')) {
                fileInput.click();
            }
        }, { passive: true });
    }

    async _handleFileUpload(files) {
        for (const file of files) {
            const path = this.currentPath === '/' ? `/${file.name}` : `${this.currentPath}/${file.name}`;
            
            // Read as data URL
            const reader = new FileReader();
            const dataUrl = await new Promise((resolve) => {
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(file);
            });

            // Store file metadata
            this.files.push({
                path: path,
                name: file.name,
                type: file.type.split('/')[0] || 'document',
                size: file.size,
                modified: new Date().toISOString(),
            });

            // Store file data
            try {
                localStorage.setItem(`nuxel-file-data:${path}`, dataUrl);
            } catch (e) {
                this._showToast('File too large for offline storage');
            }
        }

        this._saveFiles();
        this._render();
        this._showToast(`${files.length} file(s) uploaded`);
    }

    _saveFiles() {
        try {
            localStorage.setItem('nuxel-files-index', JSON.stringify(this.files));
        } catch (e) {
            console.warn('Failed to save file index locally:', e);
        }
        nuxelBridgeCall('storage', 'write', { app_id: 'org.nuxel.Files', key: 'nuxel-files-index', data: this.files }, null);
    }

    _getFileIcon(file) {
        if (file.type === 'folder') return '📁';
        const ext = file.name.split('.').pop()?.toLowerCase();
        const iconMap = {
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'svg': '🖼️',
            'pdf': '📄', 'doc': '📝', 'docx': '📝',
            'mp3': '🎵', 'wav': '🎵', 'flac': '🎵',
            'mp4': '🎬', 'mov': '🎬', 'avi': '🎬',
            'zip': '📦', 'tar': '📦', 'gz': '📦',
            'txt': '📃', 'md': '📃',
            'html': '🌐', 'css': '🎨', 'js': '⚡',
            'json': '📋', 'xml': '📋',
        };
        return iconMap[ext] || '📄';
    }

    _getFileTypeClass(name) {
        const ext = name.split('.').pop()?.toLowerCase();
        if (['jpg','jpeg','png','gif','svg','webp'].includes(ext)) return 'image';
        if (['mp3','wav','flac','aac','ogg'].includes(ext)) return 'audio';
        if (['mp4','mov','avi','mkv','webm'].includes(ext)) return 'video';
        if (['zip','tar','gz','bz2','rar','7z'].includes(ext)) return 'archive';
        if (['js','ts','py','rb','go','rs','c','cpp','h','html','css','json','xml','yaml','yml','md','sh'].includes(ext)) return 'code';
        if (['pdf','doc','docx','xls','xlsx','ppt','pptx'].includes(ext)) return 'document';
        return 'other';
    }

    _formatSize(bytes) {
        if (!bytes) return '';
        const units = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        let size = bytes;
        while (size >= 1024 && i < units.length - 1) {
            size /= 1024;
            i++;
        }
        return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
    }

    _showToast(msg) {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = msg;
        toast.style.cssText = 'position:fixed;bottom:40px;left:50%;transform:translateX(-50%);background:#0f3460;padding:12px 24px;border-radius:12px;font-size:14px;z-index:100;box-shadow:0 4px 20px rgba(0,0,0,0.4);';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.filesApp = new FilesApp();
});
