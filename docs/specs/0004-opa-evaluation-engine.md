# SPEC-0004: OPA Evaluation Engine

## Goal

Add OPA as an optional evaluation engine alongside the native Ansible filter plugin engine. Enable STIG rules to be written as Rego policies with a documented input schema, supporting both built-in and custom policies.

## Scope

**Included:** OPA lookup plugin, `normalize_config` filter, Rego policies for L2S STIG, JSON Schema for input, engine dispatch in evaluate role.

**Excluded:** OPA server deployment/management, STIG Manager OPA integration, non-IOS platforms (deferred).

## Design

### Engine configuration

```yaml
compliance_evaluate:
  engine: native       # default: Ansible tasks + filter plugins
  # engine: opa        # alternative: Rego policies + opa binary/server
  cat1: true
  cat2: true
  cat3: true
  opa:
    mode: binary                           # binary | server
    binary_path: opa                       # path to opa binary (default: PATH)
    server_url: http://localhost:8181      # OPA server URL (server mode)
    policy_dir: ""                         # override built-in policies
    policy_dirs: []                        # additional policy directories
    schema_validation: true                # validate input against JSON schema
```

### Evaluate role dispatch

```yaml
# roles/evaluate/tasks/main.yaml
- name: Include native evaluation engine
  ansible.builtin.include_tasks:
    file: "{{ compliance.framework }}/{{ evaluate_platform }}/main.yaml"
  when: compliance_evaluate.engine | default('native') == 'native'

- name: Include OPA evaluation engine
  ansible.builtin.include_tasks:
    file: engines/opa.yaml
  when: compliance_evaluate.engine | default('native') == 'opa'
```

### OPA engine task flow

```yaml
# roles/evaluate/tasks/engines/opa.yaml

- name: Gather full running configuration
  cisco.ios.ios_command:
    commands:
      - "show running-config"
  register: _evaluate_running_config

- name: Normalize config to structured JSON
  ansible.builtin.set_fact:
    evaluate_device_state: >-
      {{ _evaluate_running_config.stdout[0]
         | network.compliance.normalize_config(platform=evaluate_platform) }}

- name: Evaluate against STIG policies via OPA
  ansible.builtin.set_fact:
    stig_results: >-
      {{ lookup('network.compliance.opa',
           input=evaluate_device_state,
           policy_dir=_evaluate_policy_dir,
           query='data.stig.' ~ evaluate_platform ~ '.stig_results',
           mode=compliance_evaluate.opa.mode | default('binary'),
           binary_path=compliance_evaluate.opa.binary_path | default('opa'),
           server_url=compliance_evaluate.opa.server_url | default('')) }}
```

### Plugins

#### `normalize_config` filter plugin

Parses platform CLI `show run` output into the documented JSON schema.

```yaml
# Input: raw CLI text from show running-config
# Output: structured JSON matching policies/schemas/ios_xe_l2s.json

device_state: "{{ show_run_output | network.compliance.normalize_config(platform='ios') }}"
```

Output structure:

```json
{
  "device_info": {
    "hostname": "switch01"
  },
  "interfaces": {
    "GigabitEthernet0/1": {
      "mode": "access",
      "access_vlan": 10,
      "bpduguard": true,
      "dot1x": true,
      "storm_control": {"broadcast": "10.00", "unicast": "10.00"},
      "service_policy": "QOS_POLICY_SWITCHPORT",
      "nonegotiate": false
    }
  },
  "global": {
    "dhcp_snooping": {"enabled": true, "vlans": [2, 4, 5, 6, 7, 8, 11]},
    "spanning_tree": {"loopguard_default": true, "mode": "rapid-pvst"},
    "udld": {"enabled": true},
    "igmp_snooping": {"enabled": true},
    "vtp": {"mode": "transparent", "password_set": true}
  }
}
```

#### `opa` lookup plugin

Calls OPA binary or server to evaluate Rego policies against input data.

**Binary mode:**

```bash
# What the plugin runs internally:
echo '{"input": <device_state>}' | opa eval \
  -d policies/stig/ios_xe/l2s/ \
  -I 'data.stig.ios_xe.l2s.stig_results' \
  --schema policies/schemas/
```

**Server mode:**

```bash
# What the plugin does internally:
POST http://opa:8181/v1/data/stig/ios_xe/l2s/stig_results
Content-Type: application/json
{"input": <device_state>}
```

**Custom policy support:**

```yaml
# Use external policy library
stig_results: >-
  {{ lookup('network.compliance.opa',
       input=device_state,
       policy_dirs=[
         '/path/to/external-stig-policies',
         '/path/to/my-org-overrides'
       ],
       query='data.stig.ios_xe.l2s.stig_results') }}
```

Multiple `policy_dirs` are passed as `-d <dir>` arguments to `opa eval`. Later directories can override earlier ones.

### Rego policy structure

```text
policies/
├── schemas/
│   ├── ios_xe_l2s.json                  # JSON Schema for normalize_config output
│   └── README.md                        # Schema reference for policy authors
├── stig/
│   └── ios_xe/
│       └── l2s/
│           ├── cat1.rego                # CAT I rules
│           ├── cat2.rego                # CAT II rules
│           ├── cat3.rego                # CAT III rules
│           ├── l2s_complete.rego        # Aggregator — imports cat1/cat2/cat3
│           └── l2s_test.rego            # opa test unit tests
└── examples/
    └── custom_rule.rego                 # Template for custom policy authors
```

### Rego policy pattern

