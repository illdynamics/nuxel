// Nuxel Mail - Local Storage & Account Management

class MailStorage {
    constructor() {
        this.dbName = 'nuxel-mail';
        this.dbVersion = 1;
        this.db = null;
        this._init();
    }

    async _init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Accounts store
                if (!db.objectStoreNames.contains('accounts')) {
                    const accounts = db.createObjectStore('accounts', { keyPath: 'id' });
                    accounts.createIndex('email', 'email', { unique: true });
                }
                
                // Messages store
                if (!db.objectStoreNames.contains('messages')) {
                    const msgs = db.createObjectStore('messages', { keyPath: 'id' });
                    msgs.createIndex('accountId', 'accountId', { unique: false });
                    msgs.createIndex('folder', 'folder', { unique: false });
                    msgs.createIndex('threadId', 'threadId', { unique: false });
                    msgs.createIndex('timestamp', 'timestamp', { unique: false });
                }
                
                // Folders store
                if (!db.objectStoreNames.contains('folders')) {
                    const folders = db.createObjectStore('folders', { keyPath: 'id' });
                    folders.createIndex('accountId', 'accountId', { unique: false });
                }
            };
            
            request.onsuccess = (event) => {
                this.db = event.target.result;
                console.log('[MailDB] Database initialized');
                resolve();
            };
            
            request.onerror = (event) => {
                console.error('[MailDB] Error:', event.target.error);
                reject(event.target.error);
            };
        });
    }

    async addAccount(account) {
        const tx = this.db.transaction('accounts', 'readwrite');
        const store = tx.objectStore('accounts');
        account.id = account.id || `acct-${Date.now()}`;
        account.createdAt = new Date().toISOString();
        await store.put(account);
        return account;
    }

    async getAccounts() {
        const tx = this.db.transaction('accounts', 'readonly');
        const store = tx.objectStore('accounts');
        return new Promise((resolve) => {
            const result = [];
            const cursor = store.openCursor();
            cursor.onsuccess = (event) => {
                const c = event.target.result;
                if (c) { result.push(c.value); c.continue(); }
                else resolve(result);
            };
        });
    }

    async deleteAccount(id) {
        const tx = this.db.transaction('accounts', 'readwrite');
        await tx.objectStore('accounts').delete(id);
    }

    async saveMessages(messages) {
        const tx = this.db.transaction('messages', 'readwrite');
        const store = tx.objectStore('messages');
        for (const msg of messages) {
            await store.put(msg);
        }
    }

    async getMessages(accountId, folder = 'INBOX', limit = 50) {
        const tx = this.db.transaction('messages', 'readonly');
        const store = tx.objectStore('messages');
        const index = store.index('accountId');
        
        return new Promise((resolve) => {
            const result = [];
            const cursor = index.openCursor(accountId);
            cursor.onsuccess = (event) => {
                const c = event.target.result;
                if (c) {
                    if (c.value.folder === folder) {
                        result.push(c.value);
                    }
                    c.continue();
                } else {
                    result.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                    resolve(result.slice(0, limit));
                }
            };
        });
    }

    async getMessage(id) {
        const tx = this.db.transaction('messages', 'readonly');
        const store = tx.objectStore('messages');
        return store.get(id);
    }

    async markAsRead(id) {
        const tx = this.db.transaction('messages', 'readwrite');
        const msg = await tx.objectStore('messages').get(id);
        if (msg) {
            msg.flags = msg.flags || [];
            if (!msg.flags.includes('\\Seen')) {
                msg.flags.push('\\Seen');
            }
            msg.read = true;
            await tx.objectStore('messages').put(msg);
        }
    }

    async deleteMessage(id) {
        const tx = this.db.transaction('messages', 'readwrite');
        await tx.objectStore('messages').delete(id);
    }
}

// Global instance
const mailStorage = new MailStorage();
