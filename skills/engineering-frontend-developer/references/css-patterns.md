# Modern CSS Patterns

Production-ready CSS patterns using modern features (2024+). No vendor prefixes; logical properties used where appropriate.

---

## CSS Grid Responsive Dashboard Layout

Sidebar collapses below the main content on narrow viewports using `grid-template-areas`.

```css
.dashboard {
  display: grid;
  grid-template-columns: 260px 1fr;
  grid-template-rows: auto 1fr auto;
  grid-template-areas:
    "sidebar header"
    "sidebar main"
    "sidebar footer";
  min-block-size: 100dvh;
}

.dashboard__header  { grid-area: header; }
.dashboard__sidebar { grid-area: sidebar; background: var(--surface-secondary); }
.dashboard__main    { grid-area: main; padding: 2rem; }
.dashboard__footer  { grid-area: footer; }

@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;
    grid-template-areas:
      "header"
      "main"
      "sidebar"
      "footer";
  }
}
```

---

## Container Queries for Responsive Components

Components adapt to their container width, not the viewport. This makes them truly portable across layouts.

```css
.card-container {
  container-type: inline-size;
  container-name: card;
}

.card {
  display: grid;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: var(--surface-primary);
}

/* Stack vertically when container is narrow */
@container card (max-width: 400px) {
  .card {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .card__image {
    max-inline-size: 200px;
    margin-inline: auto;
  }
}

/* Side-by-side when container is wide */
@container card (min-width: 401px) {
  .card {
    grid-template-columns: 200px 1fr;
    align-items: start;
  }
}
```

---

## CSS Custom Properties for Theming (Light/Dark)

Uses `color-scheme` for native form control adaptation and custom properties for all custom UI.

```css
:root {
  color-scheme: light dark;

  /* Light theme (default) */
  --color-bg:       #ffffff;
  --color-surface:  #f8f9fa;
  --color-text:     #1a1a2e;
  --color-text-muted: #6b7280;
  --color-primary:  #2563eb;
  --color-border:   #e5e7eb;
  --shadow-sm:      0 1px 2px rgb(0 0 0 / 0.05);
  --shadow-md:      0 4px 6px rgb(0 0 0 / 0.07);
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-bg:       #0f172a;
    --color-surface:  #1e293b;
    --color-text:     #f1f5f9;
    --color-text-muted: #94a3b8;
    --color-primary:  #60a5fa;
    --color-border:   #334155;
    --shadow-sm:      0 1px 2px rgb(0 0 0 / 0.3);
    --shadow-md:      0 4px 6px rgb(0 0 0 / 0.4);
  }
}

/* Manual override via data attribute */
[data-theme="dark"] {
  --color-bg:       #0f172a;
  --color-surface:  #1e293b;
  --color-text:     #f1f5f9;
  --color-text-muted: #94a3b8;
  --color-primary:  #60a5fa;
  --color-border:   #334155;
}

body {
  background: var(--color-bg);
  color: var(--color-text);
}
```

---

## Fluid Typography with clamp()

Font sizes scale smoothly between a minimum and maximum, eliminating breakpoint jumps.

```css
:root {
  /* Scale between 320px and 1200px viewport */
  --text-sm:   clamp(0.875rem, 0.8rem + 0.25vw, 1rem);
  --text-base: clamp(1rem, 0.9rem + 0.4vw, 1.125rem);
  --text-lg:   clamp(1.25rem, 1rem + 0.75vw, 1.5rem);
  --text-xl:   clamp(1.5rem, 1.1rem + 1.2vw, 2rem);
  --text-2xl:  clamp(2rem, 1.4rem + 2vw, 3rem);
  --text-hero: clamp(2.5rem, 1.5rem + 3.5vw, 5rem);
}

h1 { font-size: var(--text-hero); line-height: 1.1; }
h2 { font-size: var(--text-2xl);  line-height: 1.2; }
h3 { font-size: var(--text-xl);   line-height: 1.3; }
p  { font-size: var(--text-base); line-height: 1.6; }
```

---

## CSS-Only Skeleton Loading Animation

Animated placeholder that mimics content layout before data loads. No JavaScript required.

