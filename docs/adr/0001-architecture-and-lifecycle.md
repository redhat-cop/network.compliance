# ADR-0001: Architecture and Lifecycle

## Status

Accepted

## Context

STIG compliance requires distinct operations against network devices. The Layer 2 Switch (L2S) reference used a 3-phase model but coupling reporting to handlers was fragile. The collection must support multiple network platforms and compliance frameworks without hard-coding platform logic, and integrate with AAP workflows that require approval gates between evaluation and remediation.

## Decision

### Four-Phase Lifecycle

Each phase is a separate Ansible role:

| Phase | Purpose | Mutates Device |
|-------|---------|----------------|
| scan | Discover device state, classify interfaces | No |
| evaluate | Audit against compliance rules (check_mode safe) | No |
| remediate | Apply compliant configurations | Yes |
| report | Generate CKLB/XCCDF artifacts, push to STIG Manager | No |

### Why Roles by Action (Not by Framework)

We considered three role structures:

- **Roles by action** (chosen): `scan`, `evaluate`, `remediate`, `report` as separate roles
- **Roles by framework**: One `stig` role containing all four phases
- **Single role**: One `compliance` role dispatching by framework and action

Roles by action was chosen because AAP workflows need separate job templates per phase to insert approval nodes:

```text
[Scan Job] -> [Evaluate Job] -> [Approval Node] -> [Remediate Job] -> [Report Job]
```

If evaluate and remediate are in the same role, an approval gate between them is impossible without variable-flag workarounds. This is critical for DoD environments where human approval before remediation is mandatory.

Separate roles also enable audit-only mode (run evaluate without remediate) and independent Molecule testing per phase.

### Role Directory Structure

```text
roles/
├── scan/tasks/
│   ├── main.yaml                        # dispatch to <platform>.yaml
│   └── ios.yaml
├── evaluate/tasks/
│   ├── main.yaml                        # dispatch to <framework>/<platform>/
│   ├── stig/ios/{main,cat1,cat2,cat3}.yaml
│   └── cis/ios/...                      # future
├── remediate/tasks/
│   ├── main.yaml
│   ├── stig/ios/{main,cat1,cat2,cat3}.yaml
│   └── cis/ios/...                      # future
└── report/tasks/
    ├── main.yaml
    ├── stig/main.yaml
    └── cis/main.yaml                    # future
```

Adding a framework = adding task directories under existing roles. Adding a platform = adding platform task files. No new roles needed for either.

### Dynamic Platform Dispatching

Roles dispatch to platform-specific task files using variables:

```yaml
- ansible.builtin.include_tasks:
    file: "{{ compliance.framework }}/{{ compliance.platform }}/main.yaml"
```

`compliance.platform` is derived from `ansible_network_os` (e.g., `cisco.ios.ios` -> `ios`).

### Report Formats

Two output formats via `to_cklb` and `to_xccdf` filter plugins:

- **CKLB** (JSON) for DISA STIG Viewer — statuses: `not_a_finding`, `open`, `not_reviewed`
- **XCCDF** (XML, NIST 1.2 spec) for STIG Manager — with `sm:detail` and `sm:resultEngine` namespace extensions

STIG Manager integration via `ansible.builtin.uri` (no custom module).

## Consequences

- Evaluate can run standalone for audit-only workflows.
- AAP workflows can insert approval nodes between any two phases.
- Each role has independent Molecule scenarios — test evaluate without remediate.
- New platforms/frameworks addable without modifying existing files.
- Four roles to maintain, but each is focused and testable.
- Users must include all four roles in their playbook — explicit is better than implicit.
