# ADR-0003: Quality Standards and Tooling

## Status

Accepted

## Context

This collection ships as Ansible Validated Content with a production-grade quality bar. Network remediation carries lockout risk. STIG evaluation tasks repeat the same patterns across every rule — without abstraction, each rule requires verbose Jinja2 filter chains that are difficult to read and error-prone to duplicate. We evaluated existing plugins across ansible-core, ansible.utils, and ansible.netcommon and found no existing plugin handles the compliance-specific "command results -> non-compliant items -> status dict -> merge" pipeline.

## Decision

### Custom Filter Plugins

Five filter plugins in `plugins/filter/compliance.py` to simplify evaluation, reporting, and eliminate repeated Jinja2 boilerplate.

**Building blocks** (usable independently):

- **`check_results`** — takes registered command loop output and a regex match pattern. Returns list of non-compliant item identifiers. Replaces the `rejectattr('stdout.0', 'search', pattern) | map(attribute='item.name') | list` chain.
- **`stig_result`** — takes a findings list, pass message, and fail message template. Returns `{status, findings, detail}` dict. Replaces ternary status/detail construction.

**Convenience** (combines building blocks + merge):

- **`evaluate_results`** — takes registered command output, rule ID, match pattern, messages, and existing results dict. Returns the merged results dict with the new rule added. One call replaces `check_results` + `stig_result` + `combine()`.

**Report generation:**

- **`to_cklb`** — takes `stig_results` + `stig_rules`, returns CKLB JSON string. Replaces Jinja2 template.
- **`to_xccdf`** — takes `stig_results` + `stig_rules`, returns XCCDF 1.2 XML string. Replaces Jinja2 template.

### Standardize on Command Modules

All rules use `<os>_command` for evaluate and `<os>_config` for remediate — even where resource modules exist (e.g., `ios_l2_interfaces` for DTP). This trades structured data and `state: merged` remediation for a single evaluation pattern and a single set of filter plugins. Resource modules are still used in the scan role for fact gathering.

### What We Chose Not to Build

- **`classify_interfaces`** — interface-specific, runs once, low ROI.
- **`check_config`** — would handle resource module structured data, unnecessary after standardizing on command modules.
- **STIG metadata lookup** — platform-specific `catN.yaml` files loaded via `include_vars` are sufficient.

### Validated Content Requirements

- **Linting**: Must pass `ansible-lint` production profile and `yamllint`
- **Testing**: Molecule scenarios for every rule (pass + fail). Idempotence checks for remediation
- **Documentation**: `argument_specs.yml` for all role variables with type/choice validation
- **Signing**: Digital signing for supply-chain security
- **Sensitive values**: `no_log: true` on passwords, keys, SNMP communities

### Error Handling

- **Never use `ignore_errors: true`** — use `block/rescue` or `failed_when`
- **Safe-fail logic** for lockout-risk operations: verify alternative access before disabling current access
- **`save_when: changed`** on all config tasks (never `save_when: always`)

### Check Mode and Idempotency

- Evaluate role must work entirely in `check_mode` (read-only)
- Scan role is inherently read-only
- Remediate role must be idempotent (second run = zero changes)

## Consequences

- Each evaluate rule is a 2-task pattern: gather + `evaluate_results` filter call.
- Report generation is testable Python instead of Jinja2 templates.
- Contributors must learn the filter API, but it's simpler than the Jinja2 chains it replaces.
- Adding a new rule requires no new Python — only YAML tasks using existing filters.
- Higher upfront effort per rule — each needs metadata, tasks, templates, tests, and argument specs.
- Remediation is safe to run against production devices.
