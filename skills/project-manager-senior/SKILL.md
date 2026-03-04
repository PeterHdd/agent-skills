---
name: project-manager-senior
description: "Convert project specifications into actionable, developer-ready task breakdowns with realistic scope and measurable acceptance criteria. Use when you need spec analysis, task decomposition, dependency ordering, effort estimation, scope control, ambiguity resolution, sprint planning, or structured project execution plans with verifiable deliverables."
metadata:
  version: "1.0.0"
---

# Project Task Breakdown Guide

Convert project specifications into actionable, developer-ready task breakdowns with realistic scope, measurable acceptance criteria, and strict adherence to stated requirements.

## Process

### 1. Analyze the Specification

- Locate the canonical spec (check repo root, `docs/`, or project config).
- Quote exact requirement text when creating tasks -- do not paraphrase into something broader.
- List every ambiguity, gap, or contradiction found. Each one becomes a "Clarification Needed" item with a proposed default and a stakeholder question.
- Extract the technical stack, constraints, and integration points.

### 2. Break Down Tasks

- Group tasks by feature area, ordered by dependency (foundations first, integrations last).
- Each task gets: description, estimated hours with confidence qualifier, acceptance criteria, files affected, and spec reference.
- Estimates use three levels: "high confidence" (well-understood work), "medium confidence" (some unknowns), "low confidence" (significant unknowns requiring spike/research).
- Include a setup task (Task 0) covering project scaffolding, environment, and dev tooling.
- Every task must be completable in one focused session (2-8 hours). If a task exceeds 8 hours, split it into subtasks that each independently produce a testable result.

### 3. Write the Task Document

- Save to `tasks/<project-slug>-tasklist.md` in the repository.
- Include a specification summary at the top with quoted requirements.
- End with a quality checklist and any clarification items.

### 4. Review Against Spec

- Walk through the specification line by line and confirm every stated requirement maps to at least one task.
- Confirm no task introduces requirements not present in the specification.
- Verify the dependency ordering: no task references work from a later task.

## Decision Rules

- **Ambiguous requirement**: Document the ambiguity, state the assumed interpretation, and add a "Clarification Needed" flag. Do not block other tasks -- build against the assumption but mark it.
- **Task too large (>8 hours)**: Split into subtasks. Each subtask must independently produce a testable result.
- **Missing technical detail in spec**: Add a time-boxed spike task (max 2 hours) to investigate, with a clear deliverable (e.g., "decision document comparing options A and B").
- **Conflicting requirements**: Flag both requirements with spec references, propose a resolution, and mark as blocked until stakeholder confirmation.
- **Scope creep**: New ideas go into a separate "Future Enhancements" section, never into the task list. Scope is locked to the specification.

## Guidelines

- Extract only what the specification says. Do not invent "premium" or "luxury" features.
- Acceptance criteria must be verifiable by a developer or automated test -- no subjective language like "looks good" or "feels responsive."
- When a specification is ambiguous, list the assumptions explicitly and flag them for stakeholder review before creating dependent tasks.
- Be specific: "Implement POST /api/auth/register returning 201 with a JWT" -- not "add auth functionality."
- Quote the spec: every task references the exact spec text it fulfills.
- Stay realistic: estimates include a confidence qualifier. Do not promise certainty on unfamiliar integrations.
- A developer should read a task and start coding within 5 minutes, with no need to ask clarifying questions.

See [Task Example](references/task-example.md) for a full TaskFlow worked example with all 5 tasks.

## Reference

### Task Format

Each task should include:
- **Description**: One sentence explaining what to build
- **Estimate**: Hours + confidence qualifier (high / medium / low)
- **Acceptance Criteria**: Conditions verifiable by running a command, calling an API, or checking a UI state
- **Files**: List of files to create or modify
- **Spec Reference**: Exact quoted text from the specification

### Estimate Confidence Levels

| Level | Meaning | Action |
|-------|---------|--------|
| High confidence | Well-understood work, clear requirements | Proceed normally |
| Medium confidence | Some unknowns, library integration | Add buffer time, note risks |
| Low confidence | Significant unknowns | Add a spike task (max 2h) before the implementation task |

## Scripts

### `scripts/parse_requirements.py`
Parse a requirements document (markdown or plain text) and extract structured information including numbered requirements, user stories (As a... I want... So that...), acceptance criteria (checkboxes, Given/When/Then), and dependencies. Outputs a structured Markdown summary.

```bash
scripts/parse_requirements.py docs/spec.md
scripts/parse_requirements.py requirements.md
```

### `scripts/estimate_tasks.py`
Estimate effort for tasks based on complexity sizing. Takes a CSV or text file of tasks with complexity ratings (S/M/L/XL) and produces effort estimates with a Markdown table showing per-task estimates, total hours, complexity distribution, and recommended sprint allocation.

```bash
scripts/estimate_tasks.py tasks.csv
scripts/estimate_tasks.py backlog.txt
```
