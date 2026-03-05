# Agent Skills

A collection of 9 engineering AI agent skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Each skill gives Claude deep domain expertise — decision rules, production-grade code patterns, reference material, and runnable scripts.

Built to the [Agent Skills Spec](https://agentskills.io).

## Quick Start

Install the [skills CLI](https://www.npmjs.com/package/skills):

```bash
# Install a single skill
npx skills add PeterHdd/agent-skills --skill engineering-frontend-developer

# Install all 9 skills
npx skills add PeterHdd/agent-skills --all
```

After installing, the skill is available in your Claude Code sessions automatically. Claude reads the skill's decision rules and uses them when relevant to your task.

## How It Works

Each skill is a self-contained directory:

```
skills/engineering-frontend-developer/
├── SKILL.md              # Decision rules and workflow (loaded by Claude)
├── references/           # Deep code patterns and examples
│   ├── react-patterns.md
│   ├── typescript-patterns.md
│   └── css-patterns.md
└── scripts/              # Runnable CLI tools
    └── check_bundle.sh
```

- **SKILL.md** — The core file. Contains "when X, do Y" decision rules that guide Claude's behavior. Claude reads this automatically when the skill is relevant.
- **references/** — Detailed code examples, architecture patterns, and implementation guides that SKILL.md links to. Claude reads these on demand when deeper context is needed.
- **scripts/** — Standalone CLI tools (Python/Bash) that Claude can run during your session. All scripts support `--help` and output structured markdown.

## Usage Examples

### Frontend Development

```bash
npx skills add PeterHdd/agent-skills --skill engineering-frontend-developer
```

Then in Claude Code:

```
> Build a dashboard with a data table that supports sorting, filtering, and pagination

Claude will use React patterns from the skill — compound components, TypeScript generics,
CSS Grid layout, virtualized rendering — and check your bundle size stays under 200KB.
```

### Backend Architecture

```bash
npx skills add PeterHdd/agent-skills --skill engineering-backend-architect
```

```
> Design the API layer for a multi-tenant SaaS app

Claude will apply distributed patterns (circuit breaker, saga, outbox), set up
cursor pagination, rate limiting with Redis, and Zod validation middleware.
```

### System Design

```bash
npx skills add PeterHdd/agent-skills --skill engineering-system-designer
```

```
> Design a URL shortener that handles 100M URLs per month

Claude will run capacity calculations, design the schema with sharding strategy,
choose cache-aside with Redis, and produce a full system design document.
```

### DevOps

```bash
npx skills add PeterHdd/agent-skills --skill engineering-devops-automator
```

```
> Set up CI/CD for our Node.js app with Docker and Kubernetes

Claude will generate multi-stage Dockerfiles, Kubernetes Deployments with health probes,
HPA autoscaling, GitHub Actions pipelines, and Prometheus monitoring.
```

### Mobile App Development

```bash
npx skills add PeterHdd/agent-skills --skill engineering-mobile-app-builder
```

```
> Build an offline-first React Native app with push notifications

Claude will implement a mutation queue with AsyncStorage, NetInfo-based sync,
Firebase push notifications, and Zustand state management with MMKV persistence.
```

## Available Skills (9 Engineering Skills)

| Skill | What It Does |
|-------|-------------|
| `engineering-senior-developer` | Technology selection (language, database, API style), task estimation with hour budgets, refactoring decision rules, code review patterns, architecture decisions, performance profiling, debugging strategies |
| `engineering-system-designer` | Capacity planning with formulas, failure analysis, scaling patterns (sharding, CQRS, consistent hashing), CAP tradeoff enforcement, system design documents |
| `engineering-backend-architect` | Distributed systems patterns, database optimization with scaling thresholds, API design, circuit breakers, data migration rules, event-driven architecture |
| `engineering-frontend-developer` | React/Vue/Svelte components, CSS debugging decision rules, SSR/Server Components patterns, build tooling selection, performance debugging workflow, WCAG accessibility |
| `engineering-mobile-app-builder` | SwiftUI, Jetpack Compose, React Native, Flutter, platform-specific gotchas (iOS background limits, Android Doze), offline sync strategies, push notifications, biometric auth |
| `engineering-ml-engineer` | PyTorch, HuggingFace Transformers, LoRA/QLoRA fine-tuning, RAG pipelines, scikit-learn, XGBoost, training strategy by data size, GPU memory tiers, model deployment |
| `engineering-devops-automator` | Docker, Kubernetes, Terraform, CI/CD pipelines, cost estimation with dollar amounts, service selection decision trees, monitoring, secrets management |
| `engineering-rapid-prototyper` | Next.js/Supabase/Prisma full-stack, shadcn/ui, tRPC, kill criteria, scope limits, hour-by-hour workflow, rapid MVP scaffolding |
| `engineering-security-engineer` | STRIDE/DREAD threat modeling, OWASP Top 10 with test payloads, secrets management, supply chain security, API security, compliance (SOC 2, GDPR, HIPAA) |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) or [Codex](https://openai.com/index/introducing-codex/) CLI
- [skills CLI](https://www.npmjs.com/package/skills) (`npx skills` — no install needed)
- Python 3.8+ (for Python scripts)
- Bash (for shell scripts)
