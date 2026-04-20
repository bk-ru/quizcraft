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
- For text-processing, API, storage, and generation features, include at least one Russian/Cyrillic example.
- Do not finish the task without running relevant tests.
- If tests cannot be run, explain exactly why.

## Delivery report
- At the end of each implementation batch or stage, provide:
  1. summary of changes
  2. touched files
  3. tests/checks run
  4. review result
  5. safe to merge or not
  6. integration action taken or deferred
  7. commit hashes
  8. commit messages

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

  ## Russian language requirement
- All user-facing document processing in this project must work correctly with Russian-language content and Cyrillic text.
- Uploaded documents should be tested primarily on Russian/Cyrillic fixtures.
- Quiz generation, validation, storage, API responses, and UI rendering must preserve Cyrillic text without corruption or lossy normalization.
- New parsing, generation, export, and API features must include tests with Russian-language examples.
- Do not assume ASCII-only or English-only inputs anywhere in the pipeline.

## Cyrillic test coverage
- For every feature that reads, transforms, stores, returns, or displays document content, include at least one positive test with Cyrillic/Russian text.
- For parsers and API flows, verify UTF-8 handling and round-trip preservation of Cyrillic text.
- For generation-related flows, verify that resulting quiz fields remain in Russian when the source document is in Russian.

## Cyrillic compatibility policy
- Broad refactoring for Russian/Cyrillic support is not required unless a concrete defect is found.
- Treat Cyrillic compatibility as test-proven, not assumption-based.
- If a Russian/Cyrillic test passes for an existing flow, do not refactor that flow just for precaution.
- If a Russian/Cyrillic test fails, apply the smallest targeted fix and add regression coverage.

## Text integrity policy
- Preserve Russian/Cyrillic text across request -> parsing -> storage -> generation -> response without corruption.
- Prefer targeted fixes over broad i18n refactors.
- Do not introduce English fallback text into Russian-language flows unless explicitly required.