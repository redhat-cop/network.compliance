# CI Configuration

## GitHub Actions workflow

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ansible-dev-tools
      - run: ansible-lint roles/
      - run: yamllint roles/

  molecule:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        scenario:
          - evaluate-stig-ios
          - remediate-stig-ios
          - report-stig-ios
          - workflow-stig-ios
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ansible-dev-tools
      - run: molecule test -s ${{ matrix.scenario }}
```

## tox integration

```ini
# tox.ini
[tox]
env_list = ci, fix, lint, unit, ruff, sanity, gitleaks, pre-commit, molecule
skip_missing_interpreters = true

[testenv]
deps = ansible-dev-tools
skip_install = true

[testenv:ci]
description = Run all CI checks locally
deps =
    ansible-dev-tools
    pytest
    pytest-ansible
    ruff
commands =
    ansible-lint
    ruff check plugins/ tests/
    ruff format --check plugins/ tests/
    pytest tests/unit/ -v --color=yes

[testenv:fix]
description = Auto-fix lint and format issues
deps =
    ansible-dev-tools
    ruff
commands =
    ruff check plugins/ tests/ --fix
    ruff format plugins/ tests/
    ansible-lint --fix

[testenv:lint]
description = Run ansible-lint
commands = ansible-lint

[testenv:unit]
description = Run unit tests
deps =
    ansible-dev-tools
    pytest
    pytest-ansible
commands = pytest tests/unit/ -v --color=yes

[testenv:ruff]
description = Python lint and format check
deps = ruff
commands =
    ruff check plugins/ tests/
    ruff format --check plugins/ tests/

[testenv:molecule]
description = Run all Molecule scenarios
commands = molecule test --all
```
