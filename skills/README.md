# Universal Skills Pack

This folder contains a portable skill format generated from the repository's agent definitions.

Each skill includes:
- `SKILL.md` for Codex and Claude Code skill loaders
- `AGENT.md` as a legacy Claude-style single-file agent format
- `SYSTEM_PROMPT.md` for generic AI agents
- `manifest.json` metadata

## Structure

- `skills/<skill-id>/...`
- `skills-index.json` (at repo root)

## Generate Skills

```bash
npm run skills:build
# or
node scripts/build-skills.mjs
```

## Install Skills

```bash
npm run skills:install -- --target all
# or
node scripts/install-skills.mjs --target all
```

Install targets:
- `codex`: copies `SKILL.md` into `$CODEX_HOME/skills` (or `~/.codex/skills`)
- `claude`: copies `SKILL.md` into `$CLAUDE_HOME/skills` (or `~/.claude/skills`)
- `generic`: copies `SYSTEM_PROMPT.md` into `exports/generic-prompts`
- `all`: installs all targets above

Optional custom destination:

```bash
node scripts/install-skills.mjs --target codex --dest /absolute/path/to/skills
```

## npx Usage

If this repo is hosted on GitHub and includes this `package.json`, you can run:

```bash
npx --yes github:<owner>/<repo> agency-skills build
npx --yes github:<owner>/<repo> agency-skills install --target all
```

If published on npm:

```bash
npx --yes agency-agents-skills build
npx --yes agency-agents-skills install --target all
```
