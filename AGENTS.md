# Repository Guidelines

## Project Structure

This repository is a skills catalog for AI agent runtimes (Claude Code, Codex). Built to the [Agent Skills Spec](https://agentskills.io).

```
skills/<skill-id>/
├── SKILL.md              # Decision rules and workflow (required)
├── references/           # Deep code patterns and examples
│   └── *.md
└── scripts/              # Runnable CLI tools (Python/Bash)
    └── *.py / *.sh
```

- `skills/<skill-id>/SKILL.md`: Core skill definition with decision rules, loaded by the agent automatically.
- `skills/<skill-id>/references/`: Detailed code examples and patterns that SKILL.md links to. Agent reads on demand.
- `skills/<skill-id>/scripts/`: Standalone CLI tools the agent can run during sessions. All support `--help` and output markdown.
- `scripts/validate-skills.sh`: Validates all skills have correct frontmatter and structure.

No app runtime, package build, or test suite is included.

## Commands

```bash
# Validate all skills
./scripts/validate-skills.sh --no-skills-ref

# Install skills
npx skills add PeterHdd/agent-skills --all
npx skills add PeterHdd/agent-skills --skill engineering-frontend-developer
```

## Skill Authoring Rules

- Frontmatter in each `SKILL.md` must include:
  - `name: <skill-id>` (matches folder name)
  - `description: "when to use this skill"` (this is the trigger — agents activate the skill based on this)
  - `metadata.version: x.y.z`
- Skill folder names use lowercase kebab-case (e.g., `engineering-frontend-developer`).
- SKILL.md should contain "when X, do Y" decision rules, not persona descriptions or job listings.
- Reference files go in `references/` — SKILL.md links to them with `See [Name](references/file.md) for ...`.
- Scripts must be self-contained (stdlib only), support `--help`, and output structured markdown.
- All scripts must be executable (`chmod +x`).
- No placeholders, no stubs, no "implement here" comments in any file.

## Pre-PR Checklist

1. Every `skills/<id>/SKILL.md` has valid frontmatter (`name`, `description`, `metadata.version`).
2. Run `./scripts/validate-skills.sh --no-skills-ref` — must pass.
3. All scripts pass `--help` without errors.
4. No `[placeholder]` text anywhere: `grep -ri '\[.*placeholder\]' skills/` returns nothing.

## Git Convention

Follow the commit convention defined in [`.github/git_convention.md`](.github/git_convention.md).

When committing changes, always commit and push in one step. Use the convention for the commit message.

PRs should include what changed, which skill IDs are affected, and confirmation that `./scripts/validate-skills.sh --no-skills-ref` passed.
