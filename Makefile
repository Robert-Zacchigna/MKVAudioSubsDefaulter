.PHONY: help
help:  ## Display this help message
	@echo "Usage: make [command]"
	@echo ""
	@echo "Available Commands:"
	@echo ""
	@awk -F '##' '/^[a-zA-Z_-]+:.*?##/ { name=substr($$1, 1, length($$1)-3); printf "\033[36m  %-9s\033[0m %s\n", name, $$2 }' $(MAKEFILE_LIST)

init:  ## Install project dependencies using uv
	@uv sync --no-dev
devel:  ## Set up development environment with dependencies and pre-commit hooks
	@uv sync --extra dev
	@pre-commit install --hook-type commit-msg --hook-type pre-commit --hook-type pre-push --install-hooks -t post-checkout -t post-merge
lock:  ## Generate/update Uv lock file
	@uv sync
test:  ## Run tests with coverage reporting (minimum 80% coverage required)
	@pytest --cov-config=.coveragerc --cov-branch --cov=MKVAudioSubsDefaulter --cov-fail-under 80 --cov-report term-missing --cov-report xml tests/
analysis:  ## Run code quality checks (lint, format, import optimization, etc...)
	@pre-commit run --all-files
update:  ## Update all dependencies to their latest versions and regenerate lock file
	@uv sync --upgrade
outdated:  ## Check for outdated dependencies
	@pip list --outdated
