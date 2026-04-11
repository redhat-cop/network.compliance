---
name: compliance-testing
description: >-
  Write and run tests for the network.compliance collection using Molecule
  from ansible-dev-tools. Use when creating scenarios for STIG rules,
  running lint checks, testing idempotency, or validating compliance
  workflows end-to-end.
license: GPL-3.0-or-later
compatibility: Requires molecule, ansible-lint, ansible-dev-tools, and Podman or Docker.
metadata:
  author: network-compliance-team
  version: "2.0"
---

# Compliance Testing with Molecule

## When to use this skill

Use this skill when:
- Writing Molecule scenarios for new or modified STIG rules
- Running the test suite before submitting a PR
- Debugging test failures in CI
- Testing idempotency of remediation roles
- Validating report generation end-to-end

## Toolchain

| Tool | Purpose |
|------|---------|
| `molecule` | Test framework (create, converge, verify, destroy) |
| `ansible-lint` | Lint playbooks, roles, and tasks |
| `tox` + `tox-ansible` | Orchestrate lint + molecule across scenarios |
| `yamllint` | YAML formatting checks |

Install: `pip install ansible-dev-tools`

## Running tests

```bash
# Linting (fastest, run first)
tox -e lint

# Sanity tests
ansible-test sanity -v --docker default

# Molecule scenarios
molecule test -s evaluate-stig-ios           # Single scenario
molecule test --all                         # All scenarios
tox -e molecule                             # Via tox (CI)

# Step-by-step debugging
molecule create -s evaluate-stig-ios
molecule converge -s evaluate-stig-ios
molecule idempotence -s evaluate-stig-ios
molecule verify -s evaluate-stig-ios
molecule destroy -s evaluate-stig-ios
```

## Scenario directory structure

```text
extensions/molecule/
├── scan-stig-ios/               # <role>-<framework>-<platform>
├── evaluate-stig-ios/
├── remediate-stig-ios/
├── report-stig-ios/
└── workflow-stig-ios/
```

Each contains: `molecule.yaml`, `converge.yaml`, `verify.yaml`, and optionally `prepare.yaml`.

## Writing a scenario

### Key files

- **molecule.yaml** — Driver (`default`/delegated), inventory, test sequence
- **converge.yaml** — Apply the role with `compliance`, `stig_controls`, etc.
- **verify.yaml** — Assert `stig_results` is populated with valid statuses
- **prepare.yaml** — Pre-populate mock data (e.g., `stig_results` for remediate testing)

See [references/molecule-templates.md](references/molecule-templates.md) for complete
templates of each file and scenario patterns (pass/fail, idempotency, report validation,
end-to-end workflow).

### Mock testing (no real device)

Use `ansible_connection: local` with pre-populated facts in `group_vars`:

```yaml
provisioner:
  inventory:
    hosts:
      all:
        hosts:
          mock-ios-01:
            ansible_host: localhost
            ansible_connection: local
    group_vars:
      ios_switches:
        compliance:
          framework: stig
          platform: ios
        compliance_access_ports:
          - name: GigabitEthernet0/1
            mode: access
```

### Test sequence

For **evaluate** scenarios: `dependency, syntax, converge, verify, destroy`

For **remediate** scenarios (add idempotence): `dependency, syntax, converge, idempotence, verify, destroy`

## Debugging failures

```bash
molecule --debug test -s evaluate-stig-ios       # Verbose output
molecule converge -s evaluate-stig-ios           # Run without destroying
molecule verify -s evaluate-stig-ios             # Inspect failures
molecule destroy -s evaluate-stig-ios            # Manual cleanup
```

| Issue | Diagnosis |
|-------|-----------|
| converge fails | Check role variables, inventory, connection settings |
| idempotence fails | Task not idempotent — check `changed_when` |
| verify fails | Assertions don't match — debug with `-vvv` |
| dependency fails | Collection requirements not met — check `requirements.yml` |

## CI integration

See [references/ci-config.md](references/ci-config.md) for GitHub Actions workflow
and tox configuration templates.

## Checklist

```text
[ ] Molecule scenario created under extensions/molecule/<scenario_name>/
[ ] molecule.yaml configures correct driver, platform, and inventory
[ ] converge.yaml applies the role with appropriate variables
[ ] verify.yaml asserts both pass and fail scenarios
[ ] idempotence included in test_sequence for remediate roles
[ ] prepare.yaml sets up preconditions (if needed)
[ ] requirements.yml lists collection dependencies
[ ] Scenario runs cleanly: molecule test -s <scenario_name>
[ ] All linters pass (tox -e lint)
```

## References

- [references/molecule-templates.md](references/molecule-templates.md) — Complete molecule, converge, verify, prepare templates and scenario patterns
- [references/ci-config.md](references/ci-config.md) — GitHub Actions and tox configuration
