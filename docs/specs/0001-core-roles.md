# SPEC-0001: Core Roles — Cisco IOS-XE Layer 2 Switch (L2S) STIG (First Platform)

## Goal

Implement the four-phase lifecycle (scan, evaluate, remediate, report) for the Cisco IOS-XE Layer 2 Switch STIG as the first platform in the collection.

## Scope

**Included:** 9 STIG rules (1 CAT I, 6 CAT II, 2 CAT III), collection scaffolding, all four roles for Cisco IOS, CKLB + XCCDF report generation.

**Excluded:** Juniper JunOS, STIG Manager API integration (deferred, optional), CIS Benchmarks.

## STIG Rules

| V-Key | STIG ID | Severity | Control | Remediation |
|-------|---------|----------|---------|-------------|
| V-220649 | CISC-L2-000020 | CAT I | 802.1x authentication on access/voice ports | Template (per-port) |
| V-220650 | CISC-L2-000030 | CAT II | VTP password configured | Inline (`no_log`) |
| V-220651 | CISC-L2-000040 | CAT II | DoS protection via QoS policy | Template (policy-map + per-port) |
| V-220656 | CISC-L2-000100 | CAT II | BPDU Guard on access ports | Template (per-port) |
| V-220657 | CISC-L2-000110 | CAT II | STP Loop Guard enabled globally | Inline (global config) |
| V-220665 | CISC-L2-000190 | CAT II | UDLD enabled globally | Inline (global config) |
| V-220666 | CISC-L2-000200 | CAT II | DTP disabled on trunk ports | Template (per-port) |
| V-220662 | CISC-L2-000160 | CAT III | Storm control on access/voice ports | Template (per-port) |
| V-220663 | CISC-L2-000170 | CAT III | IGMP Snooping enabled globally | Inline (global config) |

## Implementation Phases

### Phase 1: Collection Scaffolding

| File | Purpose |
|------|---------|
| `galaxy.yml` | Collection metadata, deps, version `0.1.0`. Uses `.yml` (ansible-galaxy requires this filename) |
| `meta/runtime.yml` | `requires_ansible: ">=2.15"` |
| `requirements.txt` | `jmespath`, `xmltodict` |
| `changelogs/config.yaml` | antsibull-changelog config |
| `changelogs/fragments/.gitkeep` | Placeholder for changelog fragments |

### Phase 2: Scan Role

| File | Purpose |
|------|---------|
| `roles/scan/tasks/main.yaml` | Derive `scan_platform` from `compliance.platform` or `ansible_network_os`, dispatch to `<platform>.yaml` |
| `roles/scan/tasks/ios.yaml` | `cisco.ios.ios_facts` with `gather_network_resources: [l2_interfaces]`, classify ports |
| `roles/scan/defaults/main.yaml` | Default variable values |
| `roles/scan/meta/argument_specs.yml` | Variable documentation |

Port classification via `set_fact` (in-memory, no file writes):

- `compliance_access_ports` — mode=access, no voice VLAN
- `compliance_voice_ports` — voice VLAN defined
- `compliance_trunk_ports` — mode=trunk

### Phase 3: Evaluate Role

| File | Purpose |
|------|---------|
| `roles/evaluate/vars/stig/ios/cat{1,2,3}.yaml` | Rules per severity with V-key, STIG ID, Rule ID, CCI, title, check/fix text |
| `roles/evaluate/defaults/main.yaml` | `stig_controls` per-rule toggles, `compliance_evaluate: { cat1: true, ... }` |
| `roles/evaluate/meta/argument_specs.yml` | Variable documentation |
| `roles/evaluate/tasks/main.yaml` | Load vars, init `stig_results: {}`, dispatch by framework/platform |
| `roles/evaluate/tasks/stig/ios/main.yaml` | Conditionally include cat1, cat2, cat3 |
| `roles/evaluate/tasks/stig/ios/cat1.yaml` | V-220649 |
| `roles/evaluate/tasks/stig/ios/cat2.yaml` | V-220650, V-220651, V-220656, V-220657, V-220665, V-220666 |
| `roles/evaluate/tasks/stig/ios/cat3.yaml` | V-220662, V-220663 |

**All rules use `<os>_command` for evaluate and `<os>_config` for remediate** — one consistent pattern, one filter chain:

