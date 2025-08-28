version := `uv run python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])'`


default: dev

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist src/*.egg-info

sync:
    uv sync --all-extras

build: clean lint audit test
    uv build --package mm-base6

format:
    uv run ruff check --select I --fix src tests
    uv run ruff format src tests

lint: format pre-commit
    uv run ruff check src tests
    uv run mypy src

audit:
    uv export --no-dev --all-extras --format requirements-txt --no-emit-project > requirements.txt
    uv run pip-audit -r requirements.txt --disable-pip
    rm requirements.txt
    uv run bandit --silent --recursive --configfile "pyproject.toml" src

test:
    uv run pytest tests

publish: build
    git diff-index --quiet HEAD
    uvx twine upload dist/**
    git tag -a 'v{{version}}' -m 'v{{version}}' && git push origin v{{version}}


demo:
    uv run python scripts/update_demo.py

dev:
    uv run python -m watchfiles "python -m app.main" src

pre-commit:
    uv run pre-commit run --all-files

pre-commit-autoupdate:
    uv run pre-commit autoupdate
