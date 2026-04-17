# Repository instructions

## Working mode
- Work only within the requested task scope.
- Before editing, inspect the relevant files and identify the minimal set of changes required.
- Do not perform unrelated refactors.
- Preserve backward compatibility unless the task explicitly allows breaking changes.

## Code quality
- Enforce security checks and explicit error handling in all touched layers.
- Prefer DRY abstractions when repetition is real and stable.
- Use OOP where it improves clarity and responsibility boundaries.
- Prefer registries and mappings over long if/elif chains.
- Do not add code comments. Only docstrings are allowed.
- Use logging, never print.
- Avoid silent fallbacks unless explicitly required.

## Tests
- Add or update pytest tests for positive and negative scenarios for every behavior change.
- Do not finish the task without running relevant tests.
- If tests cannot be run, explain exactly why.

## Dependencies
- Do not add new production dependencies unless strictly necessary.
- If a new dependency is required, explain why the standard library or existing stack is insufficient.

## Output format
- At the end, provide:
  1. summary of changes,
  2. list of touched files,
  3. tests/linters/type checks run,
  4. known limitations,
  5. suggested commit message.

## Git
- Create one commit per completed task.
- Use Conventional Commits format:
  <type>(<scope>): <short description>
- Keep commits atomic.

## Stage completion policy
- A stage is not considered complete until it is:
  1. implemented,
  2. tested,
  3. reviewed against the base branch,
  4. integrated back into the main development branch,
  5. confirmed with a clean working tree.
- Do not start the next stage before the current one is integrated.
- If using a worktree branch, explicitly report the integration method: merge or cherry-pick.

## Review gate
- No stage may be integrated until review findings are resolved or explicitly accepted.
- If review says "not safe to merge", do not start the next stage.
- Fix findings in the stage branch/worktree, rerun tests, rerun review, then integrate.