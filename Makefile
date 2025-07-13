.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[1m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: check
check: ## Run the test suite
	@PY=`python --version | sed 's/.*\.\([0-9]*\)\..*/py3\1/'`; \
		echo TOXENV=$$PY tox; \
		TOXENV=$$PY tox

.PHONY: lint
lint: ## Check the source code
	pre-commit run -a

.PHONY: clean
clean: ## Clean generated files
	-rm -rf dist qtile.egg-info docs/_build build/ .tox/ .mypy_cache/ .pytest_cache/ .eggs/

.PHONY: run-ffibuild
run-ffibuild: ## Build FFI modules
	./scripts/ffibuild -v

.PHONY: update-flake
update-flake: ## Update the Nix flake.lock file, requires Nix installed with flake support, see: https://nixos.wiki/wiki/Flakes
	nix flake update

