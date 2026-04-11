# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) and other compatible agentic tools when working with the `network.compliance` Ansible Validated Content collection.

**Note:** This file is for AI assistant use only. For human developers, see the collection [README.md](README.md).

## Important: Always Start Here

**BEFORE starting any development or review task:**

1. **Read this file first** — Don't work from memory or assumptions
2. **Check the relevant SKILL.md** — Skills contain step-by-step workflows for common tasks
3. **Use TodoWrite** to create a task list and track progress systematically
4. **Follow the architecture and conventions** documented below

## Project Overview

`network.compliance` is an Ansible Validated Content collection that automates STIG (Security Technical Implementation Guide) compliance evaluation and remediation for network devices.

### Supported Platforms

| Platform | `ansible_network_os` | Collection Dependency |
|----------|---------------------|----------------------|
| Cisco IOS / IOS-XE | `cisco.ios.ios` | `cisco.ios` |

### Compliance Framework

| Framework | Status | Standard Body |
|-----------|--------|---------------|
| STIG | Active | DISA (Defense Information Systems Agency) |

## Architecture

### Four-Phase Lifecycle

Every compliance workflow follows four phases. Each phase is a separate Ansible role:

```
scan → evaluate → remediate → report
```

| Role | Purpose | OS-Dependent? | Framework-Dependent? |
|------|---------|---------------|---------------------|
| `scan` | Discover device state, classify interfaces | Yes | No |
| `evaluate` | Read-only audit against compliance rules | Yes | Yes |
| `remediate` | Apply compliant configurations | Yes | Yes |
| `report` | Generate CKLB/XCCDF artifacts | Minimal | Yes |

### Task Dispatching Pattern

Roles dispatch to platform-specific and framework-specific task files using `include_tasks`:

```yaml
# evaluate/tasks/main.yaml
- name: Include framework and platform evaluation tasks
  ansible.builtin.include_tasks:
    file: "{{ compliance.framework }}/{{ evaluate_platform }}/main.yaml"
```

Each role resolves the platform from `compliance.platform` or derives it from `ansible_network_os` (e.g., `cisco.ios.ios` → `ios`).

### Directory Layout

```
roles/
  scan/
    tasks/
      main.yaml                    # Dispatches by platform
      ios.yaml                     # Cisco IOS/IOS-XE discovery
    defaults/main.yaml
    meta/argument_specs.yml

  evaluate/
    tasks/
      main.yaml                    # Dispatches by framework + platform
      stig/
        ios/
          main.yaml                # Includes cat1.yaml, cat2.yaml, cat3.yaml
          cat1.yaml                # High severity (CAT I)
          cat2.yaml                # Medium severity (CAT II)
          cat3.yaml                # Low severity (CAT III)
    vars/
      stig/
        ios/                       # Platform-specific rule metadata
          cat1.yaml                # CAT I rules
          cat2.yaml                # CAT II rules
          cat3.yaml                # CAT III rules
    defaults/main.yaml
    meta/argument_specs.yml

  remediate/
    tasks/
      main.yaml
      stig/ios/
    templates/
      stig/ios/                    # Remediation config templates
    defaults/main.yaml
    meta/argument_specs.yml

  report/
    tasks/
      main.yaml
      stig/
        main.yaml                  # CKLB + XCCDF via filter plugins
        stigmanager.yaml           # STIG Manager API integration (uri-based)
    defaults/main.yaml
    meta/argument_specs.yml

plugins/
  filter/
    compliance.py                  # Filter plugins (check_results, stig_result, etc.)
    check_results.yml              # YAML documentation (one per filter)
    stig_result.yml
    evaluate_results.yml
    to_cklb.yml
    to_xccdf.yml
```

## Conventions

### Variable Naming

**STIG control variables** follow the DISA standard pattern:

```yaml
stig_controls:
  V-220649:
    run: true
    description: "802.1x authentication on access ports"
    severity: "CAT-I"
    stig_id: "CISC-L2-000020"
    # Platform-specific parameters below
    auth_hostmode: "single-host"
  V-220650:
    run: true
    description: "VTP password"
    severity: "CAT-II"
    stig_id: "CISC-L2-000030"
```

