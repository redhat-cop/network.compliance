---
name: stig-rule-development
description: >-
  Implement a new STIG rule in the network.compliance collection. Use when adding
  evaluation, remediation, or reporting for a specific STIG V-key across supported
  platforms (Cisco IOS/IOS-XE, Juniper JunOS). Covers the full lifecycle from
  rule metadata to integration test.
license: GPL-3.0-or-later
compatibility: Requires ansible-lint, ansible-test, and access to network device labs or mocks.
metadata:
  author: network-compliance-team
  version: "1.0"
---

# STIG Rule Development

## When to use this skill

Use this skill when:
- Adding a new STIG rule (V-key) to the collection
- Porting an existing STIG check from the L2S or DISA reference implementations
- Extending an existing rule to a new platform

## Prerequisites

Before starting, gather:
1. The STIG rule's **V-key** (e.g., V-220649)
2. The **STIG ID** (e.g., CISC-L2-000020)
3. The **Rule ID with revision** (e.g., SV-220649r863283)
4. The **severity category** (CAT-I, CAT-II, CAT-III)
5. The **SRG ID** (e.g., SRG-NET-000148-L2S-000015)
6. The **CCI** (e.g., CCI-000044)
7. The **check content** from the STIG guide (what to verify)
8. The **fix text** from the STIG guide (how to remediate)
9. The target **platform** (ios, eos, junos)

## Step-by-step process

### Step 1: Add rule metadata

Add the rule to `roles/evaluate/vars/stig/rules.yaml`:

```yaml
stig_rules:
  V-220649:
    stig_id: CISC-L2-000020
    rule_id: SV-220649r863283
    severity: cat1
    srg_id: SRG-NET-000148-L2S-000015
    cci: CCI-000044
    title: "The Cisco switch must authenticate all endpoint devices before establishing a network connection using bidirectional authentication"
    check_content: |
      Review the switch configuration to verify 802.1x
      authentication is configured on all access switch ports...
    fix_text: |
      Configure 802.1x on all access switch ports...
    platforms:
      - ios
      - junos
```

### Step 2: Add default variables

Add user-configurable variables to `roles/evaluate/defaults/main.yaml`:

```yaml
stig_controls:
  V-220649:
    run: true
    # Platform-specific parameters
    auth_hostmode: "single-host"
```

Update `roles/evaluate/meta/argument_specs.yml` to document the new variables.

### Step 3: Create evaluation task

Add the check to the appropriate severity file, e.g., `roles/evaluate/tasks/stig/ios/cat1.yaml`:

```yaml
- name: >-
    STIG | CISC-L2-000020 | V-220649 | CAT-I |
    Verify 802.1x authentication on access ports
  when: stig_controls['V-220649'].run | default(false)
  tags:
    - CISC-L2-000020
    - V-220649
    - SV-220649r863283
    - cat1
    - CCI-000044
  block:
    - name: Gather interface configuration
      cisco.ios.ios_command:
        commands:
          - "show run int {{ item.name }}"
      loop: "{{ compliance_access_ports }}"
      register: _eval_access_8021x

    - name: Identify non-compliant interfaces
      ansible.builtin.set_fact:
        _v220649_findings: >-
          {{ _eval_access_8021x.results
             | rejectattr('stdout.0', 'search', 'authentication port-control auto')
             | map(attribute='item.name')
             | list }}

    - name: Set evaluation result
      ansible.builtin.set_fact:
        stig_results: >-
          {{ stig_results | default({}) | combine({
               'V-220649': {
                 'status': ('not_a_finding' if _v220649_findings | length == 0 else 'open'),
                 'findings': _v220649_findings,
                 'detail': ('All access ports have 802.1x configured'
                            if _v220649_findings | length == 0
                            else 'Non-compliant interfaces: ' ~ _v220649_findings | join(', '))
               }
             }) }}
```

**Key patterns:**
- Use `block` to group related tasks
- Register findings in `stig_results` dict (keyed by V-key)
- Status is `not_a_finding` (pass) or `open` (fail)
- Include finding details for the report
- Prefix internal variables with `_` to avoid namespace collisions

### Step 4: Create golden baseline template (if using fact_diff)

