default:
	@echo "'make check'" for tests
	@echo "'make lint'" for source code checks
	@echo "'make ckpatch'" to check a patch
	@echo "'make clean'" to clean generated files
	@echo "'make deb'" to generate debian package

.PHONY: check
check:
	nosetests -v -d

.PHONY: lint
lint:
	flake8 --config=./test/flake8.cfg ./libqtile bin/qtile* bin/qsh

.PHONY: ckpatch
ckpatch: lint check

.PHONY: clean
clean:
	-rm -rf dist qtile.egg-info docs/_build

# strip off the leading 'v'
VERSION=$(shell git describe --tags | cut -c 2-)

.PHONY: deb
deb:
	@echo building package for $(VERSION)
	git archive -o ../qtile_$VERSION.orig.tar.gz v$(VERSION)
	git buildpackage -S # -sd disables uploading of orig.tar.gz
