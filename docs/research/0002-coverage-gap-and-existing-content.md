# RESEARCH-0002: Coverage Gap and Existing DISA Content

## Summary

60+ network device STIG guides have no Ansible automation. Existing DISA-provided Ansible packages (4 platforms) are outdated and don't meet validated content quality standards.

## Findings

### Existing DISA Ansible Content

| Platform | STIG Date | Ansible Date | Status |
|----------|-----------|--------------|--------|
| Cisco IOS XE Router NDM/RTR | Oct 2021 | Feb 2017 | Outdated |
| Juniper SRX SG ALG/NDM/VPN | Nov 2020 | Nov 2020 | Outdated |
| Palo Alto Networks NDM | Jan 2022 | Jan 2022 | Outdated |

### Platforms With No Automation

Cisco (ACI, ASA, IOS/IOS-XE/IOS-XR switches, ISE, NX-OS), Juniper (EX Series, Routers), Dell, F5, Fortinet, Forescout, HPE, plus generic SRGs (DNS, Firewall, IDS/IPS, Router, Switch, VPN).

### DISA Content Quality Gaps

Reviewed `U_Cisco_IOS_XE_Router_NDM_RTR_V2R3`, `U_Juniper_SRX_SG_V1R1`, `U_Palo_Alto_Networks_V1R4`:

- Flat playbooks (no roles), no resource modules, no FQCNs
- No argument specs, Molecule tests, or CKLB/XCCDF generation
- No idempotency or check_mode support
- **Useful:** V-key to show-command mappings and check/fix text are accurate and reusable for populating `rules.yaml`

## Recommendations

- Prioritize Cisco IOS/IOS-XE Layer 2 Switch (L2S) as first target (existing reference implementation)
- Use DISA content only as a reference for control-to-command mappings
- Build a scalable framework (platform dispatching) rather than one-off playbooks
