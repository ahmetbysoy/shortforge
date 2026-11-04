# ShortForge - gelistirici komutlari
.PHONY: help install doctor doctor-json test test-live lint fmt type schema check

help:
	@grep -E "^[a-z-]+:.*?##" $(MAKEFILE_LIST) | sed "s/:.*##/\t/" | column -t -s "	"

install: ## Gelistirme ortami kur
	python -m pip install -e ".[dev]"

doctor: ## Saglayici + kota + ortam raporu
	shortforge doctor

doctor-json: ## Ayni rapor, JSON
	shortforge doctor --json

test: ## Unit testler (aga cikmaz)
	pytest -m "not live"

test-live: ## Gercek ag cagrisi yapan testler
	pytest -m live

lint: ## Ruff kontrolu
	ruff check . && ruff format --check .

fmt: ## Kodu bicimlendir
	ruff format . && ruff check --fix .

type: ## mypy (strict)
	mypy src

schema: ## Script JSON semasini uret
	python scripts/export_schema.py

check: lint type test ## CI ile ayni kontroller
