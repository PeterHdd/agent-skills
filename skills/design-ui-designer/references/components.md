# Component Patterns

Build base components (button, input, card, nav, alert) using only tokens. Document all five states for each interactive component. When a component needs more than three variants, reconsider whether it should be split into separate components.

When adding motion, keep durations under 300ms for micro-interactions and under 500ms for transitions. Use ease-out for entrances, ease-in for exits.

## Button

```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  min-height: 44px; /* touch target */
  font-family: var(--font-family-primary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.btn:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.btn--primary {
  background-color: var(--color-primary-500);
  color: white;
}

.btn--primary:hover:not(:disabled) {
  background-color: var(--color-primary-600);
  box-shadow: var(--shadow-md);
}

.btn--primary:active:not(:disabled) {
  background-color: var(--color-primary-700);
  box-shadow: none;
}
```

## Form Input

```css
.form-input {
  width: 100%;
  padding: var(--space-3);
  min-height: 44px;
  font-family: var(--font-family-primary);
  font-size: var(--font-size-base);
  color: var(--color-secondary-900);
  background-color: white;
  border: 1px solid var(--color-secondary-300);
  border-radius: 0.375rem;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgb(59 130 246 / 0.15);
}

.form-input--error {
  border-color: var(--color-error);
}

.form-input--error:focus {
  box-shadow: 0 0 0 3px rgb(239 68 68 / 0.15);
}
```

## Card

```css
.card {
  background-color: white;
  border: 1px solid var(--color-secondary-200);
  border-radius: 0.5rem;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: box-shadow var(--transition-normal), transform var(--transition-normal);
}

.card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

@media (prefers-reduced-motion: reduce) {
  .card:hover {
    transform: none;
  }
}
```

## Responsive Strategy

Base styles target mobile (320px+) and progressively add layout complexity at wider breakpoints.

```css
/* Mobile first: base styles target 320px+ */

/* sm: 640px+ */
@media (min-width: 640px) {
  .container { max-width: 640px; }
}

/* md: 768px+ */
@media (min-width: 768px) {
  .container { max-width: 768px; }
}

/* lg: 1024px+ */
@media (min-width: 1024px) {
  .container { max-width: 1024px; }
}

/* xl: 1280px+ */
@media (min-width: 1280px) {
  .container { max-width: 1280px; }
}
```

Test layouts at 320px, 640px, 768px, 1024px, and 1280px.
