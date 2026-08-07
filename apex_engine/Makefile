install:
	pip install -e .

test:
	pytest -q

run:
	apexsim run --config configs/fast.yaml --run-id reference_gru

ui:
	apexsim ui --run-dir artifacts/runs/reference_gru --config configs/fast.yaml

api:
	apexsim api --artifacts-dir artifacts/runs
