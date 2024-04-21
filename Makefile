init:
	pip install -r requirements.txt
devel:
	pip install -r requirements_dev.txt
	pre-commit install --hook-type pre-commit --hook-type pre-push
test:
	pytest --cov-config=.coveragerc --cov-branch --cov=MKVAudioSubsDefaulter --cov-fail-under 80 --cov-report term-missing --cov-report xml tests/
analysis: # Lint, format, import optimizer, etc.
	pipenv run pre-commit run --all-files
install:
	pip install --upgrade .
