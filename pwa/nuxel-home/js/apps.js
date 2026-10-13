// Nuxel Home - App Registry
// Defines the default app list with metadata

const NUXEL_APPS = {
    // Native shell apps
    'nuxel-dialer': {
        id: 'nuxel-dialer',
        name: 'Phone',
        icon: '📞',
        color: '#4CAF50',
        category: 'communication',
        type: 'native',
        url: 'nuxel-dialer://',
        description: 'Make phone calls',
        capabilities: ['call:initiate', 'call:end', 'call:status', 'contacts:read'],
        docked: true,
    },
    'nuxel-messages': {
        id: 'nuxel-messages',
        name: 'Messages',
        icon: '💬',
        color: '#2196F3',
        category: 'communication',
        type: 'native',
        url: 'nuxel-messages://',
        description: 'Send and receive SMS',
        capabilities: ['sms:send', 'sms:receive', 'contacts:read'],
        docked: true,
    },
    'nuxel-contacts': {
        id: 'nuxel-contacts',
        name: 'Contacts',
        icon: '👤',
        color: '#9C27B0',
        category: 'communication',
        type: 'native',
        url: 'nuxel-contacts://',
        description: 'Manage your contacts',
        capabilities: ['contacts:read', 'contacts:write'],
        docked: false,
    },

    // PWA apps
    'org.nuxel.Mail': {
        id: 'org.nuxel.Mail',
        name: 'Mail',
        icon: '✉️',
        color: '#FF9800',
        category: 'productivity',
        type: 'pwa',
        url: '/pwa/nuxel-apps/mail/index.html',
        description: 'Email client',
        capabilities: ['notifications:send', 'notifications:receive'],
        docked: false,
    },
    'org.nuxel.Calendar': {
        id: 'org.nuxel.Calendar',
        name: 'Calendar',
        icon: '📅',
        color: '#E91E63',
        category: 'productivity',
        type: 'pwa',
        url: '/pwa/nuxel-apps/calendar/index.html',
        description: 'Calendar and events',
        capabilities: ['notifications:send'],
        docked: false,
    },
    'org.nuxel.Notes': {
        id: 'org.nuxel.Notes',
        name: 'Notes',
        icon: '📝',
        color: '#607D8B',
        category: 'productivity',
        type: 'pwa',
        url: '/pwa/nuxel-apps/notes/index.html',
        description: 'Take notes',
        capabilities: [],
        docked: false,
    },
    'org.nuxel.Files': {
        id: 'org.nuxel.Files',
        name: 'Files',
        icon: '📁',
        color: '#3F51B5',
        category: 'tools',
        type: 'pwa',
        url: '/pwa/nuxel-apps/files/index.html',
        description: 'File browser',
        capabilities: [],
        docked: false,
    },
    'nuxel-camera': {
        id: 'nuxel-camera',
        name: 'Camera',
        icon: '📷',
        color: '#795548',
        category: 'media',
        type: 'native',
        url: 'nuxel-camera://',
        description: 'Take photos and videos',
        capabilities: ['camera:capture', 'camera:preview'],
        docked: false,
    },

    // System apps
    'nuxel-settings': {
        id: 'nuxel-settings',
        name: 'Settings',
        icon: '⚙️',
        color: '#78909C',
        category: 'system',
        type: 'native',
        url: 'nuxel-settings://',
        description: 'System settings',
        capabilities: [],
        docked: true,
    },
};

// App state management
class AppRegistry {
    constructor() {
        this.apps = new Map(Object.entries(NUXEL_APPS));
        this.userApps = new Map();
        this.recentApps = [];
        this.maxRecentApps = 10;
        this._loadState();
    }

    getAllApps() {
        const apps = [...this.apps.values()];
        // Merge user-installed apps
        for (const app of this.userApps.values()) {
            apps.push(app);
        }
        return apps.sort((a, b) => a.name.localeCompare(b.name));
    }

    getDockedApps() {
        return this.getAllApps().filter(app => app.docked);
    }

    getAppsByCategory(category) {
        return this.getAllApps().filter(app => app.category === category);
    }

    getApp(id) {
        return this.apps.get(id) || this.userApps.get(id);
    }

    addRecentApp(appId) {
        // Remove if already present
        this.recentApps = this.recentApps.filter(id => id !== appId);
        // Add to front
        this.recentApps.unshift(appId);
        // Limit size
        if (this.recentApps.length > this.maxRecentApps) {
            this.recentApps = this.recentApps.slice(0, this.maxRecentApps);
        }
        this._saveState();
    }

