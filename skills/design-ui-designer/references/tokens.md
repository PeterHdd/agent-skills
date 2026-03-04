# Design Tokens

## Full CSS Custom Properties (Light Theme)

```css
:root {
  /* Primary */
  --color-primary-50: #EFF6FF;
  --color-primary-100: #DBEAFE;
  --color-primary-300: #93C5FD;
  --color-primary-500: #3B82F6;
  --color-primary-600: #2563EB;
  --color-primary-700: #1D4ED8;
  --color-primary-900: #1E3A8A;

  /* Secondary (neutral) */
  --color-secondary-50: #F9FAFB;
  --color-secondary-100: #F3F4F6;
  --color-secondary-200: #E5E7EB;
  --color-secondary-300: #D1D5DB;
  --color-secondary-500: #6B7280;
  --color-secondary-700: #374151;
  --color-secondary-900: #111827;

  /* Semantic */
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  --color-info: #3B82F6;

  /* Typography */
  --font-family-primary: 'Inter', system-ui, sans-serif;
  --font-family-mono: 'JetBrains Mono', monospace;

  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;
  --font-size-4xl: 2.25rem;

  /* Spacing (4px base) */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);

  /* Motion */
  --transition-fast: 150ms ease-out;
  --transition-normal: 300ms ease-out;
}
```

## Dark Theme

When designing for both light and dark themes, invert the semantic meaning of the neutral scale (light-theme neutral-100 becomes dark-theme background) rather than creating separate token names.

```css
/* Dark theme: invert the neutral scale, shift primary toward lighter end */
[data-theme="dark"] {
  --color-primary-100: #1E3A8A;
  --color-primary-500: #60A5FA;
  --color-primary-900: #DBEAFE;

  --color-secondary-50: #111827;
  --color-secondary-100: #1F2937;
  --color-secondary-200: #374151;
  --color-secondary-300: #4B5563;
  --color-secondary-500: #9CA3AF;
  --color-secondary-700: #E5E7EB;
  --color-secondary-900: #F9FAFB;
}

/* System preference fallback */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-primary-100: #1E3A8A;
    --color-primary-500: #60A5FA;
    --color-primary-900: #DBEAFE;
    --color-secondary-50: #111827;
    --color-secondary-100: #1F2937;
    --color-secondary-200: #374151;
    --color-secondary-300: #4B5563;
    --color-secondary-500: #9CA3AF;
    --color-secondary-700: #E5E7EB;
    --color-secondary-900: #F9FAFB;
  }
}
```

## Theme Toggle

### CSS

```css
.theme-toggle {
  display: inline-flex;
  align-items: center;
  background: var(--color-secondary-100);
  border: 1px solid var(--color-secondary-300);
  border-radius: 24px;
  padding: 4px;
}

.theme-toggle-option {
  padding: 8px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-secondary-500);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.theme-toggle-option.active {
  background: var(--color-primary-500);
  color: white;
}
```

### HTML

```html
<div class="theme-toggle" role="radiogroup" aria-label="Theme selection">
  <button class="theme-toggle-option" data-theme="light" role="radio" aria-checked="false">Light</button>
  <button class="theme-toggle-option" data-theme="dark" role="radio" aria-checked="false">Dark</button>
  <button class="theme-toggle-option active" data-theme="system" role="radio" aria-checked="true">System</button>
</div>
```

### JavaScript

```javascript
class ThemeManager {
  constructor() {
    this.currentTheme = this.getStoredTheme() || 'system';
    this.applyTheme(this.currentTheme);
    this.initializeToggle();
  }

  getStoredTheme() {
    return localStorage.getItem('theme');
  }

  applyTheme(theme) {
    if (theme === 'system') {
      document.documentElement.removeAttribute('data-theme');
      localStorage.removeItem('theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
    }
    this.currentTheme = theme;
    this.updateToggleUI();
  }

  initializeToggle() {
    const toggle = document.querySelector('.theme-toggle');
    if (!toggle) return;
    toggle.addEventListener('click', (e) => {
      if (e.target.matches('.theme-toggle-option')) {
        this.applyTheme(e.target.dataset.theme);
      }
    });
  }

  updateToggleUI() {
    document.querySelectorAll('.theme-toggle-option').forEach(option => {
      const isActive = option.dataset.theme === this.currentTheme;
      option.classList.toggle('active', isActive);
      option.setAttribute('aria-checked', isActive);
    });
  }
}

document.addEventListener('DOMContentLoaded', () => new ThemeManager());
```
