# Ansible Collection: network.compliance

> **This project is under active development. APIs, role interfaces, and variable names may introduce breaking changes between releases until `1.0.0` is reached. Pin to a specific version if you depend on this collection.**

Ansible Validated Content collection that automates STIG (Security Technical Implementation Guide) compliance evaluation and remediation for network devices.

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

The architecture supports adding additional frameworks (e.g., CIS Benchmarks) via the `compliance_framework` variable.

## Installation

### From Automation Hub / Galaxy (released versions)

```bash
ansible-galaxy collection install network.compliance
```

### From source (development)

Use [ansible-dev-environment](https://github.com/ansible/ansible-dev-environment) (ade)
for an isolated, editable install with all dependencies:

```bash
git clone https://github.com/redhat-cop/network.compliance.git
cd network.compliance

# Create isolated virtual environment with editable install
ade install -e . --venv .venv

# Activate the environment
source .venv/bin/activate

# Verify the collection is installed
ansible-galaxy collection list | grep network.compliance
```

This symlinks the collection into the virtual environment so code changes
are reflected immediately without reinstalling.

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

### Setting up the development environment

```bash
# Clone the repository
git clone https://github.com/redhat-cop/network.compliance.git
cd network.compliance

# Install ansible-dev-tools (bundles ansible-lint, molecule, tox, pytest, ade, and more)
pip install ansible-dev-tools

# Create isolated virtual environment with collection installed in editable mode
ade install -e . --venv .venv
source .venv/bin/activate

# Verify setup
ansible-galaxy collection list | grep network.compliance
adt --version
```

The `ade install -e .` command:
- Creates a Python virtual environment at `.venv/`
- Installs `ansible-core` and all collection dependencies (`cisco.ios`, `ansible.utils`, etc.)
- Installs Python dependencies from `requirements.txt` (`jmespath`, `xmltodict`)
- Symlinks the collection source so edits are reflected immediately
- Configures `ansible.cfg` for workspace isolation

### Contributing with an AI Agent

This repository supports agentic development via [Agent Skills](https://agentskills.io). Skills are auto-discovered from `.agents/skills/` by Claude Code, Cursor, GitHub Copilot, VS Code, and other compatible tools.

**Before writing code, produce documentation first:**

1. **Research** — investigate the problem space and document findings in `docs/research/NNNN-<topic>.md` (use `docs/research/template.md`)
2. **ADR** — if your change involves an architecture or design decision, record it in `docs/adr/NNNN-<decision>.md` (use `docs/adr/template.md`)
3. **Spec** — write or update a spec in `docs/specs/NNNN-<feature>.md` with goal, design, file manifest, acceptance criteria, and verification steps (use `docs/specs/template.md`)
4. **Review and approve** — get spec approval before implementation begins

**Then implement using the appropriate skill:**

| Task | Skill | Location |
|------|-------|----------|
| Set up dev environment | `dev-environment-setup` | `.agents/skills/dev-environment-setup/SKILL.md` |
| Add a STIG rule | `stig-rule-development` | `.agents/skills/stig-rule-development/SKILL.md` |
| Write tests | `compliance-testing` | `.agents/skills/compliance-testing/SKILL.md` |
| Add a platform | `platform-onboarding` | `.agents/skills/platform-onboarding/SKILL.md` |
| Review a PR | `collection-review` | `.agents/skills/collection-review/SKILL.md` |

### Development Workflow

1. **Research and spec** — document the problem, produce an ADR if needed, write or update a spec
2. **Pick a STIG rule** — identify the V-key, STIG ID, and severity from the [DISA STIG Library](https://public.cyber.mil/stigs/)
3. **Implement** — follow the workflow in `.agents/skills/stig-rule-development/SKILL.md`
4. **Test** — write a Molecule scenario covering both compliant and non-compliant states
5. **Lint** — ensure `tox -e lint` passes before submitting

### Running CI checks locally

```bash
# Auto-fix all lint and format issues
tox -e fix

# Run all CI checks (recommended before pushing)
tox -e ci

# Individual checks
tox -e lint           # ansible-lint
tox -e unit           # unit tests (filter plugins)
tox -e ruff           # Python lint + format
tox -e sanity         # ansible-test sanity (requires Docker)
tox -e gitleaks       # secret scanning
tox -e molecule       # all Molecule scenarios

# Set up pre-commit hooks (runs checks on every commit)
pre-commit install
```

### Conventions

- **File extensions**: `.yaml` for YAML, `.j2` for Jinja2 templates
- **Module references**: always use FQCNs (`cisco.ios.ios_config`, not `ios_config`)
- **Task names**: `STIG | <STIG_ID> | <V-key> | <severity> | <description>`
- **Tags**: every task tagged with STIG ID, V-key, Rule ID, severity, CCI
- **Variables**: `compliance_` prefix for user-facing, `_` prefix for internal
- **Error handling**: `block/rescue` instead of `ignore_errors: true`
- **Sensitive values**: `no_log: true` on passwords, keys, communities
- **Line length**: 160 characters max

### PR Checklist

- [ ] Rule metadata added to `evaluate/vars/stig/rules.yaml`
- [ ] Task names and tags follow conventions
- [ ] FQCNs used for all modules
- [ ] `check_mode` works for evaluate tasks
- [ ] Remediation is idempotent
- [ ] `no_log` on sensitive values
- [ ] `argument_specs.yml` updated
- [ ] Molecule scenario added (pass + fail cases)
- [ ] Changelog fragment in `changelogs/fragments/`
- [ ] Report templates updated for new rules

## References

- [DISA STIG Library](https://public.cyber.mil/stigs/)
- [STIG Viewer](https://www.stigviewer.com/stigs)
- [STIG Manager](https://github.com/NUWCDIVNPT/stig-manager)
- [Ansible Validated Content](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.3/html/managing_red_hat_certified_and_ansible_galaxy_collections_in_automation_hub/assembly-validated-content)
- [Molecule](https://github.com/ansible/molecule)

## License

See [LICENSE](LICENSE) for details.
