# SPEC-0002: Testing and CI

## Goal

Integration testing for all roles using Molecule, with flat scenario names that map to the main code layout. CI orchestration via tox and GitHub Actions.

## Design

### Scenario naming convention

All scenario names follow `<role>-<framework>-<platform>`:

```text
Code path                              Molecule scenario
─────────────────────────────────      ──────────────────────
roles/scan/tasks/ios.yaml              scan-stig-ios
roles/evaluate/tasks/stig/ios/         evaluate-stig-ios
roles/remediate/tasks/stig/ios/        remediate-stig-ios
roles/report/tasks/stig/               report-stig-ios
(all roles, end-to-end)                workflow-stig-ios
```

### Directory layout

```text
extensions/molecule/
├── scan-stig-ios/
│   ├── molecule.yaml
│   ├── prepare.yaml
│   ├── converge.yaml
│   └── verify.yaml
├── evaluate-stig-ios/
│   ├── molecule.yaml
│   ├── prepare.yaml
│   ├── converge.yaml
│   └── verify.yaml
├── remediate-stig-ios/
│   ├── molecule.yaml
│   ├── prepare.yaml
│   ├── converge.yaml
│   └── verify.yaml
├── report-stig-ios/
│   ├── molecule.yaml
│   ├── prepare.yaml
│   ├── converge.yaml
│   └── verify.yaml
└── workflow-stig-ios/
    ├── molecule.yaml
    ├── converge.yaml
    └── verify.yaml
```

Adding a new platform (e.g., JunOS) = adding parallel scenarios:

- `scan-stig-junos/`
- `evaluate-stig-junos/`
- `remediate-stig-junos/`
- `report-stig-junos/`
- `workflow-stig-junos/`

Adding a new framework (e.g., CIS) = same pattern:

- `evaluate-cis-ios/`
- `remediate-cis-ios/`

### Running scenarios

```bash
molecule test -s evaluate-stig-ios       # Single scenario
molecule test -s remediate-stig-ios      # With idempotence
molecule test --all                      # All scenarios
```

### Test types by scenario

| Scenario | What it tests | Idempotence | Mock data in prepare.yaml |
|----------|---------------|-------------|---------------------------|
| `scan-stig-ios` | Interface classification from `ios_facts` | No | `ansible_facts.network_resources.l2_interfaces` |
| `evaluate-stig-ios` | `stig_results` populated, valid statuses | No | `compliance_access_ports`, `compliance_trunk_ports` |
| `remediate-stig-ios` | Remediation runs, config applied | Yes | `stig_results` with `open` findings |
| `report-stig-ios` | CKLB JSON + XCCDF XML valid | No | `stig_results` + `stig_rules` |
| `workflow-stig-ios` | End-to-end: scan -> evaluate -> remediate -> report | No | Full mock device state |

### Mock testing

All scenarios use `ansible_connection: local` with pre-populated facts. No real network devices required.

- **scan** — `prepare.yaml` seeds `ansible_facts.network_resources.l2_interfaces`
- **evaluate** — `prepare.yaml` seeds `compliance_access_ports`, `compliance_trunk_ports`
- **remediate** — `prepare.yaml` seeds `stig_results` with `open` findings
- **report** — `prepare.yaml` seeds `stig_results` + loads `stig_rules` from vars

### Test lifecycle

| Scenario type | Sequence |
|---------------|----------|
| scan, evaluate, report | `dependency -> syntax -> prepare -> converge -> verify -> destroy` |
| remediate | `dependency -> syntax -> prepare -> converge -> idempotence -> verify -> destroy` |
| workflow | `dependency -> syntax -> converge -> verify -> destroy` |

### CI orchestration

```bash
tox -e fix                     # auto-fix lint and format issues
tox -e ci                      # all fast CI checks combined
tox -e lint                    # ansible-lint (production profile)
tox -e unit                    # unit tests (filter plugins)
tox -e ruff                    # Python lint + format check
tox -e sanity                  # ansible-test sanity
tox -e gitleaks                # secret scanning
tox -e pre-commit              # all pre-commit hooks
tox -e molecule                # all Molecule scenarios
```

### GitHub Actions

```yaml
jobs:
  lint:
    steps: [checkout, setup-python, pip install ansible-dev-tools, ansible-lint]
  molecule:
    strategy:
      matrix:
        scenario:
          - scan-stig-ios
          - evaluate-stig-ios
          - remediate-stig-ios
          - report-stig-ios
          - workflow-stig-ios
```

## Acceptance Criteria

- [ ] Scenario names follow `<role>-<framework>-<platform>` convention
- [ ] Every STIG rule has pass and fail test assertions
- [ ] Remediation scenarios include idempotence step
- [ ] Mock testing works without network devices
- [ ] Adding a new platform or framework = adding parallel scenarios
- [ ] `tox -e lint` and `tox -e molecule` pass
- [ ] CI runs on push and PR

## Dependencies

- `ansible-dev-tools` (molecule, ansible-lint, yamllint, tox-ansible)
