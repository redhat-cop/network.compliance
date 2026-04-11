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
envlist = lint, molecule

[testenv:lint]
deps = ansible-dev-tools
commands =
    ansible-lint roles/
    yamllint roles/

[testenv:molecule]
deps = ansible-dev-tools
commands =
    molecule test --all
```
