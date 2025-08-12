.DEFAULT_GOAL := help

ifeq ($(QTILE_CI_PYTHON),)
UV_PYTHON_ARG =
else
UV_PYTHON_ARG = --python=$(QTILE_CI_PYTHON)
endif

ifeq ($(QTILE_CI_BACKEND),)
PYTEST_BACKEND_ARG =
else
PYTEST_BACKEND_ARG = --backend=$(QTILE_CI_BACKEND)
endif

TEST_RUNNER = python3 -m pytest
ifeq ($(GITHUB_ACTIONS),true)
TEST_RUNNER = coverage run -m pytest
endif

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[1m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: check
check: ## Run the test suite on the latest python
	uv sync $(UV_PYTHON_ARG) --all-extras
	uv run ./libqtile/backend/wayland/cffi/build.py
	uv run $(UV_PYTHON_ARG) $(TEST_RUNNER) $(PYTEST_BACKEND_ARG)

.PHONY: check-packaging
check-packaging:  ## Check that the packaging is sane
	uv run $(UV_PYTHON_ARG) check-manifest
	uv run $(UV_PYTHON_ARG) python3 -m build --sdist .
	uv run $(UV_PYTHON_ARG) twine check dist/*

.PHONY: lint
lint: ## Check the source code
	pre-commit run -a

.PHONY: clean
clean: ## Clean generated files
	-rm -rf dist qtile.egg-info docs/_build build/ .mypy_cache/ .pytest_cache/ .eggs/

.PHONY: update-flake
update-flake: ## Update the Nix flake.lock file, requires Nix installed with flake support, see: https://nixos.wiki/wiki/Flakes
	nix flake update

