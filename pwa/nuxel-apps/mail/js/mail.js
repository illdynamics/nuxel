// Nuxel Mail - Main Application

class MailApp {
    constructor() {
        this.currentAccount = null;
        this.currentFolder = 'INBOX';
        this.currentMessages = [];
        this.accounts = [];
        
        this._init();
    }

    async _init() {
        await mailStorage._init();
        await this._loadAccounts();
        this._bindEvents();
        
        if (this.accounts.length > 0) {
            this.currentAccount = this.accounts[0];
            await this._loadMessages();
        } else {
            this._showSetup();
        }
    }

    async _loadAccounts() {
        this.accounts = await mailStorage.getAccounts();
    }

    async _loadMessages() {
        if (!this.currentAccount) return;
        
        const list = document.getElementById('message-list');
        list.innerHTML = '<div class="loading">Loading messages...</div>';
        
        try {
            const messages = await imapClient.fetchMessages(
                this.currentAccount.id, 
                this.currentFolder
            );
            this.currentMessages = messages;
            this._renderMessageList(messages);
        } catch (e) {
            console.error('Failed to load messages:', e);
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📧</div>
                    <h3>Could not load messages</h3>
                    <p>${e.message}</p>
                    <button id="retry-load" class="btn-primary" style="margin-top:16px">Retry</button>
                </div>
            `;
            document.getElementById('retry-load')?.addEventListener('click', () => this._loadMessages());
        }
    }

    _renderMessageList(messages) {
        const list = document.getElementById('message-list');
        
        if (messages.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📨</div>
                    <h3>No messages</h3>
                    <p>Your inbox is clean!</p>
                </div>
            `;
            return;
        }

        list.innerHTML = messages.map(msg => `
            <div class="msg-item ${msg.read ? '' : 'unread'}" data-msg-id="${msg.id}">
                <div class="msg-avatar" style="background: ${this._getColor(msg.from)}">
                    ${(msg.from || '?')[0].toUpperCase()}
                </div>
                <div class="msg-info">
                    <div class="msg-from">${msg.from || 'Unknown'}</div>
                    <div class="msg-subject">${msg.subject || '(No subject)'}</div>
                    <div class="msg-preview">${(msg.body || '').substring(0, 80)}</div>
                </div>
                <div class="msg-time">${this._formatTime(msg.timestamp)}</div>
            </div>
        `).join('');

        // Bind clicks
        list.querySelectorAll('.msg-item').forEach(item => {
            item.addEventListener('click', () => {
                const msgId = item.dataset.msgId;
                this._openMessage(msgId);
            });
        });
    }

    async _openMessage(msgId) {
        const msg = this.currentMessages.find(m => m.id === msgId);
        if (!msg) return;

        // Mark as read
        await imapClient.markAsRead(this.currentAccount.id, msgId);
        msg.read = true;
        this._renderMessageList(this.currentMessages);

        const view = document.getElementById('message-view');
        view.classList.remove('hidden');
        
        document.getElementById('msg-content').innerHTML = `
            <div class="msg-full-from">${msg.from}</div>
            <div class="msg-full-subject">${msg.subject || '(No subject)'}</div>
            <div class="msg-full-date">${new Date(msg.timestamp).toLocaleString()}</div>
            <div class="msg-full-body">${this._escapeHtml(msg.body || '')}</div>
        `;

        // Bind actions
        document.getElementById('msg-back').onclick = () => view.classList.add('hidden');
        document.getElementById('msg-delete').onclick = async () => {
            await imapClient.deleteMessage(this.currentAccount.id, msgId);
            view.classList.add('hidden');
            await this._loadMessages();
            this._showToast('Message deleted');
        };
        document.getElementById('msg-reply').onclick = () => {
            this._openCompose(msg.from, `Re: ${msg.subject}`);
            view.classList.add('hidden');
        };
    }

    _openCompose(to = '', subject = '', body = '') {
        const view = document.getElementById('compose-view');
        view.classList.remove('hidden');
        
        document.getElementById('compose-to').value = to;
        document.getElementById('compose-subject').value = subject;
        document.getElementById('compose-body').value = body;

        document.getElementById('compose-back').onclick = () => view.classList.add('hidden');
        document.getElementById('send-btn').onclick = async () => {
            const toVal = document.getElementById('compose-to').value;
            const subjVal = document.getElementById('compose-subject').value;
            const bodyVal = document.getElementById('compose-body').value;
            
            if (!toVal) { this._showToast('Please enter a recipient'); return; }
            
            try {
                await imapClient.sendMessage(this.currentAccount.id, toVal, subjVal, bodyVal);
                view.classList.add('hidden');
                this._showToast('Message sent!');
                await this._loadMessages();
            } catch (e) {
                this._showToast('Failed to send: ' + e.message);
            }
        };
    }

    _showSetup() {
        document.getElementById('message-list').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📧</div>
                <h3>Welcome to Nuxel Mail</h3>
                <p>Add your email account to get started</p>
                <button id="setup-account" class="btn-primary" style="margin-top:16px">Add Account</button>
            </div>
        `;
        document.getElementById('setup-account')?.addEventListener('click', () => this._showAddAccountDialog());
    }

    _showAddAccountDialog() {
        const email = prompt('Email address:');
        if (!email) return;
        const password = prompt('Password:');
        if (!password) return;
        const imapHost = prompt('IMAP server (e.g., imap.gmail.com):', 'imap.gmail.com');
        if (!imapHost) return;

        this._addAccount({ email, password, imapHost, imapPort: 993, smtpHost: imapHost.replace('imap', 'smtp'), smtpPort: 587 });
    }

    async _addAccount(config) {
        const account = await mailStorage.addAccount({
            email: config.email,
            imapHost: config.imapHost,
            imapPort: config.imapPort || 993,
            smtpHost: config.smtpHost || config.imapHost.replace('imap', 'smtp'),
            smtpPort: config.smtpPort || 587,
            useTls: true,
            name: config.email.split('@')[0],
        });

        await imapClient.connect(account);
        await imapClient.startIdle(account.id);
        
        this.accounts.push(account);
        this.currentAccount = account;
        await this._loadMessages();
        this._showToast('Account added!');
    }

    _bindEvents() {
        // Menu button
        document.getElementById('menu-btn').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });
        document.getElementById('sidebar-close').addEventListener('click', () => {
            document.getElementById('sidebar').classList.remove('open');
        });

        // Compose button
        document.getElementById('compose-btn').addEventListener('click', () => this._openCompose());

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => this._loadMessages());
    }

    _getColor(str) {
        const colors = ['#FF9800','#E91E63','#9C27B0','#2196F3','#4CAF50','#F44336','#607D8B','#795548'];
        let hash = 0;
        for (let i = 0; i < (str || '').length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
        return colors[Math.abs(hash) % colors.length];
    }

    _formatTime(ts) {
        if (!ts) return '';
        const date = new Date(ts);
        const now = new Date();
        const diff = now - date;
        if (diff < 86400000) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        if (diff < 604800000) return date.toLocaleDateString([], { weekday: 'short' });
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    _showToast(msg) {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.mailApp = new MailApp();
});
