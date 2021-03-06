.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[1m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: check
check: ## Run the test suite
	TOXENV=py38 tox

.PHONY: lint
lint: ## Check the source code
	TOXENV=format,pep8,vulture,mypy tox

.PHONY: clean
clean: ## Clean generated files
	-rm -rf dist qtile.egg-info docs/_build build/ .tox/ .mypy_cache/ .pytest_cache/ .eggs/

.PHONY: run-ffibuild
run-ffibuild: ## Build FFI modules
	./scripts/ffibuild