| V-Key | Control | Evaluate | Remediate |
|-------|---------|----------|-----------|
| V-220649 | 802.1x | `ios_command` per port | `ios_config` + template |
| V-220650 | VTP password | `ios_command` | `ios_config` inline, `no_log` |
| V-220651 | QoS policy-map | `ios_command` + `fact_diff` | `ios_config` + template |
| V-220651 | QoS service-policy | `ios_command` per port | `ios_config` + template |
| V-220656 | BPDU Guard | `ios_command` per port | `ios_config` + template |
| V-220657 | STP Loop Guard | `ios_command` | `ios_config` inline |
| V-220665 | UDLD | `ios_command` | `ios_config` inline |
| V-220666 | DTP disabled | `ios_command` per port | `ios_config` + template |
| V-220662 | Storm control | `ios_command` per port | `ios_config` + template |
| V-220663 | IGMP snooping | `ios_command` | `ios_config` inline |

**Standard 2-task pattern per rule** (using `evaluate_results` filter):

```yaml
- name: Check interface configuration
  cisco.ios.ios_command:
    commands: "show run int {{ item.name }}"
  loop: "{{ compliance_access_ports }}"
  register: _eval_bpdu

- name: Evaluate BPDU Guard compliance
  ansible.builtin.set_fact:
    stig_results: >-
      {{ _eval_bpdu.results | network.compliance.evaluate_results(
           rule_id='V-220656',
           match='spanning-tree bpduguard enable',
           pass_msg='All access ports have BPDU Guard',
           fail_msg='Missing BPDU Guard: {}',
           results=stig_results) }}
```

The `evaluate_results` filter handles everything: extract non-compliant items, build the status dict, and merge into the existing `stig_results`.

**Key design:** No handlers, no `combine()`, no ternary logic in tasks. One filter call per rule.

### Phase 3b: Filter Plugins

| File | Purpose |
|------|---------|
| `plugins/filter/compliance.py` | Collection filter plugins |
| `tests/unit/plugins/filter/test_compliance.py` | Unit tests |

Five filter plugins, three layers:

**Building blocks** (usable independently for non-standard cases):

`check_results` — extract non-compliant items from registered command output

```yaml
{{ _eval.results | network.compliance.check_results(match='bpduguard enable') }}
# -> ['Gi0/2', 'Gi0/5']

# Custom keys (defaults: result_key='stdout.0', item_key='item.name')
{{ _eval.results | network.compliance.check_results(
     match='ntp server .* prefer',
     result_key='stdout.0',
     item_key='item') }}
```

`stig_result` — build status/findings/detail dict from any findings list

```yaml
{{ findings | network.compliance.stig_result(
     pass_msg='All compliant',
     fail_msg='Non-compliant: {}') }}
# -> { status: 'open', findings: ['Gi0/2'], detail: 'Non-compliant: Gi0/2' }
```

**Convenience** (combines check + result + merge in one call):

`evaluate_results` — full evaluate pipeline for the standard command-loop pattern

```yaml
{{ _eval.results | network.compliance.evaluate_results(
     rule_id='V-220656',
     match='spanning-tree bpduguard enable',
     pass_msg='All ports have BPDU Guard',
     fail_msg='Missing BPDU Guard: {}',
     results=stig_results) }}
# -> merged stig_results dict with V-220656 added
```

**Report generation:**

`to_cklb` — generate CKLB JSON from `stig_results` + `stig_rules`

```yaml
{{ stig_results | network.compliance.to_cklb(
     rules=stig_rules,
     hostname=inventory_hostname,
     ip_address=ansible_host) }}
```

`to_xccdf` — generate XCCDF XML from `stig_results` + `stig_rules`

```yaml
{{ stig_results | network.compliance.to_xccdf(
     rules=stig_rules,
     hostname=inventory_hostname,
     ip_address=ansible_host) }}
```

### Phase 4: Remediate Role

| File | Purpose |
|------|---------|
| `roles/remediate/defaults/main.yaml` | `compliance_remediate: { cat1: true, ... }` defaults |
| `roles/remediate/meta/argument_specs.yml` | Variable documentation |
| `roles/remediate/tasks/main.yaml` | Validate `stig_results` exists, dispatch |
| `roles/remediate/tasks/stig/ios/main.yaml` | Include cat1/cat2/cat3 conditionally |
| `roles/remediate/tasks/stig/ios/cat1.yaml` | V-220649 remediation |
| `roles/remediate/tasks/stig/ios/cat2.yaml` | V-220650 through V-220666 remediation |
| `roles/remediate/tasks/stig/ios/cat3.yaml` | V-220662, V-220663 remediation |
| `roles/remediate/templates/stig/ios/remediate_v220649.j2` | 802.1x config per access/voice port |
| `roles/remediate/templates/stig/ios/remediate_v220651_qos.j2` | QoS policy-map |
| `roles/remediate/templates/stig/ios/remediate_v220656.j2` | BPDU guard per access/voice port |
| `roles/remediate/templates/stig/ios/remediate_v220662.j2` | Storm control per port |
| `roles/remediate/templates/stig/ios/remediate_v220666.j2` | DTP disable per trunk port |

