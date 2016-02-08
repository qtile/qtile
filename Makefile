default:
	@echo "'make check'" for tests
	@echo "'make check-cov'" for tests with coverage
	@echo "'make lint'" for source code checks
	@echo "'make ckpatch'" to check a patch
	@echo "'make clean'" to clean generated files
	@echo "'make deb'" to generate debian package
	@echo "'make man'" to generate debian package
	@echo "'make update-requirements'" to update the requirements files

.PHONY: check
check:
	nosetests --verbose --detailed-errors

.PHONY: check-cov
check-cov:
	nosetests --verbose --detailed-errors --with-cov --cover-package libqtile

.PHONY: lint
lint:
	flake8 ./libqtile bin/qtile* bin/qsh

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

.PHONY: deb
deb:
	-rm ../qtile_*
	gbp buildpackage --git-upstream-tree=$(shell git symbolic-ref --short HEAD) --git-ignore-branch

.PHONY: update-requirements
update-requirements:
	pip-compile requirements.in
