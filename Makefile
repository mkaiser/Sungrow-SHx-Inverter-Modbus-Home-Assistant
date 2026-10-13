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
# runs all five of its own, strings last. Adding a generator means adding it
# here and in .github/workflows/validate.yml -- the two lists must agree.
GENERATORS := generate/descriptions.py generate/generate_compatibility.py

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

# The [b] is not a typo: it stops the pattern matching this recipe's own
# shell, whose command line contains the pattern itself.
stop: ## Stop a backgrounded Home Assistant and simulator
	-pkill -f '[b]in/hass'
	-pkill -f '[s]cripts/simulator.py'
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

typecheck: ## mypy --strict over the library. Part of `check` and of CI
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
	@# document that states a number, and the number went stale by 47 entities
	@# before anything compared it to the code.
	@$(PY) scripts/helpers/review_names.py --check
.PHONY: gen-check

version-check: ## Verify pyproject.toml and manifest.json agree
	$(PY) scripts/release/sync_version.py --check
.PHONY: version-check

##@ Scan

scan: ## Survey an installation and write a document (HOST=a.b.c.d optional)
	$(PY) scripts/sungrow_read_only_survey/sungrow_survey.py $(HOST) $(ARGS)
.PHONY: scan

probe: ## Probe for devices, e.g. make probe ARGS="sweep 192.168.178.0/24"
	$(PY) scripts/sungrow_read_only_survey/probe.py $(ARGS)
.PHONY: probe

blocks: ## The block read test -- which read inside a component fails, and why
	$(PY) scripts/sungrow_read_only_survey/blocks.py $(ARGS)
.PHONY: blocks

scan-sim: ## Run the whole survey against the simulator -- needs `make sim-bg`
	$(PY) scripts/sungrow_read_only_survey/sungrow_survey.py 127.0.0.1 --port 5020 $(ARGS)
.PHONY: scan-sim

##@ Control test (writes to the inverter)

controltest-dry: ## Show what the control test would write, and write nothing (HOST=a.b.c.d)
	$(PY) scripts/sungrow_control_test/sungrow_control_test.py $(HOST) --dry-run $(ARGS)
.PHONY: controltest-dry

controltest: ## Write each control, read it back, and put it back (HOST=a.b.c.d)
	$(PY) scripts/sungrow_control_test/sungrow_control_test.py $(HOST) $(ARGS)
.PHONY: controltest

controltest-sim: ## Run it against the simulator -- needs `make sim-bg`
	$(PY) scripts/sungrow_control_test/sungrow_control_test.py 127.0.0.1 --port 5020 --simulated --no-restart
.PHONY: controltest-sim

controltest-restore: ## Put a saved snapshot back (HOST=a.b.c.d FILE=scripts/sungrow_control_test/<stamp>-snapshot.json)
	$(PY) scripts/sungrow_control_test/sungrow_control_test.py $(HOST) --restore $(FILE)
.PHONY: controltest-restore

##@ Release

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