**Top-level config** (nested dict):

```yaml
compliance:
  framework: stig
  platform: ios                        # Derived from ansible_network_os
```

**Per-phase settings** (one dict per action):

```yaml
compliance_evaluate:
  cat1: true
  cat2: true
  cat3: true

compliance_remediate:
  cat1: true
  cat2: true
  cat3: true

compliance_report:
  format: cklb                         # cklb, xccdf, both
  output_dir: /tmp/compliance_reports

compliance_stigmanager:
  enabled: false
```

See `docs/adr/0002-conventions-and-data-model.md` for the full variable structure.

### Task Naming

Every task name MUST include STIG metadata for traceability:

```yaml
- name: >-
    STIG | {{ stig_id }} | {{ v_key }} | {{ severity }} |
    {{ short_description }}
```

Example:
```yaml
- name: >-
    STIG | CISC-L2-000020 | V-220649 | CAT-I |
    Verify 802.1x authentication on access ports
```

### Tag Convention

All tasks MUST be tagged for granular execution:

```yaml
tags:
  - CISC-L2-000020          # STIG ID
  - V-220649                # V-Key
  - SV-220649r863283        # Rule ID with revision
  - cat1                    # Severity category (lowercase)
  - CCI-000044              # Common Configuration Identifier
```

Users filter execution with: `--tags "cat1"`, `--tags "V-220649"`, etc.

### Module Usage

- **Always use FQCNs** (Fully Qualified Collection Names): `cisco.ios.ios_config`, not `ios_config`
- **Use `<os>_command` for evaluate** and **`<os>_config` for remediate** — one consistent pattern across all rules
- **Use `evaluate_results` filter** to extract non-compliant items, build status dict, and merge results in one call
- **Resource modules** (`state: gathered`) are used in the **scan role only** for fact gathering
- **Use `ansible.utils.fact_diff`** for comparing config blocks against golden baselines
- **Use `ansible.builtin.uri`** for STIG Manager API calls (no custom modules)
- **Use `to_cklb` and `to_xccdf` filter plugins** for generating compliance reports

### Check Mode

- The `evaluate` role MUST work in `check_mode` (read-only, no device changes)
- The `remediate` role MUST be idempotent (running twice = no further changes)
- The `scan` role gathers facts only (inherently read-only)

### Error Handling

- **Safe-fail logic required:** Before disabling access methods (SSH, VTY), verify alternative access exists
- **Use `block/rescue`** for operations that could cause lockout
- **Never use `ignore_errors: true`** — handle errors explicitly
- **Mark sensitive values** with `no_log: true` (passwords, RADIUS keys, SNMP communities)

## Testing

