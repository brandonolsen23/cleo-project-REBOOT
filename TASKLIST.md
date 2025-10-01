# Cleo Task Checklist

This checklist defines the canonical order of operations for any contributor (human or AI) touching the Cleo repo. Always review and follow these steps before making code or documentation changes.

## 0. Read Before Doing
1. Read `Cleo App Development Plan.md` for the roadmap and phase context.
2. Review `README.md` for up-to-date setup commands and helper scripts.
3. Search for any `AGENTS.md` in the working tree; obey the most specific instructions for each file you modify.
4. Check open issues / tickets for task-specific acceptance criteria.

## 1. Local Environment Prerequisites (run in order)
1. Copy environment file: `cp .env.example .env` (edit secrets as required).
2. Verify prerequisites: `./scripts/setup/check_prerequisites.sh`.
3. Create venv and install dependencies: `./scripts/run.sh setup`.
4. Apply baseline Supabase schema (requires `DATABASE_URL`): `./scripts/run.sh db-setup`.

## 2. Working Session Guardrails
1. Confirm you are on the correct Git branch or create a feature branch.
2. Sync with `main`: `git pull --rebase origin main` before starting work.
3. Document any assumptions or manual steps in the relevant README or docs.
4. For front-end work, run the dev server on **port 3000** (reserved per team convention).

## 3. Change Implementation Flow
Follow these steps for every task; move to the next only when the current item is complete.

1. **Define scope**
   - Break down the assigned task into actionable sub-steps.
   - Note dependencies between modules (db → backend → frontend).
2. **Update schema/config (if required)**
   - Modify SQL under `config/supabase/`.
   - Run migrations and verify with `./scripts/run.sh db-health` or relevant tests.
3. **Backend/data changes**
   - Update Python modules under `common/`, `scrapers/`, or API code.
   - Add/adjust tests in `tests/` when logic changes.
4. **Frontend changes**
   - Update Next.js app under `webapp/frontend/`.
   - Ensure components use existing design patterns and shared utilities.
5. **Documentation updates**
   - Reflect changes in `docs/`, `README.md`, or inline docstrings.

## 4. Validation & QA
1. Run unit/integration tests impacted by the change (Python: `pytest`, frontend: `npm test`, etc.).
2. Execute linters/formatters (`ruff`, `black`, `eslint`, `prettier`) as applicable.
3. For DB changes, re-run sanity queries (`./scripts/run.sh db-query "SELECT COUNT(*) FROM ..."`).
4. For frontend work, capture screenshots and verify responsive behavior.
5. Ensure new environment variables or secrets are documented.

## 5. Git Hygiene & PR Process
1. Review `git status`; ensure only intentional changes are staged.
2. Craft descriptive commit messages following Conventional Commits when possible.
3. Run `git diff` for a final review before committing.
4. Push the branch and open a PR with:
   - Summary of changes.
   - Testing performed (include command output).
   - Any follow-up tasks or known issues.
5. Request review from appropriate teammates; address feedback promptly.

## 6. Post-Merge Follow-through
1. Confirm CI/CD pipelines pass after merge.
2. Deploy or release as required by the task.
3. Update task trackers (Jira/Notion/etc.) with status and links.
4. Archive logs, datasets, or assets generated during development.

> ✅ **Always revisit this TASKLIST before new work sessions to stay aligned.**
