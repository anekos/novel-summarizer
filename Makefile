.PHONY: test
test:
	uv run pre-commit run --all-files
