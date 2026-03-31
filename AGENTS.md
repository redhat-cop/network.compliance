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
| Juniper JunOS | `junipernetworks.junos.junos` | `junipernetworks.junos` |

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
- name: Run compliance evaluation
  ansible.builtin.include_tasks:
    file: "{{ compliance_framework }}/{{ compliance_platform }}/main.yaml"
```

The `compliance_platform` variable is derived from `ansible_network_os` (e.g., `cisco.ios.ios` → `ios`).

### Directory Layout

```
roles/
  scan/
    tasks/
      main.yaml                    # Dispatches by platform
      ios.yaml                     # Cisco IOS/IOS-XE discovery
      junos.yaml                   # Juniper JunOS discovery
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
        junos/
    vars/
      stig/
        rules.yaml                 # STIG rule metadata (IDs, severity, descriptions)
        ios.yaml                   # Platform-specific golden baselines
    templates/
      stig/ios/                    # Expected config templates for fact_diff
    handlers/main.yaml             # Pass/fail handlers
    defaults/main.yaml
    meta/argument_specs.yml

  remediate/
    tasks/
      main.yaml
      stig/ios/, junos/
    templates/
      stig/ios/, junos/            # Remediation config templates
    defaults/main.yaml
    meta/argument_specs.yml

  report/
    tasks/
      main.yaml
      stig/
        main.yaml                  # CKLB + XCCDF generation
        stigmanager.yaml           # STIG Manager API integration (uri-based)
    templates/
      stig/
        stig_viewer.j2             # CKLB format
        xccdf_results.j2           # XCCDF format
    defaults/main.yaml
    meta/argument_specs.yml
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

**Role-level variables** use the `compliance_` prefix:

```yaml
compliance_framework: stig              # stig
compliance_platform: ios                # Derived from ansible_network_os
compliance_cat1_evaluate: true
compliance_cat2_evaluate: true
compliance_cat3_evaluate: true
compliance_report_format: cklb          # cklb, xccdf, both
compliance_stigmanager_enabled: false
```

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
- **Prefer resource modules** over raw commands: `cisco.ios.ios_interfaces` over `cisco.ios.ios_command` with `show run`
- **Use `ansible.utils.fact_diff`** for comparing gathered state against golden baselines
- **Use `ansible.builtin.uri`** for STIG Manager API calls (no custom modules)
- **Use `ansible.builtin.template`** for generating CKLB/XCCDF reports

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
molecule test -s evaluate_stig_ios          # Run a specific scenario
molecule test --all                         # Run all scenarios
tox -e molecule                             # Run via tox (CI)

# Step-by-step debugging
molecule converge -s evaluate_stig_ios      # Apply role
molecule idempotence -s evaluate_stig_ios   # Verify idempotency
molecule verify -s evaluate_stig_ios        # Assert results
molecule destroy -s evaluate_stig_ios       # Clean up
```

### Test Structure

```
extensions/
  molecule/
    evaluate_stig_ios/             # Scenario per role + platform combo
      molecule.yml                 # Driver, inventory, test_sequence
      converge.yml                 # Apply the role under test
      verify.yml                   # Assert expected results
      prepare.yml                  # Optional: set up mock state
    remediate_stig_ios/
    report_stig_cklb/
    full_workflow_ios/             # End-to-end: scan → evaluate → remediate → report
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
2. Add rule metadata to `evaluate/vars/stig/rules.yaml`
3. Create evaluation task in `evaluate/tasks/stig/<platform>/cat<N>.yaml`
4. Create golden baseline template in `evaluate/templates/stig/<platform>/`
5. Create remediation task in `remediate/tasks/stig/<platform>/cat<N>.yaml`
6. Create remediation template in `remediate/templates/stig/<platform>/`
7. Update report template to include the new rule
8. Add tags (STIG ID, V-key, severity, CCI)
9. Write integration test
10. Update `argument_specs.yml` with any new variables

## Report Generation

### CKLB Format (STIG Viewer)

- JSON file compatible with DISA STIG Viewer (https://www.stigviewer.com/stigs)
- Contains: rule status (`not_a_finding`, `open`, `not_reviewed`), finding details, target info
- Template: `report/templates/stig/stig_viewer.j2`

### XCCDF Format (STIG Manager)

- XML file following NIST XCCDF 1.2 specification
- Includes STIG Manager namespace extensions (`sm:detail`, `sm:resultEngine`)
- Template: `report/templates/stig/xccdf_results.j2`
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
  junipernetworks.junos: ">=8.0.0"
  ansible.netcommon: ">=6.0.0"
  ansible.utils: ">=4.0.0"
```

### Python Dependencies

- `jmespath` — JSON query support
- `xmltodict` — XCCDF XML generation

## Code Quality

- **ansible-lint**: Must pass with production profile
- **yamllint**: Must pass with collection rules
- **Line length**: 160 characters max
- **No trailing whitespace**
- **YAML files**: Use `.yaml` extension (not `.yml` — collection standard)
- **Jinja2 templates**: Use `.j2` extension

## PR Review Checklist

When reviewing PRs for this collection:

```text
[ ] STIG rule metadata added to rules.yaml
[ ] Task names follow naming convention (STIG | ID | V-key | Severity | Description)
[ ] Tags applied (STIG ID, V-key, severity, CCI)
[ ] FQCNs used for all modules
[ ] check_mode supported in evaluate tasks
[ ] Idempotent remediation
[ ] no_log on sensitive values
[ ] argument_specs.yml updated for new variables
[ ] Molecule scenario added (converge + verify, pass + fail)
[ ] Changelog fragment in changelogs/fragments/
[ ] Report template updated for new rules
```

## External References

- **Jira**: ANSTRAT-1907 — Feature epic for this collection
- **STIG Viewer**: https://www.stigviewer.com/stigs
- **STIG Manager**: https://github.com/NUWCDIVNPT/stig-manager
- **DISA STIG Library**: https://public.cyber.mil/stigs/
- **Ansible Validated Content**: https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.3/html/managing_red_hat_certified_and_ansible_galaxy_collections_in_automation_hub/assembly-validated-content
- **Existing L2S STIG reference**: /Users/gnalawad/Documents/projects/network/github/STIG-CISCO-IOS-XE-L2S
- **DISA Ansible content**: /Users/gnalawad/Documents/projects/network/context/jira/attachements/
