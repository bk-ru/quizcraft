# Repository Structure Cleanup

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

After this change, a newcomer can find agent instructions, planning documents, execution plans, and UI mockups without scanning the repository root. The repository will expose a stable top-level layout: root files only for repository entry points, `.agent/` for agent workflow rules, `docs/` for planning and design artifacts, and `tests/` for structure verification. You can see the change working by listing the repository tree, opening `docs/design/concepts/v2/01-homepage.html`, and running the repository-layout pytest checks.

## Progress

- [x] (2026-04-17 15:30:12Z) Reviewed the repository root, tracked files, and recent commits to identify the minimal scope of the cleanup.
- [x] (2026-04-17 15:31:10Z) Moved `PLANS.md` to `.agent/PLANS.md`, `backlog.md` to `docs/planning/backlog.md`, and `design-concepts-v2/` to `docs/design/concepts/v2/`.
- [x] (2026-04-17 15:31:40Z) Rewrote the root `README.md` so it reflects the new navigation model.
- [x] (2026-04-17 15:31:58Z) Added pytest coverage for the expected repository layout and moved HTML concepts.
- [x] (2026-04-17 15:32:20Z) Investigated the initial test failure, identified the wrong assumption in the test, and updated the validation logic for standalone mockups.
- [x] (2026-04-17 15:32:35Z) Ran validation commands and updated this plan with the final results.

## Surprises & Discoveries

- Observation: The repository instructions and the actual file layout were already out of sync because the user-facing guidance refers to `.agent/PLANS.md` while the file existed as `PLANS.md` in the repository root.
  Evidence: The initial repository listing showed `PLANS.md` at `D:\github\diplom\PLANS.md` and no `.agent` directory.

- Observation: The repository currently contains only documentation and static HTML prototypes, so the safest cleanup is structural rather than code-centric.
  Evidence: `git ls-files` returned `AGENTS.md`, `README.md`, `backlog.md`, and five HTML mockups under `design-concepts-v2/`.

- Observation: `04-mobile.html` is a standalone mockup and intentionally does not link to any sibling HTML screens.
  Evidence: A link-scan over `docs/design/concepts/v2/*.html` returned an empty reference list only for `04-mobile.html`, while the other concept files referenced sibling pages.

## Decision Log

- Decision: Keep `AGENTS.md`, `README.md`, and `LICENSE` in the repository root and move only planning and design artifacts.
  Rationale: These three files are standard repository entry points and moving them would reduce discoverability rather than improve it.
  Date/Author: 2026-04-17 / Codex

- Decision: Move `PLANS.md` into `.agent/PLANS.md`.
  Rationale: The user instruction already points future work to `.agent/PLANS.md`, so aligning the filesystem with that expectation removes ambiguity for both humans and agents.
  Date/Author: 2026-04-17 / Codex

- Decision: Move `backlog.md` into `docs/planning/backlog.md` and the mockups into `docs/design/concepts/v2/`.
  Rationale: Both sets of files are documentation artifacts, but they serve different navigation goals, so separating planning from design keeps the structure explicit.
  Date/Author: 2026-04-17 / Codex

- Decision: Add a repository-layout pytest instead of relying only on manual inspection.
  Rationale: The repository instructions require tests for behavior changes, and the layout change is observable through file locations and HTML link targets.
  Date/Author: 2026-04-17 / Codex

## Outcomes & Retrospective

The repository now has a predictable top-level structure: repository entry points remain at the root, agent workflow instructions live under `.agent/`, and planning plus design artifacts live under `docs/`. The added pytest module proves both the canonical file locations and the integrity of the HTML cross-links that still exist after the move.

The only adjustment during execution was to relax an overly strict validation rule. The first version of the test incorrectly assumed every mockup had at least one HTML link, but the mobile concept is intentionally standalone. Fixing the test kept the cleanup minimal and avoided unnecessary changes to the design files themselves.

## Context and Orientation

The repository root initially held almost every project artifact. `AGENTS.md` contains repository-specific instructions for coding agents and must remain at the root so agent tooling can discover it immediately. `PLANS.md` defines the ExecPlan format for complex work but did not live in the `.agent/` path referenced by the user's workflow instructions. `backlog.md` contains the product backlog and MVP decomposition for the QuizCraft project. `design-concepts-v2/` contains five static HTML mockups that describe the current UI concept set. Those HTML files reference each other with relative links such as `01-homepage.html` and `05-export-page.html`, which means they remain valid as long as the files stay together inside one directory.

In this repository, an ExecPlan is a self-contained task plan that explains what to change, how to validate it, and how to recover if something goes wrong. This plan focuses only on repository organization. It does not introduce application code, new dependencies, or unrelated documentation.