For rules that compare full configuration blocks, create a template at
`roles/evaluate/templates/stig/ios/v220649_expected.j2`:

```jinja2
interface {{ interface_name }}
 authentication port-control auto
 dot1x pae authenticator
 authentication host-mode {{ stig_controls['V-220649'].auth_hostmode }}
```

Use with `ansible.utils.fact_diff` in the evaluation task.

### Step 5: Create remediation task

Add to `roles/remediate/tasks/stig/ios/cat1.yaml`:

```yaml
- name: >-
    STIG | CISC-L2-000020 | V-220649 | CAT-I |
    Configure 802.1x authentication on access ports
  when:
    - stig_controls['V-220649'].run | default(false)
    - stig_results['V-220649'].status | default('not_reviewed') == 'open'
  tags:
    - CISC-L2-000020
    - V-220649
    - cat1
  cisco.ios.ios_config:
    src: "stig/ios/remediate_v220649.j2"
    save_when: changed
```

**Key patterns:**
- Only remediate if evaluation found the rule `open`
- Use `save_when: changed` (not `always`) for idempotency
- Reference remediation template

### Step 6: Create remediation template

At `roles/remediate/templates/stig/ios/remediate_v220649.j2`:

```jinja2
{% for port in compliance_access_ports %}
interface {{ port.name }}
 authentication port-control auto
 dot1x pae authenticator
 authentication host-mode {{ stig_controls['V-220649'].auth_hostmode }}
{% endfor %}
```

### Step 7: Update report template

Add the rule to `roles/report/templates/stig/stig_viewer.j2` in the rules array:

```json
{
  "group_id": "V-220649",
  "rule_id": "SV-220649r863283",
  "stig_id": "CISC-L2-000020",
  "severity": "high",
  "status": "{{ stig_results['V-220649'].status | default('not_reviewed') }}",
  "finding_details": "{{ stig_results['V-220649'].detail | default('') }}",
  ...
}
```

### Step 8: Write Molecule scenario

Create or update a Molecule scenario under `extensions/molecule/`:

**converge.yml** — `extensions/molecule/evaluate_stig_ios/converge.yml`:
```yaml
- name: Converge — Evaluate V-220649 on IOS
  hosts: stig_targets
  gather_facts: false
  vars:
    compliance_framework: stig
    compliance_platform: ios
    stig_controls:
      V-220649:
        run: true
  roles:
    - network.compliance.evaluate
```

**verify.yml** — `extensions/molecule/evaluate_stig_ios/verify.yml`:
```yaml
- name: Verify — V-220649 evaluation results
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Assert V-220649 was evaluated
      ansible.builtin.assert:
        that:
          - stig_results['V-220649'].status in ['not_a_finding', 'open']
          - stig_results['V-220649'].detail is defined
        fail_msg: "V-220649 was not evaluated correctly"
```

### Step 9: Run quality checks

```bash
# Lint the new files
tox -e lint

# Run sanity checks
ansible-test sanity -v --docker default

# Run the Molecule scenario
molecule test -s evaluate_stig_ios
```

## Checklist

Before submitting:

```text
[ ] Rule metadata in evaluate/vars/stig/rules.yaml
[ ] Default variables in evaluate/defaults/main.yaml
[ ] argument_specs.yml updated
[ ] Evaluation task with correct naming and tags
[ ] Golden baseline template (if using fact_diff)
[ ] Remediation task (conditional on evaluation result)
[ ] Remediation template (Jinja2)
[ ] Report template updated
[ ] Molecule scenario (converge.yml + verify.yml)
[ ] check_mode works for evaluation
[ ] Remediation is idempotent (molecule idempotence step passes)
[ ] no_log on sensitive values
[ ] Changelog fragment added
```

## Reference implementations

- **L2S STIG (3-phase)**: `/Users/gnalawad/Documents/projects/network/github/STIG-CISCO-IOS-XE-L2S`
- **DISA NDM Router (single-role)**: `/Users/gnalawad/Documents/projects/network/github/cisco_ios-xe_router_ndm_stig`
- **DISA Cisco/Juniper/PaloAlto**: `/Users/gnalawad/Documents/projects/network/context/jira/attachements/`
