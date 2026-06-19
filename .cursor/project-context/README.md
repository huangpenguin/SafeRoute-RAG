# Project Context

This directory stores stable project-specific notes for agents.

Use this directory for architecture, plans, and decisions. Recommended files:

- `overview.md`: project goal, stack, and main workflow.
- `current-plan.md`: active task, constraints, and next steps.
- `decisions.md`: stable project decisions and architecture choices.
- `docs-language.md` (optional): documentation language preferences, e.g. enable Chinese-native Python docstrings/comments.

Do not put bug postmortems here. Store reusable debugging lessons in `.cursor/lessons-learned/`.

Example snippet for `docs-language.md` or `overview.md`:

```markdown
- Python docstrings/comments: Simplified Chinese (enable `bilingual-comments.mdc`)
```

Do not store secrets, credentials, long transcripts, or private tokens here.
