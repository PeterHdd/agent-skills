---
name: engineering-frontend-developer
description: "Build modern web applications with React, Vue, Angular, or Svelte, focusing on performance and accessibility. Use when you need component library development, TypeScript UI implementation, responsive layouts with CSS Grid and Flexbox, Core Web Vitals optimization, service worker offline support, code splitting, ARIA accessibility, Storybook integration, or frontend API client architecture."
metadata:
  version: "1.0.0"
---

# Frontend Development Guide

## Overview
This guide covers modern frontend development with React, Vue, Angular, and Svelte, including component architecture, performance optimization, accessibility, and testing. Use it when building web applications, component libraries, or optimizing frontend performance.

## Framework and Layout Decision Rules

- When choosing a framework, match it to team expertise and project constraints; default to React for broad ecosystem needs, Vue for progressive enhancement into existing pages, Svelte for bundle-size-critical apps, and Angular when the project requires an opinionated full-framework with built-in DI and routing.
- When implementing a design, use CSS Grid for two-dimensional page layouts and Flexbox for one-dimensional component alignment; avoid absolute positioning for layout purposes because it breaks responsive reflow.
- When building a component library, expose each component as a named export with TypeScript props interface, a Storybook story, and a unit test -- components without all three are not merged.
- When integrating with backend APIs, centralize fetch logic in a typed API client layer (e.g., a single `api.ts` module using `fetch` or `axios` with interceptors) so auth headers, error transforms, and retries are handled in one place.

## Performance Decision Rules

- When a page's Largest Contentful Paint exceeds 2.5 seconds in Lighthouse CI, treat it as a blocking bug -- profile with Chrome DevTools Performance tab and fix the largest bottleneck before merging.
- When adding animations, use CSS `transform` and `opacity` properties (compositor-only) rather than `width`, `height`, or `top`/`left` to avoid triggering layout recalculations that cause jank.
- When the app needs offline support, register a service worker with a cache-first strategy for static assets and a network-first strategy for API requests, falling back to cached responses when offline.
- When initial JS bundle exceeds the budget (e.g., 200 KB gzipped), add route-based code splitting with `React.lazy()` or dynamic `import()` and defer non-critical scripts below the fold.
- When supporting older browsers, define a browserslist config and let the build tool (Vite, Webpack) auto-polyfill; do not manually add polyfills or feature checks unless browserslist coverage is insufficient.
- When adding images, use `<picture>` with WebP/AVIF sources and explicit `width`/`height` attributes to prevent layout shift; for images below the fold, add `loading="lazy"`.
- When a route is not needed on initial page load, wrap it in `React.lazy()` (or framework equivalent) with a `<Suspense>` fallback so the main bundle excludes that route's code.
- When serving static assets, configure the CDN or server to set `Cache-Control: public, max-age=31536000, immutable` on content-hashed filenames and `no-cache` on `index.html`.

## Accessibility Decision Rules

- When building any interactive component, add ARIA attributes, keyboard handlers (`Enter`, `Space`, `Escape` as appropriate), and test with axe-core before marking the task complete.
- When building forms, associate every `<input>` with a `<label>` via `htmlFor`/`id`, provide visible error messages linked with `aria-describedby`, and ensure the form is fully operable with keyboard-only navigation.
- When using color to convey meaning (e.g., error states, status badges), always include a secondary indicator (icon, text, pattern) so color-blind users can distinguish states.
- When adding a modal or dropdown, trap focus inside the element while it is open and return focus to the trigger element on close; test by tabbing through the entire flow without a mouse.
- When a pull request adds a new interactive component, the PR must include an axe-core integration test that asserts zero WCAG 2.1 AA violations before it can be merged.

## Code Quality Decision Rules

- When writing tests, require every component to have at least one unit test covering its primary render path and one interaction test (click, keyboard) -- enforce via a CI coverage gate of 80% line coverage minimum.
- When starting a project, enable `strict: true` in `tsconfig.json` on day one; retrofitting strict mode later is exponentially harder as the codebase grows.
- When an API call or async operation fails, display a user-facing error message with a retry action -- never swallow errors silently or show raw exception text.
- When a component file exceeds 300 lines, split it into smaller sub-components with a shared barrel export; large files signal mixed responsibilities.
- When setting up CI, include lint (ESLint), type-check (`tsc --noEmit`), test (Vitest/Jest), and bundle-size check as required gates -- all four must pass before merge.

## Workflow

### Step 1: Project Setup and Architecture
- Set up modern development environment with proper tooling.
- Configure build optimization and performance monitoring.
- Establish testing framework and CI/CD integration.
- Create component architecture and design system foundation.

### Step 2: Component Development
- Create reusable component library with proper TypeScript types.
- Implement responsive design with mobile-first approach.
- Build accessibility into components from the start.
- Create comprehensive unit tests for all components.

### Step 3: Performance Optimization
- Implement code splitting and lazy loading strategies.
- Optimize images and assets for web delivery.
- Monitor Core Web Vitals and optimize accordingly.
- Set up performance budgets and monitoring.

### Step 4: Testing and Quality Assurance
- Write comprehensive unit and integration tests.
- Perform accessibility testing with real assistive technologies.
- Test cross-browser compatibility and responsive behavior.
- Implement end-to-end testing for critical user flows.

## Reference

### Lighthouse CI Targets
- Performance score: 90+
- All interactive elements keyboard-navigable with visible focus indicators
- axe-core: zero violations at WCAG 2.1 AA level
- Bundle size: < 200 KB gzipped for initial JS (enforce with `bundlesize` or equivalent)
- Zero TypeScript `any` casts in production code; `strict: true` enabled in tsconfig

## Scripts

- `scripts/check_bundle.sh` -- Analyze a build output directory for JS and CSS bundle sizes, with gzip estimates and configurable warning/error thresholds. Run with `--help` for options.

See [DataTable Component](references/data-table.md) for a full virtualized DataTable implementation in React + TypeScript.
See [React Component Patterns](references/react-patterns.md) for compound components, custom hooks, error boundaries, optimistic UI, and form validation patterns.
See [TypeScript Patterns](references/typescript-patterns.md) for discriminated unions, polymorphic components, branded types, and type-safe API clients.
See [CSS Patterns](references/css-patterns.md) for modern CSS Grid layouts, container queries, theming, view transitions, and :has() selectors.
