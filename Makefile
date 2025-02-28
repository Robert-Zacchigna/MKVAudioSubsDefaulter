init:
	pip install -r requirements.txt
devel:
	make init
	poetry install --only dev
	pre-commit install --hook-type pre-commit --hook-type pre-push --install-hooks -t post-checkout -t post-merge
test:
	pytest --cov-config=.coveragerc --cov-branch --cov=MKVAudioSubsDefaulter --cov-fail-under 80 --cov-report term-missing --cov-report xml tests/
analysis: # Lint, format, import optimizer, etc.
	poetry run pre-commit run --all-files
install:
	poetry install
