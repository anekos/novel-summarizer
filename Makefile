.PHONY: check
check:
	uv run mypy .
	uv run ruff check --fix
	uv run ruff format

.PHONY: test
test: check
	uv run pytest

.PHONY: build-info
build-info:
	printf '{"commit": "%s", "dirty": %s, "built_at": "%s"}\n' \
		"$$(git rev-parse HEAD)" \
		"$$([ -n "$$(git status --porcelain --untracked-files=no)" ] && echo true || echo false)" \
		"$$(date -Iseconds)" \
		> src/novel_summarizer/build_info.json

.PHONY: install
install: build-info
	uv tool install --force --reinstall .

.PHONY: setup
setup:
	uv sync
	uv run pre-commit install
