# Git Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/).

## Format

```
<type>(<scope>): <description>
```

## Types

| Type | When to use |
|------|-------------|
| `feat` | new skill, new reference file, new script |
| `fix` | bug fix in a skill, script, or reference |
| `docs` | readme, agents.md, or other documentation changes |
| `chore` | ci workflow, templates, repo config |
| `refactor` | restructuring without changing behavior |

## Scope

Use the skill ID as the scope when the change is skill-specific:

```
feat(engineering-ml-engineer): add rag patterns reference
fix(engineering-frontend-developer): correct react hook dependency
docs(engineering-backend-architect): clarify rate limiting example
```

For repo-wide changes, omit the scope:

```
docs: update readme install instructions
chore: add pr template
```

## Rules

- Use imperative mood: "add feature" not "added feature"
- Entire message must be lowercase (no capital letters)
- No period at the end
- Keep the first line under 72 characters
- Add a blank line and body for complex changes

## Examples

```
feat(engineering-ml-engineer): add fine-tuning reference with lora patterns
fix(testing-api-tester): fix endpoint discovery for openapi 3.1
docs: update readme with new skill count
chore: add issue templates for bug reports and feature requests
refactor(design-ui-designer): split token generation into separate reference
```
