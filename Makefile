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

# The generated files CI checks, in dependency order: entity_map feeds
# registers, which feeds sensors and derived. Adding a generator means adding
# it here and in .github/workflows/validate.yml -- the two lists must agree.
GENERATORS := entity_map registers sensors scan_plan derived \
              numbers switches selects strings compatibility

.DEFAULT_GOAL := help

##@ Develop

dev: ## Boot Home Assistant on :8123 against config/ (ARGS=--forget to drop the config entry)
	scripts/develop.sh $(ARGS)
.PHONY: dev

develop: dev
.PHONY: develop

sim: ## Regenerate the register seed and serve it on :5020
	scripts/simulate.sh $(ARGS)
.PHONY: sim

simulate: sim
.PHONY: simulate

forget: ## Forget the stored inverter, so the next boot re-detects it
	scripts/develop.sh --forget
.PHONY: forget

dev-bg: ## Same as `dev`, in the background, logging to /tmp/ha.log
	nohup scripts/develop.sh $(ARGS) > /tmp/ha.log 2>&1 &
	@echo "Home Assistant starting on :8123 -- tail -f /tmp/ha.log"
.PHONY: dev-bg

sim-bg: ## Same as `sim`, in the background, logging to /tmp/sim.log
	nohup scripts/simulate.sh $(ARGS) > /tmp/sim.log 2>&1 &
	@echo "Simulator starting on :5020 -- tail -f /tmp/sim.log"
.PHONY: sim-bg

# The [b] is not a typo: it stops the pattern matching this recipe's own
# shell, whose command line contains the pattern itself.
stop: ## Stop a backgrounded Home Assistant and simulator
	-pkill -f '[b]in/hass'
	-pkill -f '[s]cripts/simulator.py'
.PHONY: stop

setup: ## Install Home Assistant, the library (editable) and the tooling
	scripts/setup.sh
.PHONY: setup

refs: ## Clone HA core and the Modbus libraries into .reference/
	scripts/fetch_references.sh
.PHONY: refs

##@ Check

check: version-check gen-check lint test ## Everything CI gates on, fast
.PHONY: check

ci: check zip-verify build ## check, plus the zip and the package -- the full CI job
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

typecheck: ## mypy --strict. Not part of `check`: CI has never run it
	mypy
.PHONY: typecheck

gen: ## Rewrite every generated file
	@for g in $(GENERATORS); do \
	    echo "  generate_$$g.py"; \
	    $(PY) scripts/generate_$$g.py || exit 1; \
	done
.PHONY: gen

gen-check: ## Verify every generated file is current
	@for g in $(GENERATORS); do \
	    $(PY) scripts/generate_$$g.py --check || exit 1; \
	done
.PHONY: gen-check

version-check: ## Verify pyproject.toml and manifest.json agree
	$(PY) scripts/sync_version.py --check
.PHONY: version-check

##@ Scan

scan: ## Survey an installation and write a document (HOST=a.b.c.d optional)
	$(PY) scripts/sungrow_scan/collect.py $(HOST) $(ARGS)
.PHONY: scan

probe: ## Probe for devices, e.g. make probe ARGS="sweep 192.168.178.0/24"
	$(PY) scripts/sungrow_scan/probe.py $(ARGS)
.PHONY: probe

blocks: ## The block read test -- which read inside a component fails, and why
	$(PY) scripts/sungrow_scan/blocks.py $(ARGS)
.PHONY: blocks

zip: ## Build sungrow_scan.zip
	$(PY) scripts/make_scan_zip.py
.PHONY: zip

zip-verify: ## Build it, then unpack and run it with a bare Python
	$(PY) scripts/make_scan_zip.py --verify
.PHONY: zip-verify

zip-sim: ## Run the whole survey from the zip against the simulator -- needs `make sim-bg`
	$(PY) scripts/make_scan_zip.py --verify --against 5020
.PHONY: zip-sim

##@ Release

build: ## Build the sdist and wheel, and check them
	$(PY) -m build
	twine check --strict dist/*
.PHONY: build

version: ## Set the version everywhere (VERSION=X.Y.Z)
	@test -n "$(VERSION)" || { echo "usage: make version VERSION=X.Y.Z"; exit 2; }
	@# --set also re-installs the editable library: Home Assistant compares the
	@# manifest pin against what is *installed*, not against pyproject.toml.
	$(PY) scripts/sync_version.py --set $(VERSION)
.PHONY: version

##@ Other

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make <target> [VAR=value]\n"} \
	     /^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5); next} \
	     /^[a-zA-Z0-9_-]+:.*##/ {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' \
	     $(MAKEFILE_LIST)
	@echo
.PHONY: help
