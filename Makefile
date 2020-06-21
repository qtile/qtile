default:
	@echo "'make check'" for tests
	@echo "'make check-cov'" for tests with coverage
	@echo "'make lint'" for source code checks
	@echo "'make ckpatch'" to check a patch
	@echo "'make clean'" to clean generated files
	@echo "'make man'" to generate sphinx documentation
	@echo "'make run-ffibuild'" to build ffi modules

.PHONY: check
check:
	TOXENV=py38 tox

.PHONY: lint
lint:
	TOXENV=format,pep8 tox

.PHONY: clean
clean:
	-rm -rf dist qtile.egg-info docs/_build build/ .tox/ .mypy_cache/ .pytest_cache/ .eggs/

# This is a little ugly: we want to be able to have users just run
# 'python setup.py install' to install qtile, but we would also like to install
# the man pages. I can't figure out a way to have the 'build' target invoke the
# 'build_sphinx' target as well, so we commit the man pages, since they are
# used in the 'install' target.
.PHONY: man
man:
	python3 setup.py build_sphinx -b man
	cp build/sphinx/man/* resources/

.PHONY: run-ffibuild
run-ffibuild:
	./scripts/ffibuild