V-220650 (VTP), V-220657 (Loop Guard), V-220665 (UDLD), V-220663 (IGMP) use inline `ios_config` — no template needed.

**Constraints:**

- Every task gated on `stig_results[V-key].status == 'open'`
- `save_when: changed` on all `ios_config` tasks
- `block/rescue` for V-220649 (802.1x — lockout risk)
- `no_log: true` for V-220650 (VTP password)

### Phase 5: Report Role

| File | Purpose |
|------|---------|
| `roles/report/defaults/main.yaml` | `compliance_report: { format: cklb, output_dir: ... }`, STIG Manager config |
| `roles/report/meta/argument_specs.yml` | Variable documentation |
| `roles/report/tasks/main.yaml` | Load rule metadata, dispatch |
| `roles/report/tasks/stig/main.yaml` | Generate CKLB and/or XCCDF using filter plugins |
| `roles/report/tasks/stig/stigmanager.yaml` | Optional API push via `ansible.builtin.uri` |

Report generation uses `to_cklb` and `to_xccdf` filter plugins instead of Jinja2 templates:

```yaml
- name: Generate CKLB report
  ansible.builtin.copy:
    content: >-
      {{ stig_results | network.compliance.to_cklb(
           rules=stig_rules, hostname=inventory_hostname,
           ip_address=ansible_host) }}
    dest: "{{ compliance_report.output_dir }}/{{ inventory_hostname }}.cklb"
  when: compliance_report.format in ['cklb', 'both']

- name: Generate XCCDF report
  ansible.builtin.copy:
    content: >-
      {{ stig_results | network.compliance.to_xccdf(
           rules=stig_rules, hostname=inventory_hostname,
           ip_address=ansible_host) }}
    dest: "{{ compliance_report.output_dir }}/{{ inventory_hostname }}_xccdf.xml"
  when: compliance_report.format in ['xccdf', 'both']
```

Adding a rule to the appropriate `catN.yaml` file automatically includes it in reports — the filters iterate `stig_rules` dynamically.

### Phase 6: Molecule Testing

See [SPEC-0002](0002-testing-and-ci.md) for scenario structure and CI config.

| Scenario | Tests |
|----------|-------|
| `scan-stig-ios` | Interface classification from mock facts |
| `evaluate-stig-ios` | `stig_results` populated with valid statuses |
| `remediate-stig-ios` | Remediation runs + idempotence check |
| `report-stig-ios` | CKLB JSON structure valid, XCCDF XML well-formed |
| `workflow-stig-ios` | End-to-end: scan, evaluate, remediate, report |

## Phase Dependencies

```text
Phase 1 (scaffolding)
  └── Phase 2 (scan)
        └── Phase 3 (evaluate + filter plugins)
              ├── Phase 4 (remediate)  -- depends on stig_results from evaluate
              └── Phase 5 (report)     -- uses to_cklb/to_xccdf filters
                    └── Phase 6 (molecule) -- requires all roles + plugins
```

## Acceptance Criteria

- [ ] `ansible-galaxy collection build` succeeds
- [ ] `ansible-lint roles/` passes production profile
- [ ] All four roles dispatch by `compliance.framework` and `compliance.platform`
- [ ] Evaluate works in `check_mode`, remediate is idempotent
- [ ] `stig_results` dict populated by evaluate, consumed by remediate and report
- [ ] All 9 rules evaluated and remediable for Cisco IOS
- [ ] CKLB JSON importable by STIG Viewer
- [ ] XCCDF XML follows NIST XCCDF 1.2 spec
- [ ] `argument_specs.yml` for all roles
- [ ] Tags on every task (STIG ID, V-key, severity, CCI)
- [ ] Molecule scenarios pass for all 5 scenarios
- [ ] `no_log` on sensitive values (VTP password, STIG Manager token)

## Verification

```bash
ansible-galaxy collection build          # builds .tar.gz
ansible-lint roles/                      # production profile
yamllint roles/                          # YAML formatting
molecule test -s evaluate-stig-ios       # evaluation works
molecule test -s report-stig-ios          # CKLB/XCCDF generation
```

## Dependencies

- Platform collections: `cisco.ios >=8.0.0`
- `ansible.netcommon >=6.0.0`, `ansible.utils >=4.0.0`
- Python: `jmespath`, `xmltodict`
- Testing: `ansible-dev-tools` (molecule, ansible-lint, yamllint, tox-ansible)

## File Summary

~49 files across 6 phases: scaffolding (5), scan (4), evaluate (8), filter plugins (2), remediate (12), report (5), molecule (15).

Note: All evaluate/remediate tasks use `<os>_command`/`<os>_config` (no resource modules) for consistency. Report uses `to_cklb`/`to_xccdf` filter plugins instead of Jinja2 templates.
