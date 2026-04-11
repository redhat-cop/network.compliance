# ADR-0002: Conventions and Data Model

## Status

Accepted

## Context

STIG controls have multiple identifiers. Ansible has a flat variable namespace. Without conventions, task output is untraceable, variables collide, and contributors produce inconsistent code. The collection must also support adding new frameworks (CIS) and platforms (JunOS, EOS) without restructuring variables.

## Decision

### Rule Metadata

Rule metadata stored per platform and severity in `evaluate/vars/stig/<platform>/catN.yaml`, keyed by V-key:

```yaml
stig_rules:
  V-220649:
    stig_id: CISC-L2-000020
    rule_id: SV-220649r863283
    severity: cat1
    srg_id: SRG-NET-000148-L2S-000015
    cci: CCI-000044
    title: "The Cisco switch must authenticate all endpoint devices..."
    check_content: |
      Review the switch configuration...
    fix_text: |
      Configure 802.1x on all access switch ports...
    platforms: [ios, junos]
```

### Task Naming

```yaml
- name: >-
    STIG | CISC-L2-000020 | V-220649 | CAT-I |
    Verify 802.1x authentication on access ports
```

### Tagging

Every task carries all STIG identifiers as tags: STIG ID, V-key, Rule ID, severity (`cat1`), CCI. Enables `--tags cat1` or `--tags V-220649` filtering.

### Variable Naming and Structure

Hybrid structure — one level of nesting per concern, framework-specific variables in their own namespace.

**Top-level config:**

```yaml
compliance:
  framework: stig
  platform: ios              # derived from ansible_network_os if not set
```

**Per-phase settings** (one dict per action, easy to override in inventory):

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
  format: cklb               # cklb, xccdf, both
  output_dir: /tmp/compliance_reports

compliance_stigmanager:
  enabled: false
  url: ""
  collection_id: ""
  token: ""                  # no_log: true in argument_specs
  dryrun: false
```

**Framework-specific data** (namespaced by framework, supports adding CIS without collision):

```yaml
stig_controls:               # per-rule config, keyed by V-key
  V-220649:
    run: true
    auth_hostmode: single-host

stig_results: {}             # populated by evaluate, consumed by remediate + report
```

**Scan output** (set by scan role via `set_fact`):

```yaml
compliance_access_ports: []
compliance_trunk_ports: []
compliance_voice_ports: []
```

These use the `compliance_` prefix (not `scan_`) because they are the collection's cross-role
public interface consumed by evaluate, remediate, and report. Tasks use
`# noqa: var-naming[no-role-prefix]` to suppress the ansible-lint role prefix rule.

**Role-internal variables** (prefixed with role name):

```yaml
scan_platform                # resolved platform name within scan role
scan_all_l2_ports            # intermediate fact gathering within scan role
evaluate_platform            # resolved platform name within evaluate role
```

**Temporary variables** (prefixed with `_`, never set by users):

```yaml
_scan_l2_facts               # registered command output (register targets are exempt from lint)
_eval_access_8021x           # registered command output
```

**Adding a new framework** means adding `cis_controls` and `cis_results` — no collision with `stig_*`, no restructuring:

```yaml
compliance:
  framework: cis

cis_controls: {}
cis_results: {}
```

### Validation

Fixed variables are validated by role `argument_specs.yml` with full type/choice/suboption checking. Framework-specific dicts (`stig_controls`, `stig_results`) have dynamic keys (V-keys) — their nested structure is enforced by the `stig_result` and `evaluate_results` filter plugins at write time.

### File Conventions

- `.yaml` extension (not `.yml`), `.j2` for templates. Exception: `galaxy.yml` (required by ansible-galaxy tooling)
- FQCNs for all modules (`cisco.ios.ios_config`, not `ios_config`)
- 160 character max line length

For a complete walkthrough of how a DISA STIG rule maps to these conventions, see `.agents/skills/stig-rule-development/SKILL.md`.

## Consequences

- Task output is self-documenting — every line maps to a DISA control.
- Inventory overrides are simple: `compliance_evaluate: { cat1: false }`.
- Framework-specific variables use their own namespace — no collision when adding CIS.
- Internal `_` prefix signals "do not override" to users.
- Verbose tags add boilerplate but enable granular execution.
