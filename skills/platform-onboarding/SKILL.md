---
name: platform-onboarding
description: >-
  Add support for a new network OS platform to the network.compliance collection.
  Use when extending STIG compliance coverage to a device type not yet supported.
  Currently supports Cisco IOS/IOS-XE and Juniper JunOS. Covers scan, evaluate,
  remediate, and report roles.
license: GPL-3.0-or-later
compatibility: Requires knowledge of the target platform's Ansible collection and CLI/API.
metadata:
  author: network-compliance-team
  version: "1.0"
---

# Platform Onboarding

## When to use this skill

Use this skill when:
- Adding a new network OS (e.g., `cisco.nxos`, `arista.eos`)
- The collection already supports at least one platform and you're extending to another
- You have access to the target platform's Ansible collection documentation

## Prerequisites

1. The platform's Ansible collection is available (e.g., `arista.eos`)
2. You know the `ansible_network_os` value (e.g., `arista.eos.eos`)
3. You have a reference STIG guide for the platform (from public.cyber.mil)
4. You understand the platform's CLI syntax and resource modules

## Step-by-step process

### Step 1: Update collection dependencies

Add the platform collection to `galaxy.yml`:

```yaml
dependencies:
  arista.eos: ">=9.0.0"   # Add new platform
```

### Step 2: Add scan role support

Create `roles/scan/tasks/<platform>.yaml`:

```yaml
# roles/scan/tasks/eos.yaml
- name: Gather EOS device facts
  arista.eos.eos_facts:
    gather_subset:
      - interfaces
      - config
  register: _scan_facts

- name: Classify interfaces
  ansible.builtin.set_fact:
    compliance_access_ports: >-
      {{ _scan_facts.ansible_facts.ansible_net_interfaces
         | dict2items
         | selectattr('value.mode', 'equalto', 'access')
         | list }}
    compliance_trunk_ports: >-
      {{ _scan_facts.ansible_facts.ansible_net_interfaces
         | dict2items
         | selectattr('value.mode', 'equalto', 'trunk')
         | list }}
```

Update `roles/scan/tasks/main.yaml` to include the new platform:

```yaml
- name: Include platform-specific scan tasks
  ansible.builtin.include_tasks:
    file: "{{ compliance_platform }}.yaml"
```

### Step 3: Create evaluate task structure

```bash
mkdir -p roles/evaluate/tasks/stig/<platform>/
```

Create the severity files:
- `roles/evaluate/tasks/stig/<platform>/main.yaml` — includes cat1, cat2, cat3
- `roles/evaluate/tasks/stig/<platform>/cat1.yaml` — High severity rules
- `roles/evaluate/tasks/stig/<platform>/cat2.yaml` — Medium severity rules
- `roles/evaluate/tasks/stig/<platform>/cat3.yaml` — Low severity rules

### Step 4: Create platform-specific variables

Add `roles/evaluate/vars/stig/<platform>.yaml` with golden baseline configs:

```yaml
# Platform-specific expected configurations
eos_stig_baselines:
  ssh_version: 2
  password_min_length: 15
  login_banner: |
    You are accessing a U.S. Government (USG) Information System...
```

### Step 5: Create remediate task structure

Mirror the evaluate structure:

```bash
mkdir -p roles/remediate/tasks/stig/<platform>/
mkdir -p roles/remediate/templates/stig/<platform>/
```

### Step 6: Map STIG rules to platform modules

Create a reference mapping in `skills/platform-onboarding/references/<platform>-module-map.md`:

| STIG Control Area | Platform Module | Notes |
|-------------------|-----------------|-------|
| Interface config | `arista.eos.eos_interfaces` | Resource module |
| AAA/Authentication | `arista.eos.eos_config` | No resource module |
| Logging | `arista.eos.eos_logging_global` | Resource module |
| NTP | `arista.eos.eos_ntp_global` | Resource module |
| SSH | `arista.eos.eos_config` | Lines-based config |

**Prefer resource modules** over `_config` + `_command` where available.

### Step 7: Update argument_specs.yml

Add platform-specific options to each role's `meta/argument_specs.yml`.

### Step 8: Add Molecule scenarios

Create Molecule scenarios for the new platform:
- `extensions/molecule/scan_<platform>/` — converge.yml, verify.yml, molecule.yml
- `extensions/molecule/evaluate_stig_<platform>/` — converge.yml, verify.yml, molecule.yml

Use the `default` (delegated) driver with platform-specific inventory. See the
`compliance-testing` skill for detailed Molecule patterns.

### Step 9: Update documentation

- Update collection `README.md` supported platforms table
- Update `AGENTS.md` supported platforms table
- Add platform to `galaxy.yml` tags

## Platform-specific notes

### Cisco IOS / IOS-XE (supported)
- Uses `cisco.ios` collection
- CLI-based: `cisco.ios.ios_command`, `cisco.ios.ios_config`
- Resource modules: `ios_interfaces`, `ios_l2_interfaces`, `ios_logging_global`
- STIG variants: NDM, RTR, L2S

### Juniper JunOS (supported)
- Uses `junipernetworks.junos` collection
- NETCONF-based: `junipernetworks.junos.junos_config`
- Resource modules: `junos_interfaces`, `junos_logging_global`
- Configuration is hierarchical XML/set format
- Uses `commit confirmed` for safe changes

## Checklist

```text
[ ] Collection dependency added to galaxy.yml
[ ] Scan tasks created for the platform
[ ] Evaluate task structure (main, cat1, cat2, cat3)
[ ] Platform-specific variables and baselines
[ ] Remediate task structure mirroring evaluate
[ ] Remediation templates (Jinja2)
[ ] Module mapping documented
[ ] argument_specs.yml updated
[ ] Molecule scenarios created (scan + evaluate)
[ ] README.md and AGENTS.md updated
[ ] Changelog fragment added
```
