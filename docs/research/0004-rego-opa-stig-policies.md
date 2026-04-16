# RESEARCH-0004: Rego/OPA for STIG Policy Evaluation

## Summary

Investigated using Open Policy Agent (OPA) and Rego policies for STIG compliance evaluation as an alternative to embedding evaluation logic directly in Ansible tasks. The rego_policy_libraries community project provides 363+ production-ready policies across CIS, STIG, NIST, and other frameworks, including patterns specifically for STIG finding objects. This research proposes a separation of concerns: Ansible handles data gathering and remediation, Rego handles policy evaluation.

## Background

Currently, STIG evaluation logic is embedded in Ansible task files using `ios_command` + filter plugins. This works but tightly couples the compliance rules to the automation platform. Moving evaluation logic to Rego policies would:

- Separate "what to check" (policy) from "how to gather data" (Ansible)
- Enable the same policies to be used outside Ansible (CI/CD gates, API checks, drift detection)
- Allow compliance teams to write/review rules without knowing Ansible
- Leverage OPA's policy testing, versioning, and decision logging

## Findings

### Rego Policy Libraries Architecture

The community repo at `rego_policy_libraries` organizes 363+ policies across three axes:

```text
benchmarks/       # CIS, STIG (what to check)
frameworks/       # NIST, SOC2, PCI-DSS (regulatory mapping)
enforcement/      # Ansible, Terraform, K8s (gate validation)
```

### STIG Finding Pattern in Rego

Each STIG rule maps to a structured finding object:

```rego
package stig.ios_xe.l2s

import rego.v1

finding_v220659 := {
    "vuln_id": "V-220659",
    "stig_id": "CISC-L2-000130",
    "rule_id": "SV-220659r928999",
    "severity": "CAT II",
    "cci": "CCI-002385",
    "title": "DHCP snooping must be enabled on all user VLANs",
    "status": status_v220659,
    "fix_text": "Configure ip dhcp snooping and ip dhcp snooping vlan <user-vlans>",
}

default dhcp_snooping_enabled := false

dhcp_snooping_enabled if {
    input.running_config.dhcp_snooping.enabled == true
}

status_v220659 := "Not_a_Finding" if { dhcp_snooping_enabled }
    else := "Open"
```

### Input Contract for Network Devices

Ansible gathers device state and converts it to a JSON input for OPA:

```json
{
  "device_info": {
    "hostname": "switch01",
    "platform": "ios",
    "network_os": "cisco.ios.ios"
  },
  "running_config": {
    "dhcp_snooping": {
      "enabled": true,
      "vlans": [2, 4, 5, 6, 7, 8, 11]
    },
    "interfaces": {
      "GigabitEthernet0/1": {
        "mode": "access",
        "bpduguard": true,
        "storm_control": {"broadcast": "10.00"}
      }
    },
    "spanning_tree": {
      "loopguard_default": true
    },
    "udld": {
      "enabled": true
    }
  }
}
```

### Proposed Architecture: Separation of Concerns

```text
┌─────────────────────────────────────────────────────────────┐
│                    Ansible Playbook                          │
│                                                             │
│  ┌──────────┐   ┌───────────────┐   ┌───────────────────┐  │
│  │  Scan    │──>│   Evaluate    │──>│    Remediate       │  │
│  │  (gather)│   │   (OPA call)  │   │   (ios_config)     │  │
│  └──────────┘   └───────┬───────┘   └───────────────────┘  │
│                         │                                    │
│                         ▼                                    │
│                 ┌───────────────┐                            │
│                 │   OPA Server  │                            │
│                 │   or          │                            │
│                 │   opa eval    │                            │
│                 └───────┬───────┘                            │
│                         │                                    │
│                         ▼                                    │
│                 ┌───────────────┐                            │
│                 │ Rego Policies │                            │
│                 │ (STIG rules)  │                            │
│                 └───────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

**Phase 1 (scan):** Ansible gathers device config via `ios_command`/`ios_facts`, normalizes into JSON.

**Phase 2 (evaluate):** Instead of per-rule Ansible tasks with filter plugins, POST the JSON to OPA. OPA evaluates all Rego policies and returns structured findings.

**Phase 3 (remediate):** Ansible reads OPA findings, applies fixes for open rules using `ios_config` + templates (unchanged from current approach).

**Phase 4 (report):** `to_cklb`/`to_xccdf` filter plugins consume the OPA findings (same output contract as current `stig_results`).

### How the Evaluate Role Would Change

**Current approach** (Ansible tasks + filter plugins):

```yaml
- name: Check DHCP snooping configuration
  cisco.ios.ios_command:
    commands:
      - "show run | include ip dhcp snooping"
  register: _evaluate_dhcp_snooping

