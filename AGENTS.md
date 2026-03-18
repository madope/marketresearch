# Repository Guidelines

## Project Structure & Module Organization
This repository is currently a blank workspace, so contributors should keep the initial layout predictable. Put application code in `src/`, tests in `tests/`, research notes or design docs in `docs/`, and static inputs or sample datasets in `assets/`. Keep modules small and focused; mirror the source layout under `tests/` as the codebase grows.

Example:
```text
src/
tests/
docs/
assets/
```

## Build, Test, and Development Commands
No project-specific toolchain is committed yet. When you introduce one, document it here and in the project README. Prefer a small, stable command surface:

- `make setup` installs dependencies and local tooling
- `make test` runs the full automated test suite
- `make lint` runs formatting and static checks
- `make dev` starts the local development workflow

If you do not add `make`, provide equivalent package-manager commands such as `npm test` or `pytest`.

## Coding Style & Naming Conventions
Use 4 spaces for Python and 2 spaces for JavaScript, TypeScript, JSON, YAML, and Markdown lists. Name files and modules with lowercase `snake_case` unless the language ecosystem strongly prefers another pattern. Use descriptive names such as `market_parser.py` or `survey_loader.ts`; avoid generic files like `utils.py` unless the contents are tightly scoped. Add formatter and linter configs with the first production code change.

## Testing Guidelines
Place automated tests in `tests/` and name them after the unit under test, for example `tests/test_market_parser.py` or `tests/survey-loader.test.ts`. Cover new behavior before merging and include regression tests for bug fixes. Keep test fixtures small and store reusable sample inputs under `assets/fixtures/`.

## Commit & Pull Request Guidelines
No commit history is available locally, so follow an imperative, conventional style such as `feat: add survey import pipeline` or `docs: add contributor guide`. Keep commits focused and reviewable. Pull requests should include a short description, linked issue or task when available, test evidence, and screenshots only for user-facing changes.

## Security & Configuration Tips
Do not commit secrets, raw credentials, or private datasets. Keep local configuration in ignored files such as `.env`, and provide a checked-in `.env.example` when configuration becomes necessary.