```rego
# METADATA
# title: Cisco IOS-XE L2S STIG — CAT II Rules
# description: CAT II evaluation rules for IOS-XE Layer 2 Switch STIG
# schemas:
#   - input: schema.ios_xe_l2s
package stig.ios_xe.l2s.cat2

import rego.v1

# V-220659: DHCP snooping
default dhcp_snooping_compliant := false

dhcp_snooping_compliant if {
    input.global.dhcp_snooping.enabled == true
}

finding_v220659 := {
    "status": status_v220659,
    "findings": findings_v220659,
    "detail": detail_v220659,
}

status_v220659 := "not_a_finding" if { dhcp_snooping_compliant }
    else := "open"

findings_v220659 := [] if { dhcp_snooping_compliant }
    else := ["DHCP snooping not enabled"]

detail_v220659 := "DHCP snooping is enabled on user VLANs" if { dhcp_snooping_compliant }
    else := "DHCP snooping issue: DHCP snooping not enabled"
```

### Aggregator pattern

```rego
# METADATA
# title: Cisco IOS-XE L2S STIG — Complete Assessment
# schemas:
#   - input: schema.ios_xe_l2s
package stig.ios_xe.l2s

import data.stig.ios_xe.l2s.cat1
import data.stig.ios_xe.l2s.cat2
import data.stig.ios_xe.l2s.cat3

import rego.v1

# Aggregate all findings into stig_results contract
stig_results := object.union(
    object.union(cat1.findings, cat2.findings),
    cat3.findings,
)
```

### JSON Schema for input validation

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Cisco IOS-XE L2S Device State",
  "description": "Normalized device config for STIG evaluation. Produced by normalize_config filter.",
  "type": "object",
  "required": ["interfaces", "global"],
  "properties": {
    "device_info": {
      "type": "object",
      "properties": {
        "hostname": {"type": "string"}
      }
    },
    "interfaces": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "mode": {"type": "string", "enum": ["access", "trunk"]},
          "access_vlan": {"type": "integer"},
          "bpduguard": {"type": "boolean"},
          "dot1x": {"type": "boolean"},
          "storm_control": {"type": "object"},
          "service_policy": {"type": "string"},
          "nonegotiate": {"type": "boolean"}
        }
      }
    },
    "global": {
      "type": "object",
      "properties": {
        "dhcp_snooping": {
          "type": "object",
          "properties": {
            "enabled": {"type": "boolean"},
            "vlans": {"type": "array", "items": {"type": "integer"}}
          }
        },
        "spanning_tree": {
          "type": "object",
          "properties": {
            "loopguard_default": {"type": "boolean"},
            "mode": {"type": "string"}
          }
        },
        "udld": {"type": "object", "properties": {"enabled": {"type": "boolean"}}},
        "igmp_snooping": {"type": "object", "properties": {"enabled": {"type": "boolean"}}},
        "vtp": {
          "type": "object",
          "properties": {
            "mode": {"type": "string"},
            "password_set": {"type": "boolean"}
          }
        }
      }
    }
  }
}
```

## Implementation Phases

### Phase 1: Config normalization

| File | Purpose |
|------|---------|
| `plugins/filter/normalize_config.py` | Parse `show run` to structured JSON |
| `plugins/filter/normalize_config.yml` | YAML sidecar docs |
| `tests/unit/plugins/filter/test_normalize_config.py` | Unit tests with sample `show run` output |

### Phase 2: OPA lookup plugin

| File | Purpose |
|------|---------|
| `plugins/lookup/opa.py` | Call `opa eval` (binary) or OPA server API |
| `plugins/lookup/opa.yml` | YAML sidecar docs |
| `tests/unit/plugins/lookup/test_opa.py` | Unit tests |

### Phase 3: Rego policies + schema

| File | Purpose |
|------|---------|
| `policies/schemas/ios_xe_l2s.json` | JSON Schema for input validation |
| `policies/schemas/README.md` | Schema docs for policy authors |
| `policies/stig/ios_xe/l2s/cat1.rego` | CAT I rules (V-220649) |
| `policies/stig/ios_xe/l2s/cat2.rego` | CAT II rules (V-220650 through V-220666) |
| `policies/stig/ios_xe/l2s/cat3.rego` | CAT III rules (V-220662, V-220663) |
| `policies/stig/ios_xe/l2s/l2s_complete.rego` | Aggregator |
| `policies/stig/ios_xe/l2s/l2s_test.rego` | OPA unit tests |
| `policies/examples/custom_rule.rego` | Example for custom rule authors |

### Phase 4: Engine dispatch

| File | Purpose |
|------|---------|
| `roles/evaluate/tasks/engines/opa.yaml` | OPA engine task flow |
| `roles/evaluate/tasks/main.yaml` | Add engine dispatch |
| `roles/evaluate/defaults/main.yaml` | Add `compliance_evaluate.opa` defaults |

## Acceptance Criteria

- [ ] `normalize_config` produces valid JSON matching the published schema
- [ ] `opa` lookup works in binary mode (calls `opa eval`)
- [ ] `opa` lookup works in server mode (calls OPA REST API)
- [ ] Rego policies produce same `stig_results` contract as native engine
- [ ] `opa test` passes for all Rego policy unit tests
- [ ] Engine is configurable via `compliance_evaluate.engine`
- [ ] Custom policies validated against JSON schema before evaluation
- [ ] `tox -e ci` passes with both engines
- [ ] Remediate and report roles work unchanged with OPA-produced results

## Dependencies

- OPA binary (`opa`) — optional, only needed when `engine: opa`
- No new Python dependencies (uses `subprocess` for binary, `urllib` for server)
