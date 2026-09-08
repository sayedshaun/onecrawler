# AGENTS.md

Instructions for AI coding agents working in this repository.

## Code

Keep it simple, readable, and modular.

- Make the smallest change that solves the problem, in the style of the code around it. Do not touch what you were not asked to.
- Explicit beats clever. If a reader has to decode it, rewrite it.
- No abstraction for a case that does not exist yet. Add indirection when the second caller arrives.
- One responsibility per module; a new concern gets a new module, not another branch in an old one.
- Short, single-purpose functions. Return early instead of nesting. If a comment explains the second half, that half is a function.
- Name things for what they are, and never duplicate logic.
- Type-hint public functions, following the style already in the file.
- Google-style docstrings, wrapped at 88 by docformatter. Say why, not what.
- Comment only the surprising.
- Log through the logging module, never print. A swallowed exception is still logged.
- Raise meaningful errors, catch only what you expect, and never let a failure end as an empty result.
- Prefer the standard library; a new dependency needs justification.

## Commits

- Conventional Commits: a type, an optional scope, a short description. Types in use are feat, fix, docs, style, refactor, perf, test, and chore.
- One line, imperative, no trailing period, no body unless asked.
- Never add co-author trailers, "generated with" lines, or any other AI attribution.
- One logical change per commit; tests with that change or in a test commit right after.
- Run the pre-commit hooks first — two of them rewrite files, and reformatting afterwards costs a fixup commit.

## Pull Requests

Branch off main and target main. Make sure the suite passes, across every supported Python version when the change touches crawling behaviour. Describe the defect and its cause, not the diff.

## Commands

Every task is a Makefile target; run make with no arguments to list them.
