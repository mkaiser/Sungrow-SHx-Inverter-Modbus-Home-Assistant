# Shortcuts for the scripts in scripts/. The scripts remain the source of
# truth -- everything here shells out to them, nothing reimplements them.
#
#   make            the help screen
#   make check      everything CI gates on, before you push
#   make dev        Home Assistant on :8123
#   make sim        the simulator on :5020
#   make forget     forget the stored inverter, so setup re-detects it
#
# Pass extra flags through ARGS, e.g. `make test ARGS="-k migration"`.

PY      ?= python3
ARGS    ?=
HOST    ?=
VERSION ?=

# The generators CI checks, under scripts/. `descriptions.py` with no target
# runs all six of its own, strings last. Adding a generator means adding it
# here and in .github/workflows/validate.yml -- the two lists must agree.
GENERATORS := generate/descriptions.py generate/generate_compatibility.py \
              generate/generate_simulator_registers.py

.DEFAULT_GOAL := help

##@ Develop

dev: ## Boot Home Assistant on :8123 against config/ (ARGS=--forget to drop the config entry)
	scripts/dev/develop.sh $(ARGS)
.PHONY: dev

develop: dev
.PHONY: develop

sim: ## Regenerate the register seed and serve it on :5020
	scripts/dev/simulate.sh $(ARGS)
.PHONY: sim

simulate: sim
.PHONY: simulate

hacs: ## Boot a second HA on :8124 that installs this integration through HACS
	scripts/dev/hacs_testbed.sh $(ARGS)
.PHONY: hacs

forget: ## Forget the stored inverter, so the next boot re-detects it
	scripts/dev/develop.sh --forget
.PHONY: forget

dev-bg: ## Same as `dev`, in the background, logging to /tmp/ha.log
	nohup scripts/dev/develop.sh $(ARGS) > /tmp/ha.log 2>&1 &
	@echo "Home Assistant starting on :8123 -- tail -f /tmp/ha.log"
.PHONY: dev-bg

sim-bg: ## Same as `sim`, in the background, logging to /tmp/sim.log
	nohup scripts/dev/simulate.sh $(ARGS) > /tmp/sim.log 2>&1 &
	@echo "Simulator starting on :5020 -- tail -f /tmp/sim.log"
.PHONY: sim-bg

sim-ihm-bg: ## A hand-written iHomeManager (unit 247) on :5021, in the background
	nohup $(PY) scripts/dev/simulator.py --port 5021 --unit-id 247 \
		--seed scripts/dev/simulator_ihomemanager.json > /tmp/sim-ihm.log 2>&1 &
	@echo "iHomeManager simulator starting on :5021 -- tail -f /tmp/sim-ihm.log"
.PHONY: sim-ihm-bg

sim-logger-bg: ## A hand-written Logger1000 (unit 247) on :5022, in the background
	nohup $(PY) scripts/dev/simulator.py --port 5022 --unit-id 247 \
		--seed scripts/dev/simulator_logger.json > /tmp/sim-logger.log 2>&1 &
	@echo "Logger simulator starting on :5022 -- tail -f /tmp/sim-logger.log"
.PHONY: sim-logger-bg

# The [b] is not a typo: it stops the pattern matching this recipe's own
# shell, whose command line contains the pattern itself.
stop: ## Stop a backgrounded Home Assistant and simulator
	-pkill -f '[b]in/hass'
	-pkill -f '[s]cripts/dev/simulator.py'
.PHONY: stop

setup: ## Install Home Assistant, the library (editable) and the tooling
	scripts/dev/setup.sh
.PHONY: setup

refs: ## Clone HA core and the Modbus libraries into .reference/
	scripts/dev/fetch_references.sh
.PHONY: refs

##@ Check

check: version-check gen-check lint typecheck test ## Everything CI gates on, fast
.PHONY: check

ci: check build ## check, plus the package -- the full CI job
.PHONY: ci

quick: version-check gen-check lint typecheck ## `check` without the test suite, in seconds; the pre-commit hook
.PHONY: quick

hooks: ## Run `make quick` before every commit, through a git pre-commit hook
	ln -sf "$(CURDIR)/scripts/dev/pre-commit.sh" "$$(git rev-parse --git-path hooks)/pre-commit"
.PHONY: hooks

test: ## Run the test suite
	pytest -q $(ARGS)
.PHONY: test

lint: ## ruff check and ruff format --check
	ruff check .
	ruff format --check .
.PHONY: lint

fmt: ## Reformat and autofix in place
	ruff format .
	ruff check --fix .
.PHONY: fmt

typecheck: ## mypy --strict over the library and the integration. Part of `check` and of CI
	mypy
.PHONY: typecheck

gen: ## Rewrite every generated file
	@for g in $(GENERATORS); do \
	    echo "  $$g"; \
	    $(PY) scripts/$$g || exit 1; \
	done
.PHONY: gen

gen-check: ## Verify every generated file is current
	@for g in $(GENERATORS); do \
	    $(PY) scripts/$$g --check || exit 1; \
	done
	@# Not a generator, so it is not in GENERATORS -- but it writes a
	@# committed document, and only this compares that document to the code.
	@$(PY) scripts/helpers/review_names.py --check
.PHONY: gen-check

version-check: ## Verify pyproject.toml and manifest.json agree
	$(PY) scripts/release/sync_version.py --check
