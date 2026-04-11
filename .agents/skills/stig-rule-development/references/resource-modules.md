# Resource Modules Reference

## Cross-platform resource module availability

All Ansible network resource modules support `state: gathered` which returns
structured data — no CLI parsing or regex needed.

| Control Area | Cisco IOS | Juniper JunOS | Arista EOS | Cisco NX-OS |
|-------------|-----------|---------------|------------|-------------|
| L2 interfaces | `cisco.ios.ios_l2_interfaces` | `junipernetworks.junos.junos_l2_interfaces` | `arista.eos.eos_l2_interfaces` | `cisco.nxos.nxos_l2_interfaces` |
| L3 interfaces | `cisco.ios.ios_l3_interfaces` | `junipernetworks.junos.junos_l3_interfaces` | `arista.eos.eos_l3_interfaces` | `cisco.nxos.nxos_l3_interfaces` |
| Interfaces | `cisco.ios.ios_interfaces` | `junipernetworks.junos.junos_interfaces` | `arista.eos.eos_interfaces` | `cisco.nxos.nxos_interfaces` |
| VLANs | `cisco.ios.ios_vlans` | `junipernetworks.junos.junos_vlans` | `arista.eos.eos_vlans` | `cisco.nxos.nxos_vlans` |
| ACLs | `cisco.ios.ios_acls` | `junipernetworks.junos.junos_acls` | `arista.eos.eos_acls` | `cisco.nxos.nxos_acls` |
| Logging | `cisco.ios.ios_logging_global` | `junipernetworks.junos.junos_logging_global` | `arista.eos.eos_logging_global` | `cisco.nxos.nxos_logging_global` |
| NTP | `cisco.ios.ios_ntp_global` | `junipernetworks.junos.junos_ntp_global` | `arista.eos.eos_ntp_global` | `cisco.nxos.nxos_ntp_global` |
| SNMP | `cisco.ios.ios_snmp_server` | `junipernetworks.junos.junos_snmp_server` | `arista.eos.eos_snmp_server` | `cisco.nxos.nxos_snmp_server` |
| OSPF | `cisco.ios.ios_ospfv2` | `junipernetworks.junos.junos_ospfv2` | `arista.eos.eos_ospfv2` | `cisco.nxos.nxos_ospfv2` |
| BGP | `cisco.ios.ios_bgp_global` | `junipernetworks.junos.junos_bgp_global` | `arista.eos.eos_bgp_global` | `cisco.nxos.nxos_bgp_global` |
| Static routes | `cisco.ios.ios_static_routes` | `junipernetworks.junos.junos_static_routes` | `arista.eos.eos_static_routes` | `cisco.nxos.nxos_static_routes` |
| Hostname | `cisco.ios.ios_hostname` | `junipernetworks.junos.junos_hostname` | `arista.eos.eos_hostname` | `cisco.nxos.nxos_hostname` |

## Platform command and config modules

| Platform | Command Module | Config Module |
|----------|---------------|---------------|
| Cisco IOS | `cisco.ios.ios_command` | `cisco.ios.ios_config` |
| Juniper JunOS | `junipernetworks.junos.junos_command` | `junipernetworks.junos.junos_config` |
| Arista EOS | `arista.eos.eos_command` | `arista.eos.eos_config` |
| Cisco NX-OS | `cisco.nxos.nxos_command` | `cisco.nxos.nxos_config` |

## Resource module states

| State | Action | Modifies Device | Returns |
|-------|--------|-----------------|---------|
| `gathered` | Read current config | No | Structured data in `.gathered` |
| `parsed` | Parse raw config text | No | Structured data in `.parsed` |
| `rendered` | Show CLI commands that would be sent | No | CLI commands in `.rendered` |
| `merged` | Apply config (additive) | Yes | `before`, `after`, `commands` |
| `replaced` | Replace config section | Yes | `before`, `after`, `commands` |
| `overridden` | Replace entire resource | Yes | `before`, `after`, `commands` |
| `deleted` | Remove config | Yes | `before`, `after`, `commands` |

For evaluation, use `gathered` or `parsed` exclusively — they are read-only.

## Cisco IOS-XE Layer 2 Switch (L2S) STIG module mapping

| STIG Control | Resource Module | Approach |
|--------------|-----------------|----------|
| L2 interface mode (access/trunk) | `ios_l2_interfaces` | `state: gathered` |
| DTP / nonegotiate | `ios_l2_interfaces` | `state: gathered` (has `nonegotiate` field) |
| VLAN definitions | `ios_vlans` | `state: gathered` |
| QoS service-policy attachment | `ios_interfaces` | `state: gathered` (has `service_policy` field) |
| Spanning-tree (BPDU/Loop Guard) | None | `ios_command` + filter |
| 802.1x / dot1x | None | `ios_command` + filter |
| VTP | None | `ios_command` + filter |
| UDLD | None | `ios_command` + filter |
| Storm control | None | `ios_command` + filter |
| IGMP snooping | None | `ios_command` + filter |
| QoS policy-map definition | None | `ios_command` + `fact_diff` |
