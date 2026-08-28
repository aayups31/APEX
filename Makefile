.PHONY: install test lint verify api

install:
	python -m pip install -e './apex_engine[dev]'

test:
	cd apex_engine && python -m pytest -q

lint:
	python -m ruff check apex_engine/src apex_engine/tests

verify: lint test

api:
	cd apex_engine && python -m apexsim.cli api --host 127.0.0.1 --port 8000

