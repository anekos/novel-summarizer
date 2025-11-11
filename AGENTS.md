# Repository Guidelines

## Project Structure & Module Organization
Core code lives under `src/novel_summarizer`, with CLI entrypoints in `__init__.py`, prompt templates in `prompts.py`, pagination helpers in `pager.py`, and Markdown I/O in `markdown_writer.py`. Domain models live in `types.py`, and orchestration flows through `summarizer/`. Project metadata (`pyproject.toml`, `uv.lock`) plus the launcher (`./novel-summarizer`) stay at the repo root. Add tests under `tests/`, mirroring modules (e.g., `tests/chunker/test_chunked.py`).

## Build, Test, and Development Commands
Use `uv run novel-summarizer summarize manuscript.txt '^Chapter \d+' --dest summaries` to exercise the CLI; the wrapper script `./novel-summarizer …` does the same with pinned dependencies. Before opening a PR, run `make test`, which fans out to linting, formatting, type-checking, and pytest so every quality check stays in sync with the root Makefile.

## Coding Style & Naming Conventions
Follow standard Python style: 4-space indentation, `snake_case` functions, `PascalCase` classes, and exhaustive type hints (mypy runs with `disallow_untyped_defs=true`). Keep modules cohesive—each should expose a minimal public API via `__all__` or explicit re-exports in `__init__.py`. Prefer pure functions in helpers like `chunker` and reserve stateful logic for orchestrators. Let Ruff handle import sorting and linting; if it flags problems, rely on the fixes surfaced when `make test` runs.

## Testing Guidelines
Write pytest tests that mirror module names (`tests/markdown_writer/test_render.py`) and use descriptive test names (`test_chunker_handles_overlap`). Target ≥85 % coverage on new logic by covering both happy paths and edge cases (e.g., page overlaps, empty chunks). Run the full suite with `make test` before pushing; it wraps `uv run pytest` with the repo’s pinned dependencies.

## Commit & Pull Request Guidelines
Existing history favors short, imperative commit titles (“Add a command”, “Refine AI inputs”); continue that style and keep body text optional but informative. Each PR should describe the problem, the solution, and validation steps, linking issues when available. Attach CLI output snippets or screenshots for user-facing changes, and mention any follow-up tasks explicitly. Request review only after passing lint, type-check, and test commands, and ensure CI badges (if configured) are green.

## Security & Configuration Tips
Never hard-code API keys; the OpenAI client reads `OPENAI_API_KEY`, so load it via your shell profile or a local `.env` that is gitignored. When sharing logs, redact manuscript text and prompt payloads. If you add new configuration files, document the required environment variables in the README and keep sample defaults minimal to avoid leaking sensitive settings.
