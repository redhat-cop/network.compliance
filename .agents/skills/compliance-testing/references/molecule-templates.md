# Molecule Templates and Scenario Patterns

## molecule.yaml — Network device testing (delegated driver)

```yaml
---
driver:
  name: default

platforms:
  - name: ios-switch-01
    groups:
      - ios_switches
      - stig_targets

provisioner:
  name: ansible
  inventory:
    hosts:
      all:
        hosts:
          ios-switch-01:
            ansible_host: "${MOLECULE_IOS_HOST:-localhost}"
            ansible_connection: "${MOLECULE_CONNECTION:-ansible.netcommon.network_cli}"
            ansible_network_os: cisco.ios.ios
            ansible_user: "${MOLECULE_IOS_USER:-admin}"
            ansible_password: "${MOLECULE_IOS_PASS:-admin}"
    group_vars:
      stig_targets:
        compliance:
          framework: stig
          platform: ios
  env:
    ANSIBLE_ROLES_PATH: "${MOLECULE_PROJECT_DIRECTORY}/roles"
  config_options:
    defaults:
      gathering: explicit

dependency:
  name: galaxy
  options:
    requirements-file: requirements.yml

scenario:
  test_sequence:
    - dependency
    - syntax
    - create
    - prepare
    - converge
    - idempotence
    - verify
    - destroy
```

## molecule.yaml — Mock/local testing (no real device)

```yaml
---
driver:
  name: default

platforms:
  - name: mock-ios-01
    groups:
      - ios_switches

provisioner:
  name: ansible
  inventory:
    hosts:
      all:
        hosts:
          mock-ios-01:
            ansible_host: localhost
            ansible_connection: local
    group_vars:
      ios_switches:
        compliance:
          framework: stig
          platform: ios
        compliance_access_ports:
          - name: GigabitEthernet0/1
            mode: access
          - name: GigabitEthernet0/2
            mode: access
        compliance_trunk_ports:
          - name: GigabitEthernet0/48
            mode: trunk

scenario:
  test_sequence:
    - dependency
    - syntax
    - converge
    - idempotence
    - verify
```

## converge.yaml — Apply role under test

```yaml
---
- name: Converge - Run STIG evaluation on IOS
  hosts: stig_targets
  gather_facts: false
  vars:
    stig_controls:
      V-220649:
        run: true
        auth_hostmode: single-host
      V-220650:
        run: true
    compliance_evaluate:
      cat1: true
      cat2: true
      cat3: false
  roles:
    - network.compliance.evaluate
```

## verify.yaml — Assert expected results

```yaml
---
- name: Verify - Check STIG evaluation results
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Assert stig_results is populated
      ansible.builtin.assert:
        that:
          - stig_results is defined
          - stig_results | length > 0
        fail_msg: "stig_results was not populated by the evaluate role"

    - name: Assert V-220649 was evaluated
      ansible.builtin.assert:
        that:
          - "'V-220649' in stig_results"
          - stig_results['V-220649'].status in ['not_a_finding', 'open']
        fail_msg: "V-220649 was not evaluated or has invalid status"

    - name: Assert finding details are present for open findings
      ansible.builtin.assert:
        that:
          - stig_results[item].detail is defined
          - stig_results[item].detail | length > 0
      loop: "{{ stig_results | dict2items | selectattr('value.status', 'equalto', 'open') | map(attribute='key') | list }}"
      loop_control:
        label: "{{ item }}"
```

## prepare.yaml — Set up test preconditions

```yaml
---
- name: Prepare - Create a non-compliant device state
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Set mock evaluation results (simulates open findings)
      ansible.builtin.set_fact:
        stig_results:
          V-220649:
            status: open
            findings:
              - GigabitEthernet0/1
              - GigabitEthernet0/2
            detail: "Non-compliant interfaces: GigabitEthernet0/1, GigabitEthernet0/2"
          V-220656:
            status: open
            findings:
              - GigabitEthernet0/1
            detail: "Missing BPDU guard on GigabitEthernet0/1"
```

## Scenario patterns

### Evaluation pass/fail

```yaml
# converge.yaml
- name: Converge - Evaluate non-compliant device
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Run evaluation
      ansible.builtin.include_role:
        name: network.compliance.evaluate
      vars:
        compliance:
          framework: stig
          platform: ios
    - name: Save results
      ansible.builtin.set_fact:
        _noncompliant_results: "{{ stig_results }}"

# verify.yaml
- name: Verify - Non-compliant findings detected
  hosts: stig_targets
  gather_facts: false
  tasks:
    - name: Assert open findings exist
      ansible.builtin.assert:
        that:
          - _noncompliant_results['V-220649'].status == 'open'
          - _noncompliant_results['V-220649'].findings | length > 0
```

### Remediation idempotency

Include `idempotence` in `test_sequence`. Molecule re-runs converge and fails if any task reports `changed`.

### Report format validation

```yaml
# verify.yaml
- name: Verify - CKLB report is valid
  hosts: stig_targets
  tasks:
    - name: Read generated CKLB file
      ansible.builtin.slurp:
        src: "{{ compliance_report.output_dir }}/{{ inventory_hostname }}.cklb"
      register: _cklb_raw
    - name: Parse CKLB JSON
      ansible.builtin.set_fact:
        _cklb: "{{ _cklb_raw.content | b64decode | from_json }}"
    - name: Assert CKLB structure
      ansible.builtin.assert:
        that:
          - _cklb.title is defined
          - _cklb.stigs | length > 0
          - _cklb.target_data.host_name is defined
```

### End-to-end workflow

```yaml
# converge.yaml
- name: Converge - Full STIG compliance workflow
  hosts: stig_targets
  gather_facts: false
  vars:
    compliance:
      framework: stig
      platform: ios
  tasks:
    - ansible.builtin.include_role:
        name: network.compliance.scan
    - ansible.builtin.include_role:
        name: network.compliance.evaluate
    - ansible.builtin.include_role:
        name: network.compliance.remediate
    - ansible.builtin.include_role:
        name: network.compliance.report
```
