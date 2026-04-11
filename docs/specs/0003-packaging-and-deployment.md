# SPEC-0003: Packaging and Deployment

## Goal

Package as Ansible Validated Content for Automation Hub distribution, with AAP workflow seeding for operational deployment.

## Design

### Collection Packaging

**galaxy.yml:**
```yaml
namespace: network
name: compliance
version: 1.0.0
dependencies:
  cisco.ios: ">=8.0.0"
  ansible.netcommon: ">=6.0.0"
  ansible.utils: ">=4.0.0"
```

- Python deps: `jmespath`, `xmltodict`
- Changelog: `changelogs/fragments/` with `antsibull-changelog`
- Sanity: `ansible-test sanity` must pass
- Digital signing for supply-chain security

### Platform Onboarding (adding a new network OS)

1. Add dependency to `galaxy.yml`
2. Create scan tasks: `roles/scan/tasks/<platform>.yaml`
3. Create evaluate/remediate directories under `stig/<platform>/`
4. Map STIG rules to platform command/config modules
5. Add Molecule scenarios
6. Update supported platforms table in docs

### AAP Workflow Seeding

**Workflow:** `[Scan] -> [Evaluate] -> [Approval Node] -> [Remediate] -> [Report]`

- Approval node gates remediation — operator reviews findings first
- Survey: target inventory, framework, severity filter, dry-run toggle
- Execution environment: `ee-supported-rhel9` + collection deps + Python deps
- Fleet-wide: runs across inventory groups, generates per-device artifacts

## Acceptance Criteria

- [ ] `ansible-galaxy collection build` succeeds
- [ ] `ansible-test sanity` passes
- [ ] `meta/runtime.yml` specifies minimum ansible-core version
- [ ] AAP workflow template with approval node documented
- [ ] EE definition file included
- [ ] Platform onboarding documented with checklist

## Dependencies

- All core roles implemented (SPEC-0001)
- `antsibull-changelog` for changelog management
- AAP 2.x for workflow seeding
