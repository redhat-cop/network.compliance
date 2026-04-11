---
name: stig-rule-development
description: >-
  Implement a new STIG rule in the network.compliance collection. Use when adding
  evaluation, remediation, or reporting for a specific STIG V-key across supported
  network platforms. Covers the full lifecycle from rule metadata to integration test.
license: GPL-3.0-or-later
compatibility: Requires ansible-lint, ansible-test, and access to network device labs or mocks.
metadata:
  author: network-compliance-team
  version: "3.0"
---

# STIG Rule Development

## When to use this skill

Use this skill when:
- Adding a new STIG rule (V-key) to the collection
- Porting an existing STIG check from a DISA reference implementation
- Extending an existing rule to a new platform

## Prerequisites

Before starting, gather:
1. The STIG rule's **V-key** (e.g., V-220649)
2. The **STIG ID** (e.g., CISC-L2-000020)
3. The **Rule ID with revision** (e.g., SV-220649r863283)
4. The **severity category** (CAT-I, CAT-II, CAT-III)
5. The **SRG ID** (e.g., SRG-NET-000148-L2S-000015)
6. The **CCI** (e.g., CCI-000044)
7. The **check content** and **fix text** from the STIG guide
8. The target **platform** (ios, eos, junos, nxos, etc.)

## How a DISA STIG rule maps to Ansible

| STIG Field | Example | Ansible Mapping |
|------------|---------|-----------------|
| Group ID (V-Key) | V-220649 | Dict key in `stig_rules` and `stig_results` |
| Rule ID | SV-220649r863283 | `rule_id` in metadata, tag on tasks |
| STIG ID | CISC-L2-000020 | `stig_id` in metadata, tag + task name |
| Severity | CAT I | `severity: cat1`, file placement (cat1.yaml), tag |
| SRG ID | SRG-NET-000148-L2S-000015 | `srg_id` in metadata |
| CCI | CCI-000778 | `cci` in metadata, tag on tasks |
| Check Content | "Review the switch configuration..." | Becomes the **evaluate task** logic |
| Fix Text | "Configure 802.1x on all..." | Becomes the **remediate task** + Jinja2 template |

```text
DISA STIG Rule
├── Identifiers -> evaluate/vars/stig/rules.yaml + task name + task tags
├── Check Content -> evaluate/tasks/stig/<platform>/catN.yaml
├── Fix Text -> remediate/tasks/stig/<platform>/catN.yaml + template
└── Severity -> cat1.yaml / cat2.yaml / cat3.yaml file placement
```

## Variable naming

See `docs/adr/0002-conventions-and-data-model.md` for the full variable structure.

- `compliance.framework` / `compliance.platform` — top-level config
- `compliance_evaluate: { cat1: true, ... }` — phase settings
- `stig_controls` — per-rule config keyed by V-key (`stig_controls['V-220649'].run`)
- `stig_results` — evaluation output keyed by V-key (`stig_results['V-220649'].status`)
- `_` prefix for internal variables (`_eval_access_8021x`)

## Step-by-step process

### Step 1: Add rule metadata to `roles/evaluate/vars/stig/rules.yaml`

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
      Review the switch configuration to verify 802.1x...
    fix_text: |
      Configure 802.1x on all access switch ports...
    platforms:
      - ios
      - junos
```

### Step 2: Add default variables to `roles/evaluate/defaults/main.yaml`

```yaml
stig_controls:
  V-220649:
    run: true
    auth_hostmode: "single-host"
```

Update `roles/evaluate/meta/argument_specs.yml` to document new variables.

### Step 3: Create evaluation task at `roles/evaluate/tasks/stig/<platform>/catN.yaml`

All rules use `<os>_command` for evaluation. The `evaluate_results` filter handles
extracting non-compliant items, building the status dict, and merging into `stig_results`:

```yaml
- name: >-
    STIG | CISC-L2-000020 | V-220649 | CAT-I |
    Verify 802.1x authentication on access ports
  when: stig_controls['V-220649'].run | default(false)
  tags: [CISC-L2-000020, V-220649, SV-220649r863283, cat1, CCI-000044]
  block:
    - name: Check interface configuration
      cisco.ios.ios_command:
        commands:
          - "show run int {{ item.name }}"
      loop: "{{ compliance_access_ports }}"
      register: _eval_access_8021x

    - name: Evaluate 802.1x compliance
      ansible.builtin.set_fact:
        stig_results: >-
          {{ _eval_access_8021x.results | network.compliance.evaluate_results(
               rule_id='V-220649',
               match='authentication port-control auto',
               pass_msg='All access ports have 802.1x configured',
               fail_msg='Non-compliant interfaces: {}',
               results=stig_results) }}
```

**Key patterns:**
- Use `block` to group related tasks under the `when`/`tags` guard
- Use `evaluate_results` filter — one call does check + status + merge
- For the building blocks independently, see [references/evaluation-examples.md](references/evaluation-examples.md)

### Step 4: Create golden baseline template (if using fact_diff)

For rules that compare full config blocks, create a template at
`roles/evaluate/templates/stig/<platform>/vNNNNNN_expected.j2` and use
with `ansible.utils.fact_diff`. See [references/evaluation-examples.md](references/evaluation-examples.md).

### Step 5: Create remediation task at `roles/remediate/tasks/stig/<platform>/catN.yaml`

All rules use `<os>_config` for remediation. Gate on `stig_results[V-key].status == 'open'`:

```yaml
- name: >-
    STIG | CISC-L2-000020 | V-220649 | CAT-I |
    Configure 802.1x authentication on access ports
  when:
    - stig_controls['V-220649'].run | default(false)
    - stig_results['V-220649'].status | default('not_reviewed') == 'open'
  tags: [CISC-L2-000020, V-220649, cat1]
  cisco.ios.ios_config:
    src: "stig/ios/remediate_v220649.j2"
    save_when: changed
```

Use `block/rescue` for lockout-risk operations (802.1x, SSH, AAA).

### Step 6: Create remediation template

At `roles/remediate/templates/stig/<platform>/remediate_vNNNNNN.j2`:

```jinja2
{% for port in compliance_access_ports %}
interface {{ port.name }}
 authentication port-control auto
 dot1x pae authenticator
 authentication host-mode {{ stig_controls['V-220649'].auth_hostmode }}
{% endfor %}
```

### Step 7: Write Molecule scenario

Create `extensions/molecule/evaluate-stig-<platform>/` with `converge.yaml` and `verify.yaml`.
Scenario names follow `<role>-<framework>-<platform>` convention.

### Step 8: Run quality checks

```bash
tox -e lint
ansible-test sanity -v --docker default
molecule test -s evaluate-stig-<platform>
```

## Checklist

```text
[ ] Rule metadata in evaluate/vars/stig/rules.yaml
[ ] Default variables in evaluate/defaults/main.yaml
[ ] argument_specs.yml updated
[ ] Evaluation task using evaluate_results filter with correct naming and tags
[ ] Golden baseline template (if using fact_diff)
[ ] Remediation task (conditional on stig_results status)
[ ] Remediation template (Jinja2)
[ ] Molecule scenario (converge.yaml + verify.yaml)
[ ] check_mode works for evaluation
[ ] Remediation is idempotent
[ ] no_log on sensitive values
[ ] Changelog fragment added
```

## References

- [references/resource-modules.md](references/resource-modules.md) — Cross-platform module table and state reference
- [references/evaluation-examples.md](references/evaluation-examples.md) — Building block filter examples and fact_diff approach
- [DISA STIG Library](https://public.cyber.mil/stigs/)
