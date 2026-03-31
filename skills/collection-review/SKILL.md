---
name: collection-review
description: >-
  Review pull requests and code changes for the network.compliance collection.
  Use when reviewing PRs, checking code quality, validating STIG rule implementations,
  or ensuring validated content standards are met.
license: GPL-3.0-or-later
compatibility: Requires gh CLI, ansible-lint, and access to the repository.
metadata:
  author: network-compliance-team
  version: "1.0"
---

# Collection Review

## When to use this skill

Use this skill when:
- Reviewing a pull request for new STIG rules
- Reviewing platform onboarding changes
- Validating that code meets Ansible Validated Content standards
- Checking compliance with AGENTS.md conventions

## Review process

### Step 1: Understand the change

```bash
gh pr view <number>
gh pr diff <number>
```

Identify what type of change this is:
- **New STIG rule** → Check stig-rule-development checklist
- **New platform** → Check platform-onboarding checklist
- **Bug fix** → Verify the fix and check for regressions
- **Refactor** → Ensure no functional changes

### Step 2: Verify STIG metadata

For any new STIG rule, check `evaluate/vars/stig/rules.yaml`:

```text
[ ] V-key is correct and matches DISA source
[ ] STIG ID matches (e.g., CISC-L2-000020)
[ ] Rule ID with revision is accurate
[ ] Severity category is correct (cat1/cat2/cat3)
[ ] SRG ID is present
[ ] CCI is present
[ ] Check content matches DISA STIG guide
[ ] Fix text matches DISA STIG guide
```

Cross-reference with: https://public.cyber.mil/stigs/

### Step 3: Verify task conventions

```text
[ ] Task names follow: STIG | {stig_id} | {v_key} | {severity} | {description}
[ ] Tags include: STIG ID, V-key, Rule ID, severity (lowercase), CCI
[ ] FQCNs used for ALL modules (no short names)
[ ] Variables accessed via stig_controls['V-XXXXX'] pattern
[ ] Internal variables prefixed with _ (e.g., _eval_result)
[ ] Sensitive values use no_log: true
```

### Step 4: Verify evaluate role requirements

```text
[ ] Works in check_mode (read-only, no device changes)
[ ] Uses resource modules where available (not raw show commands)
[ ] Results stored in stig_results dict keyed by V-key
[ ] Status is 'not_a_finding' or 'open' (not custom values)
[ ] Finding details include specific non-compliant items
[ ] Block structure groups related tasks
```

### Step 5: Verify remediate role requirements

```text
[ ] Conditional on evaluation result: when stig_results[V-key].status == 'open'
[ ] Idempotent: running twice produces no changes
[ ] Uses save_when: changed (not save_when: always)
[ ] Safe-fail logic for lockout-risk operations
[ ] Remediation templates use Jinja2 loops (not hardcoded interfaces)
```

### Step 6: Verify argument_specs.yml

```text
[ ] New variables documented with type, description, default
[ ] Required vs optional correctly marked
[ ] Choices listed where applicable
[ ] No undocumented variables used in tasks
```

### Step 7: Verify Molecule scenarios

```text
[ ] Molecule scenario exists under extensions/molecule/ for the change
[ ] converge.yml applies the role with appropriate variables
[ ] verify.yml asserts both pass (compliant) and fail (non-compliant) scenarios
[ ] idempotence step included in test_sequence for remediate roles
[ ] Scenario runs cleanly: molecule test -s <scenario_name>
```

### Step 8: Verify report integration

```text
[ ] New rules added to stig_viewer.j2 template
[ ] New rules added to xccdf_results.j2 template
[ ] Report includes correct V-key, Rule ID, severity
[ ] Status and findings are templated from stig_results
```

### Step 9: Run quality checks

```bash
# Checkout the PR
gh pr checkout <number>

# Run linters
tox -e lint

# Run sanity
ansible-test sanity -v --docker default

# Run affected Molecule scenarios
molecule test -s <scenario_name>
```

### Step 10: Check changelog

```text
[ ] Changelog fragment exists in changelogs/fragments/
[ ] Fragment uses correct section (minor_changes, bugfixes, etc.)
[ ] Description is user-facing and mentions STIG ID
```

## Common review issues

| Issue | Fix |
|-------|-----|
| Short module names (`ios_config`) | Use FQCN (`cisco.ios.ios_config`) |
| Missing tags on tasks | Add STIG ID, V-key, severity, CCI |
| `ignore_errors: true` | Use `block/rescue` or `failed_when` |
| Hardcoded interface names | Use loop over `compliance_access_ports` |
| `save_when: always` in remediate | Change to `save_when: changed` |
| Custom status values | Use only `not_a_finding`, `open`, `not_reviewed` |
| Missing `no_log` on passwords | Add `no_log: true` |
| `.yml` extension | Use `.yaml` (collection standard) |

## Validated content quality bar

This collection follows Ansible Validated Content standards:

1. **Production-ready**: Passes ansible-lint production profile
2. **Fully documented**: argument_specs, README, task names
3. **Tested**: Integration tests for all rules
4. **Traceable**: Every task maps to a DISA STIG control
5. **Secure**: no_log on secrets, safe-fail on lockout risks
6. **Idempotent**: All remediation is safe to re-run