This collection uses [Molecule](https://github.com/ansible/molecule) from the
[ansible-dev-tools](https://github.com/ansible/ansible-dev-tools) ecosystem for testing.

### Running Tests

```bash
# Install toolchain
pip install ansible-dev-tools

# Lint checks
tox -e lint

# Sanity tests
ansible-test sanity -v --docker default

# Molecule scenarios (integration testing)
molecule test -s evaluate-stig-ios          # Run a specific scenario
molecule test --all                         # Run all scenarios
tox -e molecule                             # Run via tox (CI)

# Step-by-step debugging
molecule converge -s evaluate-stig-ios      # Apply role
molecule idempotence -s evaluate-stig-ios   # Verify idempotency
molecule verify -s evaluate-stig-ios        # Assert results
molecule destroy -s evaluate-stig-ios       # Clean up
```

### Test Structure

```
extensions/
  molecule/
    scan-stig-ios/
    evaluate-stig-ios/             # <role>-<framework>-<platform>
      molecule.yaml
      converge.yaml
      verify.yaml
      prepare.yaml                 # Optional: set up mock state
    remediate-stig-ios/
    report-stig-ios/
    workflow-stig-ios/             # End-to-end: scan → evaluate → remediate → report
```

### Writing Tests

- Every new STIG rule implementation MUST have a Molecule scenario
- Use `converge.yml` to apply the role, `verify.yml` to assert results
- Tests should verify both pass (compliant) and fail (non-compliant) scenarios
- Use Molecule's built-in `idempotence` step for remediation roles
- Use the `default` (delegated) driver for network devices
- Mock device state via inventory `group_vars` when no lab is available

## STIG Rule Development Workflow

See the `stig-rule-development` skill for the detailed step-by-step process.

**Quick reference:**

1. Identify the STIG rule (V-key, STIG ID, severity, SRG)
2. Add rule metadata to `evaluate/vars/stig/<platform>/cat<N>.yaml`
3. Create evaluation task in `evaluate/tasks/stig/<platform>/cat<N>.yaml`
4. Create golden baseline template in `evaluate/templates/stig/<platform>/`
5. Create remediation task in `remediate/tasks/stig/<platform>/cat<N>.yaml`
6. Create remediation template in `remediate/templates/stig/<platform>/`
7. Update report template to include the new rule
8. Add tags (STIG ID, V-key, severity, CCI)
9. Write integration test
10. Update `argument_specs.yml` with any new variables

## Report Generation

Reports are generated by `to_cklb` and `to_xccdf` filter plugins (not Jinja2 templates).

### CKLB Format (STIG Viewer)

- JSON file compatible with DISA STIG Viewer (https://www.stigviewer.com/stigs)
- Contains: rule status (`not_a_finding`, `open`, `not_reviewed`), finding details, target info
- Generated by: `stig_results | network.compliance.to_cklb(rules=stig_rules, ...)`

### XCCDF Format (STIG Manager)

- XML file following NIST XCCDF 1.2 specification
- Includes STIG Manager namespace extensions (`sm:detail`, `sm:resultEngine`)
- Generated by: `stig_results | network.compliance.to_xccdf(rules=stig_rules, ...)`
- Can be auto-imported by `stigman-watcher` or POSTed via API

### STIG Manager API Integration

- Uses `ansible.builtin.uri` module (no custom module)
- Requires OIDC token for authentication
- Batch endpoint: `POST /api/collections/{collectionId}/reviews`
- Supports `dryRun: true` for validation

## Dependencies

### Collection Dependencies (galaxy.yml)

```yaml
dependencies:
  cisco.ios: ">=8.0.0"
  ansible.netcommon: ">=6.0.0"
  ansible.utils: ">=4.0.0"
```

### Python Dependencies

- `jmespath` — JSON query support
- `xmltodict` — XCCDF XML generation

## Code Quality

- **ansible-lint**: Must pass with production profile (`.ansible-lint` skips `var-naming[no-role-prefix]`)
- **ruff**: Python linting and formatting (replaces black + flake8 + isort)
- **gitleaks**: Secret scanning in pre-commit and CI
- **yamllint**: Must pass with collection rules
- **Line length**: 100 characters for Python, 160 for YAML
- **No trailing whitespace**
- **YAML files**: Use `.yaml` extension (not `.yml`). Exception: `galaxy.yml`
- **Jinja2 templates**: Use `.j2` extension
- **Pre-commit hooks**: Install with `pre-commit install`
- **Local CI checks**: Run `tox -e ci` before pushing, `tox -e fix` to auto-fix

## PR Review Checklist

When reviewing PRs for this collection:

```text
[ ] STIG rule metadata added to vars/stig/<platform>/catN.yaml
[ ] Task names follow naming convention (STIG | ID | V-key | Severity | Description)
[ ] Tags applied (STIG ID, V-key, severity, CCI)
[ ] FQCNs used for all modules
[ ] evaluate_results or check_results + stig_result filters used
[ ] check_mode supported in evaluate tasks
[ ] Idempotent remediation
[ ] no_log on sensitive values
[ ] argument_specs.yml updated for new variables
[ ] Molecule scenario added (converge + verify, pass + fail)
[ ] Changelog fragment in changelogs/fragments/
[ ] tox -e ci passes locally
```

## External References

- **STIG Viewer**: https://www.stigviewer.com/stigs
- **STIG Manager**: https://github.com/NUWCDIVNPT/stig-manager
- **DISA STIG Library**: https://public.cyber.mil/stigs/
- **Ansible Validated Content**: https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.3/html/managing_red_hat_certified_and_ansible_galaxy_collections_in_automation_hub/assembly-validated-content
