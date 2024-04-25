PYTHON_FILES := pantos/common scripts tests ./*.py

.PHONY: code
code: check format lint sort bandit test

.PHONY: check
check:
	mypy $(PYTHON_FILES)

.PHONY: test
test:
	python3 -m pytest tests

.PHONY: coverage
coverage:
	rm -rf .coverage
	python3 -m pytest --cov-report term-missing --cov=pantos tests

.PHONY: lint
lint:
	flake8 $(PYTHON_FILES)

.PHONY: sort
sort:
	isort --force-single-line-imports $(PYTHON_FILES)

.PHONY: sort-check
sort-check:
	isort --force-single-line-imports $(PYTHON_FILES) --check-only

.PHONY: bandit
bandit:
	bandit -r $(PYTHON_FILES) --quiet --configfile=.bandit

.PHONY: bandit-check
bandit-check:
	bandit -r $(PYTHON_FILES) --configfile=.bandit

.PHONY: format
format:
	yapf --in-place --recursive $(PYTHON_FILES)

.PHONY: format-check
format-check:
	yapf --diff --recursive $(PYTHON_FILES)

.PHONY: clean
clean:
	rm -r -f build/
	rm -r -f dist/
	rm -r -f pantos_common.egg-info/
