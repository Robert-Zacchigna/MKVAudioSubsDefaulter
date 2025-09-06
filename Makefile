.PHONY: help
help:  ## Display this help message
	@echo "Usage: make [command]"
	@echo ""
	@echo "Available Commands:"
	@echo ""
	@awk -F '##' '/^[a-zA-Z_-]+:.*?##/ { name=substr($$1, 1, length($$1)-3); printf "\033[36m  %-9s\033[0m %s\n", name, $$2 }' $(MAKEFILE_LIST)

init:  ## Install project dependencies using Poetry
	@poetry install
devel:  ## Set up development environment with dependencies and pre-commit hooks
	@make init
	@poetry install --only dev
	@pre-commit install --hook-type pre-commit --hook-type pre-push --install-hooks -t post-checkout -t post-merge
lock:  ## Generate/update Poetry lock file
	@poetry lock
test:  ## Run tests with coverage reporting (minimum 80% coverage required)
	@pytest --cov-config=.coveragerc --cov-branch --cov=MKVAudioSubsDefaulter --cov-fail-under 80 --cov-report term-missing --cov-report xml tests/
analysis:  ## Run code quality checks (lint, format, import optimization, etc...)
	@poetry run pre-commit run --all-files
update:  ## Check and update all project dependencies to their latest versions
	@echo "[*] Checking Updated Packages [*]"
	@echo ""
	@found_updates=0; \
	echo "[~] Checking 'main' Dependencies [~]"; \
	updates_main=$$(poetry show --outdated --without dev | awk '{ printf("%s@%s ", $$1, $$3) }'); \
	if [ ! -z "$$updates_main" ]; then \
		echo ""; \
		echo "Updating 'main' packages: $$updates_main"; \
  		poetry add $$updates_main; \
  		found_updates=1; \
	fi; \
	echo "[~] Checking 'dev' Dependencies [~]"; \
	updates_dev=$$(poetry show --outdated --with dev | awk '{ printf("%s@%s ", $$1, $$3) }'); \
	if [ ! -z "$$updates_dev" ]; then \
		echo ""; \
		echo "Updating 'dev' packages: $$updates_dev"; \
		poetry add --group dev $$updates_dev; \
  		found_updates=1; \
	fi; \
	if [ $$found_updates -eq 0 ]; then \
	  	echo ""; \
		echo "[*] No Updates Required [*]"; \
	fi
