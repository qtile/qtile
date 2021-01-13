.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[1m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: check
check: ## Run the test suite
	nox -s test

.PHONY: lint
lint: ## Check the source code
	nox -s format lint

.PHONY: clean
clean: ## Clean generated files
	-rm -rf dist qtile.egg-info docs/_build build/ .tox/ .mypy_cache/ .pytest_cache/ .eggs/

# This is a little ugly: we want to be able to have users just run
# 'python setup.py install' to install qtile, but we would also like to install
# the man pages. I can't figure out a way to have the 'build' target invoke the
# 'build_sphinx' target as well, so we commit the man pages, since they are
# used in the 'install' target.
.PHONY: man
man: ## Generate Sphinx documentation
	python3 setup.py build_sphinx -b man
	cp build/sphinx/man/* resources/

.PHONY: run-ffibuild
run-ffibuild: ## Build FFI modules
	./scripts/ffibuild