- name: Evaluate DHCP snooping compliance
  ansible.builtin.set_fact:
    stig_results: >-
      {{ stig_results | default({}) | combine({
           'V-220659': ([] if "ip dhcp snooping" in _evaluate_dhcp_snooping.stdout[0]
             else ["DHCP snooping not enabled"])
           | network.compliance.stig_result(...) }) }}
```

**Proposed approach** (Ansible gather + OPA evaluate):

```yaml
# Phase 1: Gather all config in one pass
- name: Gather device configuration
  cisco.ios.ios_command:
    commands:
      - "show running-config"
  register: _scan_running_config

# Phase 2: Normalize to JSON and evaluate via OPA
- name: Normalize config to structured data
  ansible.builtin.set_fact:
    device_state: "{{ _scan_running_config.stdout[0] | network.compliance.normalize_config }}"

- name: Evaluate against STIG policies via OPA
  ansible.builtin.uri:
    url: "{{ opa_url }}/v1/data/stig/ios_xe/l2s/compliance_report"
    method: POST
    body_format: json
    body:
      input: "{{ device_state }}"
  register: _opa_result

- name: Set stig_results from OPA response
  ansible.builtin.set_fact:
    stig_results: "{{ _opa_result.json.result.findings }}"
```

### New Plugin Requirements

| Plugin | Type | Purpose |
|--------|------|---------|
| `normalize_config` | filter | Parse CLI `show run` output into structured JSON for OPA input |
| `opa_evaluate` | lookup or module | Call OPA (server or local binary) with device state, return findings |

### Policy File Structure for Network STIG

```text
policies/stig/
├── ios_xe/
│   ├── l2s/
│   │   ├── cat1.rego           # CAT I rules (V-220649)
│   │   ├── cat2.rego           # CAT II rules (V-220650, V-220656, etc.)
│   │   ├── cat3.rego           # CAT III rules (V-220662, V-220663)
│   │   ├── l2s_complete.rego   # Aggregator — imports cat1/cat2/cat3
│   │   └── l2s_test.rego       # Unit tests
│   ├── ndm/
│   │   ├── cat1.rego
│   │   └── ...
│   └── rtr/
│       └── ...
├── junos/                       # Future
└── eos/                         # Future
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **Separation of concerns** | Policy authors write Rego, automation engineers write Ansible |
| **Reusability** | Same policies work with Ansible, Terraform, CI/CD, API |
| **Testability** | `opa test` runs policy unit tests without devices |
| **Composability** | Aggregate across frameworks (STIG + CIS + NIST) |
| **Auditability** | OPA decision logs provide audit trail |
| **Speed** | OPA evaluates hundreds of rules in milliseconds |

### Trade-offs

| Trade-off | Impact |
|-----------|--------|
| **Additional dependency** | OPA server or binary must be available |
| **Config normalization** | Need a `normalize_config` plugin to convert CLI output to structured JSON |
| **Two languages** | Contributors need Rego for policies + YAML for Ansible |
| **Deployment complexity** | OPA server management in production |
| **Offline mode** | Need fallback when OPA is unreachable |

### Integration Options

| Option | How it works | Dependency |
|--------|-------------|------------|
| **OPA server** | POST to `http://opa:8181/v1/data/...` via `ansible.builtin.uri` | Running OPA container |
| **OPA binary** | `opa eval -d policies/ -i input.json 'data.stig.ios_xe.l2s'` via `ansible.builtin.command` | OPA binary on control node |
| **Embedded** | Python `opa` library in a custom Ansible module | Python package |
| **Hybrid** | Current filter plugins as default, OPA as optional upgrade | Optional |

## Recommendations

1. **Start with hybrid approach** — keep current filter plugins as the default evaluation path, add OPA as an optional alternative for users who want policy-as-code separation.

2. **Build `normalize_config` filter first** — this is needed regardless of OPA. Converting CLI output to structured JSON is valuable on its own (improves testability, enables fact_diff comparisons).

3. **Write STIG L2S policies in Rego** — port the existing 9+1 rules to Rego as a proof of concept. Use the finding object pattern from the rego_policy_libraries STIG examples.

4. **Keep the same `stig_results` contract** — OPA findings should produce the same `{status, findings, detail}` structure so remediate and report roles work unchanged.

5. **Ship policies in the collection** — include `.rego` files under `policies/` in the collection tarball. Users can load them into their own OPA instance or use the local binary.

## References

- [rego_policy_libraries](https://github.com/ansible/rego_policy_libraries) — 363+ production-ready OPA policies
- [Open Policy Agent](https://www.openpolicyagent.org/)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [OPA Ansible Integration](https://www.openpolicyagent.org/docs/latest/integration/)
