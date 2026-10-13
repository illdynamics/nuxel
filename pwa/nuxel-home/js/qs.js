// Nuxel Home - Quick Settings Panel
// Manages the quick settings toggles

class QuickSettings {
    constructor() {
        this.panel = document.getElementById('quick-settings');
        this.isOpen = false;
        this.state = {
            wifi: false,
            bluetooth: false,
            mobile: false,
            location: false,
            dnd: false,
            flashlight: false,
            rotate: false,
        };
        this._init();
    }

    _init() {
        this._bindEvents();
    }

    _bindEvents() {
        // Toggle on status bar swipe down
        document.addEventListener('gesture:qs', () => this.toggle());

        // Individual toggle clicks
        const toggles = ['wifi', 'bluetooth', 'mobile', 'location', 'dnd', 'flashlight', 'rotate'];
        toggles.forEach(id => {
            const el = document.getElementById(`qs-${id}`);
            if (el) {
                el.addEventListener('click', () => {
                    this._toggle(id);
                });
            }
        });

        // Settings button
        const settingsBtn = document.getElementById('qs-settings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.close();
                appRegistry.launchApp('nuxel-settings');
            });
        }
    }

    open() {
        if (this.isOpen) return;
        this.isOpen = true;
        this._render();
        this.panel.classList.remove('hidden');
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;
        this.panel.classList.add('hidden');
    }

    toggle() {
        if (this.isOpen) this.close();
        else this.open();
    }

    _toggle(id) {
        this.state[id] = !this.state[id];
        const el = document.getElementById(`qs-${id}`);
        if (el) {
            el.dataset.enabled = this.state[id] ? 'true' : 'false';
        }
        
        // Dispatch event
        const event = new CustomEvent('qs:toggle', {
            detail: { id, enabled: this.state[id] },
            bubbles: true,
        });
        document.dispatchEvent(event);
        
        // Provide haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(10);
        }
    }

    _render() {
        // Update all toggle states from bridge
        this._syncState();
    }

    async _syncState() {
        try {
            const status = await bridge.getPhoneStatus();
            if (status.network) {
                this.state.wifi = status.network.wifi_enabled || false;
            }
            if (status.modem) {
                this.state.mobile = status.modem.connected || false;
            }
            this._updateUI();
        } catch (e) {
            // Use defaults
        }
    }

    _updateUI() {
        for (const [id, enabled] of Object.entries(this.state)) {
            const el = document.getElementById(`qs-${id}`);
            if (el) {
                el.dataset.enabled = enabled ? 'true' : 'false';
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.qs = new QuickSettings();
});
