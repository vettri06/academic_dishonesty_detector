// Theme Management System
class ThemeManager {
    constructor() {
        this.settings = this.loadSettings();
        this.applySettings();
        this.bindEvents();
    }

    loadSettings() {
        const defaultSettings = {
            theme: 'light',
            background: {
                type: 'gradient',
                value: 'default'
            }
        };

        try {
            const saved = localStorage.getItem('academicThemeSettings');
            return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
        } catch {
            return defaultSettings;
        }
    }

    saveSettings() {
        try {
            localStorage.setItem('academicThemeSettings', JSON.stringify(this.settings));
        } catch (error) {
            console.error('Failed to save theme settings:', error);
        }
    }

    applySettings() {
        // Apply theme
        this.applyTheme(this.settings.theme);
        
        // Apply background
        this.applyBackground(this.settings.background);
        
        // Update UI elements
        this.updateUI();
    }

    applyTheme(theme) {
        const html = document.documentElement;
        
        if (theme === 'auto') {
            // Check system preference
            const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            html.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
        } else {
            html.setAttribute('data-bs-theme', theme);
        }
        
        this.settings.theme = theme;
    }

    applyBackground(background) {
        const body = document.body;
        
        // Remove all background classes
        body.className = body.className.replace(/\bbg-\S+/g, '');
        
        switch (background.type) {
            case 'gradient':
                body.classList.add(`bg-gradient-${background.value}`);
                break;
            case 'solid':
                body.classList.add(`bg-solid-${background.value}`);
                break;
            case 'custom':
                body.style.background = background.value;
                break;
        }
        
        this.settings.background = background;
    }

    bindEvents() {
        // Theme buttons
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const theme = e.target.closest('.theme-btn').dataset.theme;
                this.setTheme(theme);
            });
        });

        // Quick theme toggle
        document.querySelectorAll('.theme-quick-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const theme = e.target.closest('.theme-quick-toggle').dataset.theme;
                this.setTheme(theme);
            });
        });

        // Background options
        document.querySelectorAll('.background-option').forEach(option => {
            option.addEventListener('click', (e) => {
                const bgType = option.dataset.bgType;
                const bgValue = option.dataset.bgValue;
                
                // Update active state
                document.querySelectorAll('.background-option').forEach(opt => {
                    opt.classList.remove('active');
                });
                option.classList.add('active');
                
                this.setBackground(bgType, bgValue);
            });
        });

        // Custom color
        document.getElementById('applyCustomColor')?.addEventListener('click', () => {
            const color = document.getElementById('customColor').value;
            this.setBackground('custom', color);
        });

        // Save settings
        document.getElementById('saveSettings')?.addEventListener('click', () => {
            this.saveSettings();
            this.showToast('Settings saved successfully!');
            bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
        });

        // System theme change listener
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (this.settings.theme === 'auto') {
                this.applyTheme('auto');
            }
        });
    }

    setTheme(theme) {
        this.applyTheme(theme);
        this.updateThemeButtons();
        this.saveSettings();
        this.showToast(`Theme changed to ${theme} mode`);
    }

    setBackground(type, value) {
        this.applyBackground({ type, value });
        this.saveSettings();
    }

    updateThemeButtons() {
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === this.settings.theme);
        });
    }

    updateUI() {
        this.updateThemeButtons();
        
        // Update background options
        document.querySelectorAll('.background-option').forEach(option => {
            const isActive = option.dataset.bgType === this.settings.background.type && 
                            option.dataset.bgValue === this.settings.background.value;
            option.classList.toggle('active', isActive);
        });
    }

    showToast(message) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'position-fixed bottom-0 end-0 p-3';
        toast.style.zIndex = '9999';
        
        toast.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-header">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    <strong class="me-auto">System</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    // Public method to get current settings
    getSettings() {
        return this.settings;
    }

    // Public method to reset to defaults
    resetToDefaults() {
        this.settings = {
            theme: 'light',
            background: {
                type: 'gradient',
                value: 'default'
            }
        };
        this.applySettings();
        this.saveSettings();
        this.showToast('Settings reset to defaults');
    }
}

// Initialize theme manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.themeManager = new ThemeManager();
    
    // Add keyboard shortcut for theme toggle (Ctrl+Shift+T)
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'T') {
            e.preventDefault();
            const currentTheme = window.themeManager.getSettings().theme;
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            window.themeManager.setTheme(newTheme);
        }
    });
});

// Export for global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeManager;
}