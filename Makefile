default:
	@echo "'make check'" for tests
	@echo "'make lint'" for source code checks
	@echo "'make ckpatch'" to check a patch
	@echo "'make clean'" to clean generated files

.PHONY: check
check:
	nosetests -v -d

.PHONY: lint
lint:
	flake8 --config=./test/flake8.cfg ./libqtile

.PHONY: ckpatch
ckpatch: lint check

.PHONY: clean
clean:
	-rm -rf dist qtile.egg-info docs/_build
