# Ansible Collection: network.compliance

> **This project is under active development and not ready for consumption. Expect unstable or breaking changes.**

## What is this collection?

This is an [Ansible Validated Content](https://access.redhat.com/articles/ansible-automation-platform-certified-content) collection that automates STIG (Security Technical Implementation Guide) compliance evaluation and remediation for network devices.

**Validated content** is a reference implementation — it provides production-quality roles, plugins, and playbooks that demonstrate best practices for automating compliance workflows with Ansible. Partners and vendors can use this as a baseline to build their own customizations, extend platform support, or learn from the patterns used here. See the [Ansible Validated Content documentation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.3/html/managing_red_hat_certified_and_ansible_galaxy_collections_in_automation_hub/assembly-validated-content) for more about what validated content means in the Ansible ecosystem.

## Overview

This collection implements a four-phase compliance lifecycle as Ansible roles:

```
scan → evaluate → remediate → report
```

| Role | Purpose | Modifies Device |
|------|---------|-----------------|
| `scan` | Discover device state, classify interfaces | No |
| `evaluate` | Audit configuration against STIG controls | No |
| `remediate` | Apply compliant configurations | Yes |
| `report` | Generate CKLB/XCCDF compliance artifacts | No |

Each phase can run independently. For example, run `evaluate` alone for audit-only workflows, or insert an approval gate between `evaluate` and `remediate` in AAP.

### Supported Platforms

| Platform | `ansible_network_os` | Collection |
|----------|---------------------|------------|
| Cisco IOS / IOS-XE | `cisco.ios.ios` | `cisco.ios` |

### Compliance Frameworks

| Framework | Status | Standard Body |
|-----------|--------|---------------|
| STIG | Active | DISA |

The architecture supports adding additional frameworks (e.g., CIS Benchmarks) and platforms (e.g., Juniper JunOS, Arista EOS, Cisco NX-OS) via the `compliance.framework` and `compliance.platform` variables. See `docs/adr/0001-architecture-and-lifecycle.md` for the extensibility design.

## Installation

### From Automation Hub / Galaxy (released versions)

```bash
ansible-galaxy collection install network.compliance
```

### From source (development)

See the [Contributing Guide](CONTRIBUTING.md) for setting up a local development
environment with editable install.

### Requirements

- ansible-core >= 2.15
- Python packages: `jmespath`, `xmltodict`
- Collection dependencies (installed automatically):
  - `cisco.ios >= 8.0.0`
  - `ansible.netcommon >= 6.0.0`
  - `ansible.utils >= 4.0.0`

## Usage

### Basic Evaluation (Audit Only)

```yaml
- name: STIG compliance audit
  hosts: ios_switches
  gather_facts: false
  vars:
    compliance:
      framework: stig
      platform: ios

  tasks:
    - name: Discover device state
      ansible.builtin.include_role:
        name: network.compliance.scan

    - name: Evaluate STIG compliance
      ansible.builtin.include_role:
        name: network.compliance.evaluate
```

Run in check mode for a read-only audit:

```bash
ansible-playbook site.yaml --check
```

### Full Workflow (Evaluate + Remediate + Report)

```yaml
- name: STIG compliance workflow
  hosts: ios_switches
  gather_facts: false
  vars:
    compliance:
      framework: stig
      platform: ios
    compliance_report:
      format: both
      output_dir: /tmp/compliance_reports

  tasks:
    - name: Phase 1 - Scan
      ansible.builtin.include_role:
        name: network.compliance.scan

    - name: Phase 2 - Evaluate
      ansible.builtin.include_role:
        name: network.compliance.evaluate

    - name: Phase 3 - Remediate
      ansible.builtin.include_role:
        name: network.compliance.remediate

    - name: Phase 4 - Report
      ansible.builtin.include_role:
        name: network.compliance.report
```

### Filtering by Severity

Run only high-severity controls:

```bash
ansible-playbook site.yaml --tags cat1
```

Run a single control:

```bash
ansible-playbook site.yaml --tags V-220649
```

### Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `compliance.framework` | `stig` | Compliance framework |
| `compliance.platform` | (derived) | Target platform, derived from `ansible_network_os` |
| `compliance_evaluate` | `{cat1: true, cat2: true, cat3: true}` | Control which severity levels to evaluate |
| `compliance_remediate` | `{cat1: true, cat2: true, cat3: true}` | Control which severity levels to remediate |
| `compliance_report` | `{format: cklb, output_dir: /tmp/...}` | Report format and output directory |
| `stig_controls` | per-rule toggles | Per-rule config keyed by V-key (e.g., `V-220649: {run: true}`) |

## Report Output

The `report` role generates compliance artifacts consumable by standard STIG tooling:

- **CKLB** (JSON) — importable by [STIG Viewer](https://www.stigviewer.com/stigs)
- **XCCDF** (XML) — importable by [STIG Manager](https://github.com/NUWCDIVNPT/stig-manager) or `stigman-watcher`

## Documentation

Design decisions, research, and specifications are maintained in `docs/`:

```
docs/
├── adr/                                      # Architecture Decision Records
│   ├── 0001-architecture-and-lifecycle.md    # Four-phase model, dispatching, report formats
│   ├── 0002-conventions-and-data-model.md    # Rule metadata, naming, tagging, variables
│   ├── 0003-quality-standards.md             # Validated content, error handling, safety
│   └── template.md
├── research/                                  # Investigation and analysis
│   ├── 0001-stig-standards-and-frameworks.md # STIG data model, framework comparison
│   ├── 0002-coverage-gap-and-existing-content.md  # Gap analysis, DISA content review
│   ├── 0003-l2s-reference-implementation.md  # Patterns extracted from reference impl
│   └── template.md
└── specs/                                     # Feature specifications
    ├── 0001-core-roles.md                    # Scan, evaluate, remediate, report
    ├── 0002-testing-and-ci.md                # Molecule, tox, GitHub Actions
    ├── 0003-packaging-and-deployment.md      # Collection packaging, AAP workflow seeding
    └── template.md
```

## Contributing

See the [Contributing Guide](CONTRIBUTING.md) for development environment setup,
conventions, CI checks, and PR checklist.

## References

- [Ansible Certified and Validated Content](https://access.redhat.com/articles/ansible-automation-platform-certified-content)
- [Ansible Validated Content documentation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.3/html/managing_red_hat_certified_and_ansible_galaxy_collections_in_automation_hub/assembly-validated-content)
- [DISA STIG Library](https://public.cyber.mil/stigs/)
- [STIG Viewer](https://www.stigviewer.com/stigs)
- [STIG Manager](https://github.com/NUWCDIVNPT/stig-manager)
- [Molecule](https://github.com/ansible/molecule)

## License

See [LICENSE](LICENSE) for details.
