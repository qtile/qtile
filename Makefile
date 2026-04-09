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

# Detect if we're in a Nix environment
ifdef NIX_BUILD_CORES
PYTHON_CMD = python3
else
PYTHON_CMD = uv run $(UV_PYTHON_ARG) python3
endif

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[1m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: deps
deps: ## Install all of qtile's dependencies.
ifndef NIX_BUILD_CORES
	uv sync $(UV_PYTHON_ARG) --all-extras
else
	@echo "Running in Nix environment, dependencies managed by Nix"
endif

.PHONY: check
check: deps ## Run the test suite on the latest python
ifdef NIX_BUILD_CORES
	python3 ./libqtile/backend/wayland/cffi/build.py
	$(TEST_RUNNER) $(PYTEST_BACKEND_ARG)
else
	uv run ./libqtile/backend/wayland/cffi/build.py
	uv run $(UV_PYTHON_ARG) $(TEST_RUNNER) $(PYTEST_BACKEND_ARG)
endif

.PHONY: docs
docs: deps ## Run the sphinx build for the html docs.
ifdef NIX_BUILD_CORES
	$(MAKE) -C docs html
else
	uv run $(MAKE) -C docs html
endif

.PHONY: check-packaging
check-packaging:  ## Check that the packaging is sane
ifdef NIX_BUILD_CORES
	check-manifest
	python3 -m build --sdist .
	twine check dist/*
else
	uv run $(UV_PYTHON_ARG) check-manifest
	uv run $(UV_PYTHON_ARG) python3 -m build --sdist .
	uv run $(UV_PYTHON_ARG) twine check dist/*
endif

.PHONY: lint
lint: ## Check the source code
	pre-commit run -a

.PHONY: clean
clean: ## Clean generated files
	-rm -rf dist qtile.egg-info docs/_build build/ .mypy_cache/ .pytest_cache/ .eggs/

.PHONY: update-flake
update-flake: ## Update the Nix flake.lock file, requires Nix installed with flake support, see: https://nixos.wiki/wiki/Flakes
	nix flake update

.PHONY: build-wayland
build-wayland: ## Build wayland backend
	@python libqtile/backend/wayland/cffi/build.py

.PHONY: build-wayland-debug
build-wayland-debug: ## Build wayland backend with debug symbols
	@echo "Building wayland backend with debug symbols."
	@python libqtile/backend/wayland/cffi/build.py --debug

.PHONY: build-wayland-asan
build-wayland-asan: ## Build wayland backend with address sanitisation support.
	@echo "Building wayland backend with address sanitisation support."
	@echo "When starting qtile, you'll need to set 'LD_PRELOAD=$(gcc -print-file-name=libasan.so)' first."
	@python libqtile/backend/wayland/cffi/build.py --asan