    getRecentApps() {
        return this.recentApps
            .map(id => this.getApp(id))
            .filter(app => app !== undefined);
    }

    searchApps(query) {
        const q = query.toLowerCase().trim();
        if (!q) return [];

        const results = [];
        for (const app of this.getAllApps()) {
            if (app.name.toLowerCase().includes(q) ||
                app.description.toLowerCase().includes(q) ||
                app.category.toLowerCase().includes(q)) {
                results.push({
                    ...app,
                    matchType: app.name.toLowerCase().includes(q) ? 'name' : 'description',
                });
            }
        }

        // Sort by relevance
        results.sort((a, b) => {
            const aScore = a.matchType === 'name' ? 0 : 1;
            const bScore = b.matchType === 'name' ? 0 : 1;
            if (aScore !== bScore) return aScore - bScore;
            return a.name.localeCompare(b.name);
        });

        return results;
    }

    launchApp(appId) {
        const app = this.getApp(appId);
        if (!app) {
            console.error(`App not found: ${appId}`);
            return;
        }

        this.addRecentApp(appId);

        // Dispatch launch event
        const event = new CustomEvent('app:launch', {
            detail: { app },
            bubbles: true,
        });
        document.dispatchEvent(event);

        // Handle based on type
        if (app.type === 'pwa') {
            // Open PWA via iframe or navigation
            this._launchPwa(app);
        } else if (app.type === 'native') {
            // Launch native app via custom protocol or xdg-open
            this._launchNative(app);
        }
    }

    _launchPwa(app) {
        console.log(`Launching PWA: ${app.name} (${app.url})`);
        // In a real implementation, this would:
        // 1. Check if PWA is already open (via service worker)
        // 2. Focus existing window or open new one
        // 3. Request capabilities from nuxel-bridge
        
        // Open in fullscreen iframe or new window
        const event = new CustomEvent('pwa:open', {
            detail: {
                app: app,
                url: app.url,
            },
            bubbles: true,
        });
        document.dispatchEvent(event);
    }

    _launchNative(app) {
        console.log(`Launching native app: ${app.name} (${app.url})`);
        
        // Try xdg-open for custom protocol URLs
        try {
            // Use nuxel-bridge to request launch
            const event = new CustomEvent('native:launch', {
                detail: {
                    app: app,
                    url: app.url,
                },
                bubbles: true,
            });
            document.dispatchEvent(event);
        } catch (e) {
            console.error(`Failed to launch native app: ${e}`);
        }
    }

    installApp(manifest) {
        const app = {
            id: manifest.id || `user-${Date.now()}`,
            name: manifest.name || 'Unknown App',
            icon: manifest.icon || '📱',
            color: manifest.color || '#555',
            category: manifest.category || 'tools',
            type: 'pwa',
            url: manifest.start_url || '/',
            description: manifest.description || '',
            capabilities: manifest.capabilities || [],
            docked: false,
            userInstalled: true,
        };

        this.userApps.set(app.id, app);
        this._saveState();

        const event = new CustomEvent('app:installed', {
            detail: { app },
            bubbles: true,
        });
        document.dispatchEvent(event);

        return app;
    }

    uninstallApp(appId) {
        if (this.userApps.has(appId)) {
            this.userApps.delete(appId);
            this._saveState();

            const event = new CustomEvent('app:uninstalled', {
                detail: { appId },
                bubbles: true,
            });
            document.dispatchEvent(event);
            return true;
        }
        return false;
    }

    _saveState() {
        try {
            const state = {
                recentApps: this.recentApps,
                userApps: [...this.userApps.entries()],
            };
            localStorage.setItem('nuxel-app-registry', JSON.stringify(state));
        } catch (e) {
            console.warn('Failed to save app state:', e);
        }
    }

    _loadState() {
        try {
            const raw = localStorage.getItem('nuxel-app-registry');
            if (raw) {
                const state = JSON.parse(raw);
                this.recentApps = state.recentApps || [];
                if (state.userApps) {
                    this.userApps = new Map(state.userApps);
                }
            }
        } catch (e) {
            console.warn('Failed to load app state:', e);
        }
    }
}

// Create global instance
const appRegistry = new AppRegistry();
