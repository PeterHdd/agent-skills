---
name: engineering-rapid-prototyper
description: "Build functional prototypes and MVPs at maximum speed to validate ideas through working software. Use when you need proof-of-concept development, rapid iteration on user feedback, no-code or low-code solutions, backend-as-a-service integration, A/B testing scaffolding, quick feature validation, or modular architectures designed for fast experimentation and learning."
metadata:
  version: "1.0.0"
---

# Rapid Prototyping Guide

## Overview
This guide covers fast proof-of-concept development and MVP creation. Use it when building prototypes to validate hypotheses, setting up A/B testing, or choosing rapid development stacks that prioritize speed-to-deploy over production hardening.

## Stack Selection Guide

### How to choose tools
- When authentication is needed, use Clerk or NextAuth for instant setup -- do not build custom auth for a prototype.
- When a database is needed, use Prisma + Supabase for instant hosting, schema management, and row-level security.
- When deployment is needed, use Vercel for instant hosting and preview URLs on every PR.
- When no-code/low-code can cover the requirement, use it -- speed to validation matters more than custom code.
- When building, implement core functionality first, polish and edge cases later.
- When selecting features, build only what is necessary to test core hypotheses (3-5 features maximum).

### Recommended Stack
- **Framework**: Next.js 14+
- **UI**: shadcn/ui + react-hook-form + Zod validation
- **State**: Zustand
- **Database**: Prisma + Supabase
- **Auth**: Clerk or NextAuth
- **Animation**: Framer Motion
- **Deploy**: Vercel

See [Stack Setup](references/stack-setup.md) for the full package.json and shadcn/ui install commands.

## Workflow

### Day 1 Morning: Requirements and Hypothesis Definition
- Define core hypotheses to test.
- Identify minimum viable features (3-5 maximum).
- Choose rapid development stack.
- Set up analytics and feedback collection.

### Day 1 Afternoon: Foundation Setup
- Set up Next.js project with essential dependencies.
- Configure authentication with Clerk or similar.
- Set up database with Prisma and Supabase.
- Deploy to Vercel for instant hosting and preview URLs.

### Day 2-3: Core Feature Implementation
- Build primary user flows with shadcn/ui components.
- Implement data models and API endpoints.
- Add basic error handling and validation.
- Create simple analytics and A/B testing infrastructure.

### Day 3-4: User Testing and Iteration Setup
- Deploy working prototype with feedback collection.
- Set up user testing sessions with target audience.
- Implement basic metrics tracking and success criteria monitoring.
- Create rapid iteration workflow for daily improvements.

See [Code Examples](references/code-examples.md) for a feedback form component and A/B testing hook.

## Scripts

- `scripts/scaffold.sh` -- Create a Next.js + TypeScript + Tailwind project structure with minimal boilerplate files (no npm install). Run with `--help` for options.

## Guidelines
- Establish clear success metrics and validation criteria before building.
- Build modular architectures that allow quick feature additions or removals.
- Implement user feedback collection mechanisms from the start.
- Plan transition paths from prototype to production-ready system.
- Use pre-built components and templates whenever possible.

## References

- [Stack Setup](references/stack-setup.md) -- Package.json and shadcn/ui install commands.
- [Code Examples](references/code-examples.md) -- Feedback form component and A/B testing hook.
- [Full Stack Integration](references/full-stack-integration.md) -- Prisma schema, Supabase + Clerk auth, server actions, tRPC, file uploads, and email with Resend.
- [UI Patterns](references/ui-patterns.md) -- Data tables, command palette, form wizard, dashboard layout, toasts, and loading skeletons with shadcn/ui.
