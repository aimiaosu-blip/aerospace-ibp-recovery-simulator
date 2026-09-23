.PHONY: run test check
PYTHON ?= python3
run:
	$(PYTHON) -m aeroplan --seed 42 --output artifacts
test:
	$(PYTHON) -m unittest discover -s tests -v
check: test run
	git diff --exit-code -- artifacts
