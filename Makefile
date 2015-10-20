default:
	@echo "'make check'" for tests
	@echo "'make check-cov'" for tests with coverage
	@echo "'make lint'" for source code checks
	@echo "'make ckpatch'" to check a patch
	@echo "'make clean'" to clean generated files
	@echo "'make man'" to generate sphinx documentation
	@echo "'make update-requirements'" to update the requirements files
	@echo "'make isort'" sorts imports in *.py files

.PHONY: check
check:
	pytest --verbose

.PHONY: check-cov
check-cov:
	pytest --verbose --with-cov libqtile --cov-report term-missing

.PHONY: lint
lint:
	flake8 ./libqtile bin/q*

.PHONY: ckpatch
ckpatch: lint check

.PHONY: clean
clean:
	-rm -rf dist qtile.egg-info docs/_build build/

# This is a little ugly: we want to be able to have users just run
# 'python setup.py install' to install qtile, but we would also like to install
# the man pages. I can't figure out a way to have the 'build' target invoke the
# 'build_sphinx' target as well, so we commit the man pages, since they are
# used in the 'install' target.
.PHONY: man
man:
	python setup.py build_sphinx -b man
	cp build/sphinx/man/* resources/

.PHONY: update-requirements
update-requirements:
	pip-compile requirements.in

.PHONY: isort
isort:
	isort -rc .
