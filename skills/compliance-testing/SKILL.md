---
name: compliance-testing
description: >-
  Write and run tests for the network.compliance collection using Molecule
  (from ansible-dev-tools). Use when creating scenarios for STIG rules,
  running lint checks, testing idempotency, or validating compliance
  workflows end-to-end.
license: GPL-3.0-or-later
compatibility: Requires molecule, ansible-lint, ansible-dev-tools (adt), and Podman or Docker.
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

This collection uses [Molecule](https://github.com/ansible/molecule) from the
[ansible-dev-tools](https://github.com/ansible/ansible-dev-tools) ecosystem:

| Tool | Purpose |
|------|---------|
| `molecule` | Test framework — manages scenario lifecycle (create → converge → verify → destroy) |
| `ansible-lint` | Lint playbooks, roles, and tasks |
| `ansible-navigator` | Optional: run playbooks with a TUI |
| `tox` + `tox-ansible` | Orchestrate lint + molecule across scenarios |
| `yamllint` | YAML formatting checks |

Install with:
```bash
pip install ansible-dev-tools
```

## Test types

### 1. Linting (fastest, run first)

```bash
# Run all linters via tox
tox -e lint

# Individual linters
ansible-lint roles/
yamllint roles/
```

**What it checks:**
- YAML syntax and formatting
- Ansible best practices (FQCNs, deprecated modules, etc.)
- Task naming conventions
- Tag usage

### 2. Sanity tests

```bash
ansible-test sanity -v --docker default
```

**What it checks:**
- Python code quality (callback plugins)
- YAML validity across all files
- Import checks

### 3. Molecule scenarios (integration testing)

```bash
# Run the default scenario for a role
molecule test -s evaluate_stig_ios

# Run all scenarios
molecule test --all

# Run via tox (recommended for CI)
tox -e molecule

# Step-by-step (useful for debugging)
molecule create -s evaluate_stig_ios
molecule converge -s evaluate_stig_ios
molecule idempotence -s evaluate_stig_ios
molecule verify -s evaluate_stig_ios
molecule destroy -s evaluate_stig_ios
```

## Molecule scenario structure

### Directory layout

Each role has Molecule scenarios under `molecule/`:

```
extensions/
  molecule/
    evaluate_stig_ios/               # Scenario: evaluate STIG on IOS
      molecule.yml                   # Scenario configuration
      converge.yml                   # Apply the role under test
      verify.yml                     # Assert expected results
      prepare.yml                    # Optional: set up mock device state
    evaluate_stig_junos/             # Scenario: evaluate STIG on JunOS
      molecule.yml
      converge.yml
      verify.yml
    remediate_stig_ios/              # Scenario: remediate STIG on IOS
      molecule.yml
      converge.yml
      verify.yml
    report_stig_cklb/                # Scenario: CKLB report generation
      molecule.yml
      converge.yml
      verify.yml
    full_workflow_ios/               # Scenario: end-to-end workflow
      molecule.yml
      converge.yml
      verify.yml
```

### molecule.yml — Scenario configuration

For network device testing, use the `default` (delegated) driver since we manage
device provisioning externally (lab, CML, or mock):

```yaml
---
# molecule/evaluate_stig_ios/molecule.yml
driver:
  name: default                      # Delegated — we manage the inventory

platforms:
  - name: ios-switch-01
    groups:
      - ios_switches
      - stig_targets

provisioner:
  name: ansible
  inventory:
    hosts:
      all:
        hosts:
          ios-switch-01:
            ansible_host: "${MOLECULE_IOS_HOST:-localhost}"
            ansible_connection: "${MOLECULE_CONNECTION:-ansible.netcommon.network_cli}"
            ansible_network_os: cisco.ios.ios
            ansible_user: "${MOLECULE_IOS_USER:-admin}"
            ansible_password: "${MOLECULE_IOS_PASS:-admin}"
    group_vars:
      stig_targets:
        compliance_framework: stig
        compliance_platform: ios
  env:
    ANSIBLE_ROLES_PATH: "${MOLECULE_PROJECT_DIRECTORY}/roles"
  config_options:
    defaults:
      gathering: explicit

dependency:
  name: galaxy
  options:
    requirements-file: requirements.yml

scenario:
  test_sequence:
    - dependency
    - syntax
    - create
    - prepare
    - converge
    - idempotence
    - verify
    - destroy
```

**For mock/local testing** (no real device needed):

```yaml
---
# molecule/evaluate_stig_ios_mock/molecule.yml
driver:
  name: default

platforms:
  - name: mock-ios-01
    groups:
      - ios_switches

provisioner:
  name: ansible
  inventory:
    hosts:
      all:
        hosts:
          mock-ios-01:
            ansible_host: localhost
            ansible_connection: local
    group_vars:
      ios_switches:
        compliance_framework: stig
        compliance_platform: ios
        # Pre-populated mock data (simulates scan output)
        compliance_access_ports:
          - name: GigabitEthernet0/1
            mode: access
          - name: GigabitEthernet0/2
            mode: access
        compliance_trunk_ports:
          - name: GigabitEthernet0/48
            mode: trunk

scenario:
  test_sequence:
    - dependency
    - syntax
    - converge
    - idempotence
    - verify
```

### converge.yml — Apply the role under test

```yaml
---
# molecule/evaluate_stig_ios/converge.yml
- name: Converge — Run STIG evaluation on IOS
  hosts: stig_targets
  gather_facts: false
  vars:
    stig_controls:
      V-220649:
        run: true
        auth_hostmode: single-host
      V-220650:
        run: true
      V-220651:
        run: true
    compliance_cat1_evaluate: true
    compliance_cat2_evaluate: true
    compliance_cat3_evaluate: false
  roles:
    - network.compliance.evaluate
```

### verify.yml — Assert expected results

```yaml
---
# molecule/evaluate_stig_ios/verify.yml
- name: Verify — Check STIG evaluation results
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Assert stig_results is populated
      ansible.builtin.assert:
        that:
          - stig_results is defined
          - stig_results | length > 0
        fail_msg: "stig_results was not populated by the evaluate role"

    - name: Assert V-220649 was evaluated
      ansible.builtin.assert:
        that:
          - "'V-220649' in stig_results"
          - stig_results['V-220649'].status in ['not_a_finding', 'open']
        fail_msg: "V-220649 was not evaluated or has invalid status"

    - name: Assert finding details are present for open findings
      ansible.builtin.assert:
        that:
          - stig_results[item].detail is defined
          - stig_results[item].detail | length > 0
      loop: "{{ stig_results | dict2items | selectattr('value.status', 'equalto', 'open') | map(attribute='key') | list }}"
      loop_control:
        label: "{{ item }}"
```

### prepare.yml — Set up test preconditions

```yaml
---
# molecule/remediate_stig_ios/prepare.yml
- name: Prepare — Create a non-compliant device state
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Set mock evaluation results (simulates open findings)
      ansible.builtin.set_fact:
        stig_results:
          V-220649:
            status: open
            findings:
              - GigabitEthernet0/1
              - GigabitEthernet0/2
            detail: "Non-compliant interfaces: GigabitEthernet0/1, GigabitEthernet0/2"
          V-220656:
            status: open
            findings:
              - GigabitEthernet0/1
            detail: "Missing BPDU guard on GigabitEthernet0/1"
```

## Common scenario patterns

### Pattern: Evaluation pass/fail

Test both compliant and non-compliant device states in the same scenario:

```yaml
# converge.yml
- name: Converge — Evaluate non-compliant device
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Run evaluation with non-compliant state
      ansible.builtin.include_role:
        name: network.compliance.evaluate
      vars:
        compliance_framework: stig
        compliance_platform: ios
        stig_controls:
          V-220649:
            run: true

    - name: Save non-compliant results
      ansible.builtin.set_fact:
        _noncompliant_results: "{{ stig_results }}"

# verify.yml
- name: Verify — Non-compliant findings detected
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Assert open findings exist
      ansible.builtin.assert:
        that:
          - _noncompliant_results['V-220649'].status == 'open'
          - _noncompliant_results['V-220649'].findings | length > 0
```

### Pattern: Remediation idempotency

Molecule has built-in idempotence testing. It re-runs `converge.yml` and fails
if any task reports `changed`:

```yaml
# molecule.yml — include idempotence in test_sequence
scenario:
  test_sequence:
    - converge
    - idempotence        # Automatically re-runs converge, asserts no changes
    - verify
```

For the remediate role specifically:

```yaml
# molecule/remediate_stig_ios/converge.yml
- name: Converge — Apply STIG remediation
  hosts: stig_targets
  gather_facts: false
  roles:
    - role: network.compliance.remediate
      vars:
        compliance_framework: stig
        compliance_platform: ios
        stig_results:
          V-220649:
            status: open
            findings: [GigabitEthernet0/1]
        stig_controls:
          V-220649:
            run: true
            auth_hostmode: single-host
```

The `idempotence` step will re-run this and verify zero changes on second run.

### Pattern: Report format validation

```yaml
# molecule/report_stig_cklb/verify.yml
- name: Verify — CKLB report is valid
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Read generated CKLB file
      ansible.builtin.slurp:
        src: "{{ compliance_report_output_path }}"
      register: _cklb_raw

    - name: Parse CKLB JSON
      ansible.builtin.set_fact:
        _cklb: "{{ _cklb_raw.content | b64decode | from_json }}"

    - name: Assert CKLB structure
      ansible.builtin.assert:
        that:
          - _cklb.title is defined
          - _cklb.stigs is defined
          - _cklb.stigs | length > 0
          - _cklb.target_data.host_name is defined

    - name: Assert each rule has required fields
      ansible.builtin.assert:
        that:
          - item.group_id is defined
          - item.rule_id is defined
          - item.status in ['not_a_finding', 'open', 'not_reviewed', 'not_applicable']
      loop: "{{ _cklb.stigs[0].rules }}"
      loop_control:
        label: "{{ item.group_id }}"
```

### Pattern: End-to-end workflow

```yaml
# molecule/full_workflow_ios/converge.yml
- name: Converge — Full STIG compliance workflow
  hosts: stig_targets
  gather_facts: false
  vars:
    compliance_framework: stig
    compliance_platform: ios
    stig_controls:
      V-220649: { run: true }
      V-220650: { run: true }
  tasks:
    - name: Phase 1 — Scan
      ansible.builtin.include_role:
        name: network.compliance.scan

    - name: Phase 2 — Evaluate
      ansible.builtin.include_role:
        name: network.compliance.evaluate

    - name: Phase 3 — Remediate
      ansible.builtin.include_role:
        name: network.compliance.remediate

    - name: Phase 4 — Report
      ansible.builtin.include_role:
        name: network.compliance.report
```

## CI workflow with Molecule

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
          - evaluate_stig_ios
          - remediate_stig_ios
          - report_stig_cklb
          - full_workflow_ios
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

## Debugging Molecule failures

```bash
# Step through the scenario interactively
molecule create -s evaluate_stig_ios
molecule converge -s evaluate_stig_ios
molecule login -s evaluate_stig_ios -h ios-switch-01   # SSH into test instance

# Run with verbose output
molecule --debug test -s evaluate_stig_ios

# Keep instances after failure for inspection
molecule converge -s evaluate_stig_ios
molecule verify -s evaluate_stig_ios    # If this fails, instances are still up
# ... inspect, debug ...
molecule destroy -s evaluate_stig_ios   # Clean up manually
```

**Common issues:**
1. **converge fails** — Check role variables, inventory, and connection settings
2. **idempotence fails** — A task is not idempotent; check `changed_when` conditions
3. **verify fails** — Assertions don't match actual results; debug with `-vvv`
4. **dependency fails** — Collection requirements not met; check `requirements.yml`

## Checklist

```text
[ ] Molecule scenario created under extensions/molecule/<scenario_name>/
[ ] molecule.yml configures correct driver, platform, and inventory
[ ] converge.yml applies the role with appropriate variables
[ ] verify.yml asserts both pass and fail scenarios
[ ] idempotence included in test_sequence for remediate roles
[ ] prepare.yml sets up preconditions (if needed)
[ ] requirements.yml lists collection dependencies
[ ] Scenario runs cleanly: molecule test -s <scenario_name>
[ ] All linters pass (tox -e lint)
```
