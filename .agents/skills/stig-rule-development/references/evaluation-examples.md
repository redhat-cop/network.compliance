# Evaluation Approach Examples

## Standard pattern: `evaluate_results` filter (used for most rules)

All rules use `<os>_command` for evaluation. The `evaluate_results` convenience filter
handles the full pipeline: extract non-compliant items, build status dict, merge into results.

```yaml
- name: Check BPDU Guard on access ports
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

The filter accepts optional `result_key` (default: `stdout.0`) and `item_key` (default: `item.name`)
for non-standard registered output shapes.

## Building blocks: `check_results` and `stig_result` (for custom logic)

When you need the intermediate findings list or have non-standard input:

**`check_results`** — extract non-compliant items from registered command output:

```yaml
{{ _eval.results | network.compliance.check_results(match='bpduguard enable') }}
# -> ['Gi0/2', 'Gi0/5']

# With custom keys
{{ _eval.results | network.compliance.check_results(
     match='ntp server .* prefer',
     result_key='stdout.0',
     item_key='item') }}
```

**`stig_result`** — build status dict from any findings list:

```yaml
{{ my_findings | network.compliance.stig_result(
     pass_msg='All compliant',
     fail_msg='Non-compliant: {}') }}
# -> { status: 'open', findings: ['Gi0/2'], detail: 'Non-compliant: Gi0/2' }
```

## Alternative: `ansible.utils.fact_diff` (config block comparison)

For rules that compare a full config block against a golden baseline template
(e.g., QoS policy-map). Works with any platform.

```yaml
- name: Render expected config
  ansible.builtin.template:
    src: "stig/{{ compliance.platform }}/v220651_qos_expected.j2"
    dest: "/tmp/{{ inventory_hostname }}_qos.cfg"
  delegate_to: localhost

- name: Get running config section
  cisco.ios.ios_command:
    commands:
      - "show running-config | section policy-map"
  register: _qos_running

- name: Compare against golden baseline
  ansible.utils.fact_diff:
    before: "{{ _qos_running.stdout[0] }}"
    after: "{{ lookup('file', '/tmp/' ~ inventory_hostname ~ '_qos.cfg') }}"
  register: _qos_diff
```

## Remediation examples

**Template-based** (most rules):

```yaml
- name: Configure 802.1x on access ports
  when:
    - stig_controls['V-220649'].run | default(false)
    - stig_results['V-220649'].status | default('not_reviewed') == 'open'
  cisco.ios.ios_config:
    src: "stig/ios/remediate_v220649.j2"
    save_when: changed
```

**Inline config** (global settings like UDLD, Loop Guard, IGMP):

```yaml
- name: Enable UDLD globally
  when:
    - stig_controls['V-220665'].run | default(false)
    - stig_results['V-220665'].status | default('not_reviewed') == 'open'
  cisco.ios.ios_config:
    lines:
      - udld enable
    save_when: changed
```