```css
.skeleton {
  background: var(--color-surface, #e5e7eb);
  border-radius: 0.375rem;
  position: relative;
  overflow: hidden;
}

.skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgb(255 255 255 / 0.4) 50%,
    transparent 100%
  );
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
}

@keyframes skeleton-shimmer {
  from { translate: -100% 0; }
  to   { translate: 100% 0; }
}

/* Skeleton variants */
.skeleton--text {
  block-size: 1rem;
  inline-size: 80%;
  margin-block-end: 0.5rem;
}

.skeleton--heading {
  block-size: 1.5rem;
  inline-size: 60%;
  margin-block-end: 1rem;
}

.skeleton--avatar {
  block-size: 3rem;
  inline-size: 3rem;
  border-radius: 50%;
}

.skeleton--thumbnail {
  block-size: 200px;
  inline-size: 100%;
}
```

---

## Scroll-Snap Carousel

A horizontal carousel with snap points. No JavaScript needed for the core scrolling behavior.

```css
.carousel {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scroll-padding-inline: 1rem;
  padding: 1rem;

  /* Hide scrollbar but keep functionality */
  scrollbar-width: none;
}

.carousel::-webkit-scrollbar {
  display: none;
}

.carousel__item {
  flex: 0 0 min(300px, 80vw);
  scroll-snap-align: start;
  border-radius: 0.75rem;
  overflow: hidden;
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.carousel__item img {
  inline-size: 100%;
  block-size: 200px;
  object-fit: cover;
}

/* Full-width slide variant */
.carousel--fullwidth .carousel__item {
  flex: 0 0 100%;
  scroll-snap-align: center;
}
```

---

## @layer for Managing Specificity

Cascade layers let you control which styles win without fighting specificity. Essential for component libraries that must coexist with application styles.

```css
/* Declare layer order: lowest priority first */
@layer reset, base, components, utilities;

@layer reset {
  *,
  *::before,
  *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
}

@layer base {
  body {
    font-family: system-ui, sans-serif;
    line-height: 1.6;
    color: var(--color-text);
    background: var(--color-bg);
  }

  a { color: var(--color-primary); text-decoration: none; }
  a:hover { text-decoration: underline; }
}

@layer components {
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding-block: 0.625rem;
    padding-inline: 1.25rem;
    border-radius: 0.5rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    background: var(--color-primary);
    color: white;
  }
}

@layer utilities {
  /* Utilities always win over components */
  .text-center { text-align: center; }
  .mt-4 { margin-block-start: 1rem; }
  .hidden { display: none; }
}
```

Application code can add unlayered styles that override all layers, or add its own layers between the declared ones.

---

## View Transitions API for Page Transitions

Animate between page states with the View Transitions API. Works for both SPA navigation and MPA with `@view-transition`.

### SPA Navigation

```css
/* Default crossfade is automatic; customize specific elements */
::view-transition-old(main-content) {
  animation: slide-out 0.25s ease-in forwards;
}

::view-transition-new(main-content) {
  animation: slide-in 0.25s ease-out forwards;
}

@keyframes slide-out {
  to { translate: -100% 0; opacity: 0; }
}

@keyframes slide-in {
  from { translate: 100% 0; opacity: 0; }
}

/* Tag the element to participate in the transition */
.page-content {
  view-transition-name: main-content;
}

/* Shared element transition (e.g., thumbnail to hero) */
.product-card__image {
  view-transition-name: product-hero;
}

.product-detail__image {
  view-transition-name: product-hero;
}
```

### JavaScript trigger

```js
document.startViewTransition(() => {
  // Update the DOM here (e.g., swap route content)
  updateRoute(newPath);
});
```

### MPA (multi-page) opt-in

```css
@view-transition {
  navigation: auto;
}
```

---

## :has() Selector for Parent-Based Styling

Style parent elements based on their children's state, eliminating JavaScript class toggling in many cases.

```css
/* Highlight form group when its input is focused */
.form-group:has(input:focus) {
  outline: 2px solid var(--color-primary);
  outline-offset: 4px;
  border-radius: 0.375rem;
}

/* Show helper text only when input is invalid and not empty */
.form-group:has(input:invalid:not(:placeholder-shown)) .helper-text {
  display: block;
  color: var(--color-error, #dc2626);
}

/* Card with image gets different layout than card without */
.card:has(> img) {
  grid-template-rows: 200px 1fr;
}

.card:not(:has(> img)) {
  grid-template-rows: 1fr;
  padding-block-start: 2rem;
}

/* Disable submit button styling when required fields are empty */
form:has(:required:placeholder-shown) button[type="submit"] {
  opacity: 0.5;
  pointer-events: none;
}

/* Navigation item active state based on nested aria-current */
.nav-item:has(a[aria-current="page"]) {
  background: var(--color-surface);
  border-inline-start: 3px solid var(--color-primary);
}
```
