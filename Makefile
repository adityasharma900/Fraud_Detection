# ----------------------------------------------------------------------------
# Credit-Card Fraud Detection on MongoDB  -  one-command reproduction
# Usage examples:
#   make up                 # start MongoDB (Docker)
#   make gen                # generate D1, D2, D3 datasets
#   make pipeline D=D1      # load + derive + extend for one dataset
#   make bench              # benchmark all datasets, write figures
#   make all                # everything, end to end
# ----------------------------------------------------------------------------
PY ?= python
D  ?= D1

.PHONY: up down gen load derive extend pipeline bench dashboard test verify all clean

up:        ; docker compose up -d
down:      ; docker compose down

gen:       ; $(PY) src/generate.py --all
load:      ; $(PY) src/load.py --dataset $(D)
derive:    ; $(PY) src/build_derived.py --dataset $(D)
extend:    ; $(PY) src/extend.py --dataset $(D)
pipeline:  load derive extend

bench:     ; $(PY) src/benchmark.py --all
dashboard: ; $(PY) src/dashboard.py
test:      ; $(PY) -m pytest -q tests/

# Offline algorithm check (no MongoDB needed): pandas oracle over a sample.
verify:    ; $(PY) tests/oracle_pandas.py

all: up gen
	$(MAKE) pipeline D=D1
	$(MAKE) pipeline D=D2
	$(MAKE) pipeline D=D3
	$(MAKE) bench
	$(MAKE) dashboard

clean:
	rm -rf data/*/ results/*.csv report/figures/*.png
