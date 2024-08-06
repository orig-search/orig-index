UV?=uv
PYTHON?=python
SOURCES=orig_index tests setup.py

.PHONY: venv
venv:
	$(UV) venv .venv
	source .venv/bin/activate && make setup
	@echo 'run `source .venv/bin/activate` to use virtualenv'

# The rest of these are intended to be run within the venv, where python points
# to whatever was used to set up the venv.

.PHONY: setup
setup:
	$(UV) pip install -Ue .[dev,test]

.PHONY: test
test:
	pytest --cov=orig_index $(TESTOPTS)

.PHONY: format
format:
	python -m ufmt format $(SOURCES)

.PHONY: lint
lint:
	python -m ufmt check $(SOURCES)
	python -m flake8 $(SOURCES)
	python -m checkdeps --allow-names orig_index orig_index
	mypy --strict --install-types --non-interactive orig_index

.PHONY: release
release:
	rm -rf dist
	python setup.py sdist bdist_wheel
	twine upload dist/*