.PHONY: version-check

##@ Scan

scan: ## Survey an installation and write a document; asks before the control test (HOST=a.b.c.d optional)
	$(PY) device-survey/scripts/python/sungrow_survey.py $(HOST) $(ARGS)
.PHONY: scan

probe: ## Probe for devices, e.g. make probe ARGS="sweep 192.168.178.0/24"
	$(PY) device-survey/scripts/python/probe.py $(ARGS)
.PHONY: probe

blocks: ## The block read test -- which read inside a component fails, and why
	$(PY) device-survey/scripts/python/blocks.py $(ARGS)
.PHONY: blocks

scan-sim: ## Run the whole survey against the simulator -- needs `make sim-bg`
	$(PY) device-survey/scripts/python/sungrow_survey.py 127.0.0.1 --port 5020 --simulated $(ARGS)
.PHONY: scan-sim

scan-sim-ihm: ## The survey against the iHomeManager simulator -- needs `make sim-ihm-bg`
	$(PY) device-survey/scripts/python/sungrow_survey.py 127.0.0.1 --port 5021 \
		--address hidden --reporter simulator --comment '' --timeout 2 $(ARGS)
.PHONY: scan-sim-ihm

scan-sim-logger: ## The survey against the Logger simulator -- needs `make sim-logger-bg`
	$(PY) device-survey/scripts/python/sungrow_survey.py 127.0.0.1 --port 5022 \
		--address hidden --reporter simulator --comment '' --timeout 2 $(ARGS)
.PHONY: scan-sim-logger

# The launcher a contributor runs, on a library that is not released yet.
# uv builds the environment from the script's header, as for anybody, and
# SUNGROW_MODBUS_LIBRARY lays this tree's library -- or a wheel of it -- over
# the pinned one. `scan` above skips both the launcher and the header.
scan-local: ## The launcher, as a contributor runs it, on this tree's library (HOST=a.b.c.d)
	SUNGROW_MODBUS_LIBRARY=$(CURDIR) device-survey/scripts/survey.sh $(HOST) $(ARGS)
.PHONY: scan-local

scan-wheel: wheel ## The same on a freshly built wheel -- what a release would publish
	SUNGROW_MODBUS_LIBRARY=$(LIBRARY_WHEEL) device-survey/scripts/survey.sh $(HOST) $(ARGS)
.PHONY: scan-wheel

##@ Control test (writes to the inverter)

controltest-dry: ## Show what the control test would write, and write nothing (HOST=a.b.c.d)
	$(PY) device-survey/scripts/python/sungrow_control_test.py $(HOST) --dry-run $(ARGS)
.PHONY: controltest-dry

controltest: ## Write each control, read it back, and put it back (HOST=a.b.c.d)
	$(PY) device-survey/scripts/python/sungrow_control_test.py $(HOST) $(ARGS)
.PHONY: controltest

controltest-sim: ## Run it against the simulator -- needs `make sim-bg`
	$(PY) device-survey/scripts/python/sungrow_control_test.py 127.0.0.1 --port 5020 --simulated --no-restart
.PHONY: controltest-sim

controltest-local: ## The launcher on this tree's library; add ARGS=--dry-run first (HOST=a.b.c.d)
	SUNGROW_MODBUS_LIBRARY=$(CURDIR) device-survey/scripts/survey.sh control $(HOST) $(ARGS)
.PHONY: controltest-local

controltest-restore: ## Put a saved snapshot back (HOST=a.b.c.d FILE=device-survey/<stamp>-snapshot.json)
	$(PY) device-survey/scripts/python/sungrow_control_test.py $(HOST) --restore $(FILE)
.PHONY: controltest-restore

##@ Release

# The one wheel `wheel` leaves in dist/. Named by the version, so a wheel left
# behind by an older version is never picked up instead.
LIBRARY_WHEEL = $(CURDIR)/dist/sungrow_modbus-$(shell sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)-py3-none-any.whl

wheel: ## Build only the library's wheel into dist/, for SUNGROW_MODBUS_LIBRARY
	rm -f $(LIBRARY_WHEEL)
	$(PY) -m build --wheel
	@echo "SUNGROW_MODBUS_LIBRARY=$(LIBRARY_WHEEL)"
.PHONY: wheel

build: ## Build the sdist and wheel, and check them
	$(PY) -m build
	twine check --strict dist/*
	$(PY) scripts/release/check_pinned_library.py --wheel "$$(ls dist/*.whl)"
.PHONY: build

pin-check: ## Does the *published* library the manifest pins serve this integration?
	$(PY) scripts/release/check_pinned_library.py
.PHONY: pin-check

version: ## Set the version everywhere (VERSION=X.Y.Z)
	@test -n "$(VERSION)" || { echo "usage: make version VERSION=X.Y.Z"; exit 2; }
	@# --set also re-installs the editable library: Home Assistant compares the
	@# manifest pin against what is *installed*, not against pyproject.toml.
	$(PY) scripts/release/sync_version.py --set $(VERSION)
.PHONY: version

##@ Other

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make <target> [VAR=value]\n"} \
	     /^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5); next} \
	     /^[a-zA-Z0-9_-]+:.*##/ {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' \
	     $(MAKEFILE_LIST)
	@echo
.PHONY: help
