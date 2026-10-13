// Nuxel Home - Search
// App search functionality with fuzzy matching

class SearchManager {
    constructor() {
        this.overlay = document.getElementById('search-overlay');
        this.input = document.getElementById('search-input');
        this.results = document.getElementById('search-results');
        this.closeBtn = document.getElementById('search-close');
        
        this.isOpen = false;
        this.searchHistory = [];
        this._loadHistory();
        this._init();
    }

    _init() {
        this._bindEvents();
    }

    _bindEvents() {
        // Open search (called from launcher gesture)
        document.addEventListener('swipe:search', () => this.open());
        
        // Search input handler
        this.input.addEventListener('input', () => {
            const query = this.input.value.trim();
            if (query.length >= 1) {
                this._performSearch(query);
            } else {
                this._showHistory();
            }
        });

        // Close button
        this.closeBtn.addEventListener('click', () => this.close());

        // Keyboard navigation
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.close();
            }
            if (e.key === 'Enter' && this.input.value.trim()) {
                const results = this.results.querySelectorAll('.search-result-item');
                if (results.length > 0) {
                    results[0].click();
                }
            }
        });
    }

    open() {
        if (this.isOpen) return;
        this.isOpen = true;
        this.overlay.classList.remove('hidden');
        this.input.value = '';
        this._showHistory();
        
        // Focus input with slight delay for animation
        setTimeout(() => this.input.focus(), 100);
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;
        this.overlay.classList.add('hidden');
        this.input.blur();
    }

    toggle() {
        if (this.isOpen) this.close();
        else this.open();
    }

    _performSearch(query) {
        const results = appRegistry.searchApps(query);
        
        if (results.length === 0) {
            this.results.innerHTML = `
                <div class="search-no-results">
                    <div class="no-results-icon">🔍</div>
                    <h3>No results for "${query}"</h3>
                    <p>Try a different search term or browse apps</p>
                </div>
            `;
            return;
        }

        const sections = this._categorizeResults(results);
        let html = '';

        for (const [category, apps] of Object.entries(sections)) {
            if (apps.length === 0) continue;
            
            const categoryLabel = category.charAt(0).toUpperCase() + category.slice(1);
            html += `
                <div class="search-section">
                    <div class="search-section-header">${categoryLabel}</div>
                    ${apps.map(app => {
                        const highlightedName = this._highlightMatch(app.name, query);
                        const highlightedDesc = this._highlightMatch(app.description, query);
                        return `
                            <div class="search-result-item press-effect" 
                                 data-app-id="${app.id}" tabindex="0">
                                <div class="result-icon" 
                                     style="background: ${app.color}33">
                                    <span>${app.icon}</span>
                                </div>
                                <div class="result-info">
                                    <div class="result-name">${highlightedName}</div>
                                    <div class="result-desc">${highlightedDesc}</div>
                                </div>
                                <span class="result-action">Open</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        this.results.innerHTML = html;

        // Bind click events on results
        this.results.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const appId = item.dataset.appId;
                this._addToHistory(this.input.value.trim());
                this.close();
                appRegistry.launchApp(appId);
            });
        });
    }

    _categorizeResults(results) {
        const categories = {};
        for (const app of results) {
            const cat = app.category || 'other';
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(app);
        }
        return categories;
    }

    _highlightMatch(text, query) {
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<span class="highlight-match">$1</span>');
    }

    _showHistory() {
        if (this.searchHistory.length === 0) {
            // Show suggestions
            const suggestions = ['Phone', 'Messages', 'Settings', 'Mail', 'Camera'];
            this.results.innerHTML = `
                <div class="search-section">
                    <div class="search-section-header">Quick Suggestions</div>
                    <div class="search-suggestions">
                        ${suggestions.map(s => `
                            <span class="search-suggestion-chip press-effect">${s}</span>
                        `).join('')}
                    </div>
                </div>
            `;

            // Bind suggestion clicks
            this.results.querySelectorAll('.search-suggestion-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    this.input.value = chip.textContent;
                    this._performSearch(chip.textContent);
                });
            });
            return;
        }

        this.results.innerHTML = `
            <div class="search-section">
                <div class="search-section-header">Recent Searches</div>
                <div class="recent-searches">
                    ${this.searchHistory.map(q => `
                        <div class="recent-search-item press-effect" data-query="${q}">
                            <span class="recent-icon">🕐</span>
                            <span>${q}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        this.results.querySelectorAll('.recent-search-item').forEach(item => {
            item.addEventListener('click', () => {
                this.input.value = item.dataset.query;
                this._performSearch(item.dataset.query);
            });
        });
    }

    _addToHistory(query) {
        if (!query) return;
        this.searchHistory = this.searchHistory.filter(q => q !== query);
        this.searchHistory.unshift(query);
        if (this.searchHistory.length > 10) {
            this.searchHistory = this.searchHistory.slice(0, 10);
        }
        try {
            localStorage.setItem('nuxel-search-history', JSON.stringify(this.searchHistory));
        } catch (e) {}
    }

    _loadHistory() {
        try {
            const data = localStorage.getItem('nuxel-search-history');
            if (data) this.searchHistory = JSON.parse(data);
        } catch (e) {}
    }
}

function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

document.addEventListener('DOMContentLoaded', () => {
    window.search = new SearchManager();
});
