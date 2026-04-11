---
name: dev-environment-setup
description: >-
  Set up a local development environment for the network.compliance collection.
  Use when cloning the repo for the first time, onboarding a new contributor,
  or troubleshooting environment issues. Covers ade, ansible-dev-tools, and
  virtual environment setup.
license: GPL-3.0-or-later
compatibility: Requires Python 3.10+, pip or uv, and git.
metadata:
  author: network-compliance-team
  version: "1.0"
---

# Development Environment Setup

## When to use this skill

Use this skill when:
- Setting up the project for the first time after cloning
- Onboarding a new contributor
- Recreating a broken or stale virtual environment
- Upgrading ansible-core or collection dependencies

## Prerequisites

- Python 3.10+ installed
- `git` installed
- Access to the repository

## Quick setup

```bash
# 1. Clone the repository
git clone https://github.com/redhat-cop/network.compliance.git
cd network.compliance

# 2. Install ansible-dev-tools (includes ade, ansible-lint, molecule, tox, pytest)
pip install ansible-dev-tools

# 3. Create isolated virtual environment with editable collection install
ade install -e . --venv .venv

# 4. Activate
source .venv/bin/activate

# 5. Verify
ansible-galaxy collection list | grep network.compliance
adt --version
```

## What each tool does

**ansible-dev-tools (adt)** is a meta-package that bundles:

| Tool | Purpose |
|------|---------|
| `ansible-core` | Ansible automation engine |
| `ansible-lint` | Lints playbooks, roles, tasks |
| `molecule` | Integration test framework |
| `tox` + `tox-ansible` | Test orchestration across versions |
| `pytest` + `pytest-ansible` | Unit test framework |
| `ansible-creator` | Scaffolds new collections/roles |
| `ansible-navigator` | TUI for running playbooks |
| `ansible-builder` | Builds execution environments |
| `ansible-dev-environment (ade)` | Virtual environment manager for collections |

**ansible-dev-environment (ade)** handles the virtual environment:

- Creates `.venv/` with isolated Python environment
- Installs `ansible-core` at the required version
- Installs collection dependencies from `galaxy.yml` (`cisco.ios`, `ansible.utils`, etc.)
- Installs Python dependencies from `requirements.txt` (`jmespath`, `xmltodict`)
- **Symlinks** the collection source into the venv so edits are immediately reflected
- Configures `ansible.cfg` for workspace isolation (prevents picking up global collections)

## Common operations

### Recreate the virtual environment

```bash
rm -rf .venv
ade install -e . --venv .venv
source .venv/bin/activate
```

### Use a specific Python version

```bash
ade install -e . --venv .venv --python python3.12
```

### Use a specific ansible-core version

```bash
ade install -e . --venv .venv --acv 2.18.0
```

### Install with test dependencies

If a `test-requirements.txt` exists, ade installs it automatically. Otherwise:

```bash
source .venv/bin/activate
pip install pytest pytest-ansible
```

### Run CI checks locally before pushing

Run all CI checks with one command:

```bash
source .venv/bin/activate
tox -e ci
```

This runs the same checks as the GitHub Actions CI pipeline:
- `ansible-lint` (production profile)
- `ruff check` (Python linting)
- `ruff format --check` (Python formatting)
- `pytest tests/unit/` (unit tests for filter plugins)

### Run individual checks

```bash
tox -e lint           # ansible-lint only
tox -e unit           # unit tests only
tox -e ruff           # ruff lint + format check
tox -e sanity         # ansible-test sanity (requires Docker)
tox -e gitleaks       # scan for secrets (requires gitleaks installed)
tox -e pre-commit     # run all pre-commit hooks
tox -e molecule       # run all Molecule scenarios
```

### Run checks without tox

```bash
source .venv/bin/activate

ansible-lint                              # ansible-lint
ruff check plugins/ tests/                # Python linting
ruff format --check plugins/ tests/       # Python format check
pytest tests/unit/ -v                     # unit tests
ansible-test sanity -v --docker default   # sanity (needs Docker)
molecule test -s evaluate-stig-ios        # single Molecule scenario
molecule test --all                       # all Molecule scenarios
```

### Set up pre-commit hooks

Install hooks to run automatically on every commit:

```bash
pip install pre-commit
pre-commit install
```

Hooks run: trailing whitespace fix, merge conflict check, private key detection,
ruff lint + format, gitleaks secret scanning, ansible-lint.

### Check what's installed

```bash
ade list                    # List installed collections
ade tree                    # Show dependency tree
ade inspect network.compliance  # Inspect this collection
```

## Tox environments reference

| Environment | Command | What it checks | CI equivalent |
|-------------|---------|----------------|---------------|
| `ci` | `tox -e ci` | All fast checks combined | Full CI minus sanity/molecule |
| `lint` | `tox -e lint` | ansible-lint | `ansible-lint` job |
| `unit` | `tox -e unit` | pytest unit tests | `unit-galaxy` / `unit-source` jobs |
| `ruff` | `tox -e ruff` | Python lint + format | (included in `ci`) |
| `sanity` | `tox -e sanity` | ansible-test sanity | `sanity` job |
| `gitleaks` | `tox -e gitleaks` | Secret scanning | `gitleaks` job |
| `pre-commit` | `tox -e pre-commit` | All pre-commit hooks | (local only) |
| `molecule` | `tox -e molecule` | All Molecule scenarios | (future integration job) |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ade: command not found` | Run `pip install ansible-dev-tools` |
| Collection not found after `ade install` | Activate the venv: `source .venv/bin/activate` |
| Wrong collection version picked up | Check `ansible.cfg` exists with `collections_path = .` |
| Module import errors in tests | Ensure venv is activated and deps are installed |
| `ansible-lint` fails on `var-naming` | Expected — `.ansible-lint` skips `var-naming[no-role-prefix]` for cross-role variables |
| `ruff` format failures | Run `ruff format plugins/ tests/` to auto-fix |
| `pre-commit` not running on commit | Run `pre-commit install` to set up hooks |
| `gitleaks` false positive | Add pattern to `.gitleaks.toml` allowlist |
