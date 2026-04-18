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

## Batch integration policy
- Do not start the next batch until the current batch is reviewed, integrated into main, and main is in a known clean or explicitly acknowledged state.
- Keep integration separate from implementation.

## Planning artifacts
- For multi-step work, create or update an ExecPlan before large implementation changes.
- If an ExecPlan changes delivery sequencing or stage status, commit that plan separately from feature work.
- Do not mark a stage complete until implementation, tests, review, and integration are all finished.

## Batch execution policy
- For each stage, break work into small reviewable batches before implementation.
- Implement only one batch at a time unless explicitly told otherwise.
- Keep each batch limited to one coherent slice of functionality.
- Do not mix unrelated architectural layers in the same batch.

## Review output
- Every completed batch or stage must include a review result against the base branch.
- The review report must explicitly state:
  - critical issues,
  - medium issues,
  - minor issues,
  - safe to merge or not.

## Integration policy
- Keep implementation commits separate from integration commits.
- If using a worktree branch, integrate only after tests and review are green.
- Prefer merge when the whole branch is valid as a unit.
- Use cherry-pick only when excluding specific commits is intentional and documented.

## Working tree safety
- Before starting a new batch or stage, report whether the target branch working tree is clean.
- If it is not clean, explicitly state whether that blocks safe implementation or integration.
- Do not silently proceed across unrelated local modifications.

## Standard delivery report
- At the end of each implementation batch or stage, provide:
  1. summary of changes,
  2. list of touched files,
  3. tests/checks run,
  4. review result,
  5. safe to merge or not,
  6. integration action taken or deferred,
  7. commit hashes,
  8. commit messages.