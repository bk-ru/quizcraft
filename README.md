# diplom

Repository for QuizCraft planning artifacts and interface concepts.

The repository currently contains product planning documents, agent workflow instructions, execution plans, and static HTML mockups. Application source code is not present yet, so the main goal of the structure is predictable navigation.

## Repository layout

- `AGENTS.md` contains repository-specific instructions for coding agents.
- `.agent/PLANS.md` defines the ExecPlan format used for complex work.
- `docs/execplans/` stores task-specific execution plans.
- `docs/planning/backlog.md` stores the product backlog and MVP decomposition.
- `docs/design/concepts/v2/` stores the second iteration of static UI concepts.
- `tests/test_repository_layout.py` verifies that planning and design artifacts stay in their expected locations.

## Working with design concepts

Open `docs/design/concepts/v2/01-homepage.html` in a browser to start from the main concept screen. The remaining HTML files in the same directory link to each other with relative paths.