## Plan of Work

First, create the target directories `.agent/`, `docs/execplans/`, `docs/planning/`, `docs/design/concepts/v2/`, and `tests/`. Move `PLANS.md` into `.agent/PLANS.md` so future agent instructions point to a real path. Move `backlog.md` into `docs/planning/backlog.md` so planning artifacts no longer occupy the repository root. Move the full `design-concepts-v2/` directory into `docs/design/concepts/v2/` as one unit so the HTML files keep their relative links.

Next, rewrite `README.md` so it explains the new repository layout and tells a newcomer where to find plans, backlog items, and mockups. Do not add implementation claims because the repository does not yet contain the application source code.

Then add `tests/test_repository_layout.py`. The test module must assert that the new canonical paths exist, that the legacy root-level paths no longer exist, and that every relative `.html` reference inside the moved design files resolves to a real file in `docs/design/concepts/v2/`.

Finally, run the validation commands from the repository root, record the results in this ExecPlan, and keep the plan synchronized with the final filesystem layout.

## Concrete Steps

From `D:\github\diplom`, create the directories:

    powershell -Command "New-Item -ItemType Directory -Force .agent, docs, docs/execplans, docs/planning, docs/design/concepts/v2, tests | Out-Null"

Move the repository-level planning documents:

    powershell -Command "Move-Item -LiteralPath PLANS.md -Destination .agent/PLANS.md"
    powershell -Command "Move-Item -LiteralPath backlog.md -Destination docs/planning/backlog.md"

Move the mockup directory without splitting the files:

    powershell -Command "Move-Item -LiteralPath design-concepts-v2 -Destination docs/design/concepts/v2"

Rewrite the root README and add the pytest module so both describe the new canonical structure.

Run validation from `D:\github\diplom`:

    python -m pytest tests/test_repository_layout.py -q

Observed result:

    ..                                                                    [100%]
    2 passed in 0.01s

Inspect the final layout:

    git status --short

Observed result before staging:

     M README.md
    R  backlog.md -> docs/planning/backlog.md
    R  design-concepts-v2/01-homepage.html -> docs/design/concepts/v2/01-homepage.html
    R  design-concepts-v2/02-quiz-editor.html -> docs/design/concepts/v2/02-quiz-editor.html
    R  design-concepts-v2/03-status-page.html -> docs/design/concepts/v2/03-status-page.html
    R  design-concepts-v2/04-mobile.html -> docs/design/concepts/v2/04-mobile.html
    R  design-concepts-v2/05-export-page.html -> docs/design/concepts/v2/05-export-page.html
    ?? .agent/
    ?? docs/execplans/
    ?? tests/

## Validation and Acceptance

Acceptance is satisfied when all of the following are true. Listing the repository root shows only repository entry points and top-level containers, not raw planning artifacts. `python -m pytest tests/test_repository_layout.py -q` passes. Opening `docs/design/concepts/v2/01-homepage.html` in a browser still allows navigation to the linked concept screens because the HTML files remained together. `AGENTS.md` stays at the root, and `.agent/PLANS.md` exists at the path described by the user's workflow instructions.

## Idempotence and Recovery

The cleanup is safe to repeat as long as each move checks the current path before executing. If a move partially succeeds, inspect `git status --short` and move only the remaining unmoved files. Because this task rearranges documentation rather than generated artifacts or database state, rollback is straightforward: move the files back to their original paths with the inverse `Move-Item` commands. Do not delete files during recovery; move them so the history stays inspectable.

## Artifacts and Notes

Important repository files after the cleanup:

    D:\github\diplom\AGENTS.md
    D:\github\diplom\.agent\PLANS.md
    D:\github\diplom\docs\planning\backlog.md
    D:\github\diplom\docs\design\concepts\v2\01-homepage.html
    D:\github\diplom\docs\execplans\2026-04-17-repository-structure-cleanup.md

Important validation command:

    python -m pytest tests/test_repository_layout.py -q

## Interfaces and Dependencies

This task depends only on the existing Git repository, PowerShell file operations, Python's standard library, and pytest for validation. No production dependencies are required. At the end of the task, the following filesystem interfaces must exist:

    .agent/PLANS.md
    docs/planning/backlog.md
    docs/design/concepts/v2/01-homepage.html
    docs/design/concepts/v2/02-quiz-editor.html
    docs/design/concepts/v2/03-status-page.html
    docs/design/concepts/v2/04-mobile.html
    docs/design/concepts/v2/05-export-page.html
    docs/execplans/2026-04-17-repository-structure-cleanup.md
    tests/test_repository_layout.py

Revision note: Updated the ExecPlan after implementation to record the final directory moves, the standalone nature of `04-mobile.html`, and the passing pytest verification.
