---
name: uv
description: >
  Default Python toolchain for this repo. Use whenever running Python, pytest,
  scripts, installs, or shell commands that would otherwise use python3, python,
  pip, pipx, pyenv, poetry, or virtualenv. This project has no usable system
  python3 — always prefer uv run / uv add / uvx.
---

# uv

uv is the **only** supported way to run Python in this project. It replaces pip,
pip-tools, pipx, pyenv, virtualenv, poetry, etc.

## Hard rule (read first)

**Never call `python3`, `python`, or `pip` in the shell.** They are not the
project environment (and often do not exist or are the wrong interpreter).

| Bad | Good |
|---|---|
| `python3 script.py` | `uv run script.py` |
| `python3 -m pytest` | `uv run pytest` |
| `python3 -c "…"` | `uv run python -c "…"` |
| `python3.12 -c "…"` | `uv run -p 3.12 python -c "…"` |
| `pip install requests` | `uv add requests` |
| `python3 -m venv .venv` | `uv sync` then `uv run …` |

If you catch yourself typing `python3`, rewrite the command with `uv run` first.

## When to use uv

**Always use uv for Python work** in this repo (`uv.lock` + `pyproject.toml`).

Don't use uv only in projects managed by other tools (not this one):

- Poetry projects (`poetry.lock`)
- PDM projects (`pdm.lock`)

## Choosing the right workflow

### Scripts

**Use when:** Running single Python files and standalone scripts.

```bash
uv run script.py                       # Run a script
uv run --with requests script.py       # Run with additional packages
uv add --script script.py requests     # Add dependencies inline to the script
```

### Projects

**Use when:** There is a `pyproject.toml` or `uv.lock` (this repo).

```bash
uv init                    # Create new project
uv add requests            # Add dependency
uv remove requests         # Remove dependency
uv sync                    # Install from lockfile
uv run <command>           # Run commands in environment
uv run pytest              # Run tests
uv run python -c ""        # Run Python in project environment
uv run -p 3.12 <command>   # Run with specific Python version
```

### Tools

**Use when:** Running CLI tools (e.g. ruff, ty, pytest) without installing them
into the project.

```bash
uvx <tool> <args>            # Run a tool without installation
uvx <tool>@<version> <args>  # Run a specific version of a tool
```

**Important:**

- `uvx` runs tools from PyPI by package name. Only run well-known tools.
- Use `uv tool install` only when specifically requested by the user.

### Pip interface

**Use when:** Legacy workflows with `requirements.txt` or manual environment
management, **no** `uv.lock` present. Prefer not to use this in this repo.

```bash
uv venv
uv pip install -r requirements.txt
uv pip compile requirements.in -o requirements.txt
uv pip sync requirements.txt

# Platform independent resolution
uv pip compile --universal requirements.in -o requirements.txt
```

**Important:**

- Don't use the pip interface unless clearly needed.
- Don't introduce new `requirements.txt` files.
- Prefer `uv init` for new projects.

## Migrating from other tools

### pyenv → uv python

```bash
pyenv install 3.12  → uv python install 3.12
pyenv versions      → uv python list --only-installed
pyenv local 3.12    → uv python pin 3.12
pyenv global 3.12   → uv python install 3.12 --default
```

### pipx → uvx

```bash
pipx run ruff       → uvx ruff
pipx install ruff   → uv tool install ruff
pipx upgrade ruff   → uv tool upgrade ruff
pipx list           → uv tool list
```

### pip and pip-tools → uv pip

```bash
pip install package     → uv pip install package
pip install -r req.txt  → uv pip install -r req.txt
pip freeze              → uv pip freeze
pip-compile req.in      → uv pip compile req.in
pip-sync req.txt        → uv pip sync req.txt
virtualenv .venv        → uv venv
```

## Common patterns

### Don't use pip in uv projects

```bash
# Bad
pip install requests

# Good
uv add requests
```

### Don't run python / python3 directly

```bash
# Bad
python script.py
python3 script.py

# Good
uv run script.py
```

```bash
# Bad
python -c "..."
python3 -c "..."

# Good
uv run python -c "..."
```

```bash
# Bad
python3.12 -c "..."

# Good
uv run -p 3.12 python -c "..."
# or (standalone, outside project env):
uvx python@3.12 -c "..."
```

### Don't manually manage environments in uv projects

```bash
# Bad
python3 -m venv .venv
source .venv/bin/activate

# Good
uv run <command>
```

## Documentation

For detailed information, read the official documentation:

- https://docs.astral.sh/uv/llms.txt
