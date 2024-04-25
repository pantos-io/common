.PHONY: code
code: check format lint sort bandit test

.PHONY: check
check:
	mypy pantos/common

.PHONY: test
test:
	python3 -m pytest tests

.PHONY: coverage
coverage:
	python3 -m pytest --cov-report term-missing --cov=pantos tests
	rm .coverage

.PHONY: lint
lint:
	flake8 pantos/common tests

.PHONY: sort
sort:
	isort --force-single-line-imports pantos/common tests

.PHONY: bandit
bandit:
	bandit -r pantos/common tests --quiet --configfile=.bandit

.PHONY: format
format:
	yapf --in-place --recursive pantos/common tests

.PHONY: clean
clean:
	rm -r -f build/
	rm -r -f dist/
	rm -r -f pantos_common.egg-info/
