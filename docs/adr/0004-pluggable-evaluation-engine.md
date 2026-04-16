# ADR-0004: Pluggable Evaluation Engine

## Status

Proposed

## Context

The evaluate role currently embeds compliance logic directly in Ansible task files — each rule is a `block` with `ios_command` + filter plugin calls. This works but tightly couples compliance rules to the automation platform:

- Compliance teams must understand Ansible to review or write rules.
- The same rule logic cannot be reused outside Ansible (CI/CD gates, API checks, drift detection).
- Adding a rule requires editing YAML tasks, not just declaring policy intent.

The Open Policy Agent (OPA) ecosystem provides a mature, language-agnostic policy engine with its own rule language (Rego), testing framework, and deployment model. The community rego_policy_libraries project demonstrates that STIG, CIS, and NIST rules can be expressed as declarative Rego policies with structured input/output contracts.

## Decision

### Pluggable evaluation engine with a stable interface

The evaluate role supports multiple evaluation engines selected via configuration:

```yaml
compliance_evaluate:
  engine: native    # default
  # engine: opa     # alternative
```

### Engine interface contract

Every engine must:

1. **Accept** a normalized device state as structured JSON input
2. **Return** findings in the `stig_results` contract: `{V-key: {status, findings, detail}}`
3. **Respect** `stig_controls[V-key].run` toggles
4. **Support** severity filtering via `compliance_evaluate.cat{1,2,3}`

This contract ensures remediate and report roles work unchanged regardless of which engine produced the findings.

### Separation of concerns

```text
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Scan Role  │────>│  Evaluate Role   │────>│ Remediate / Report│
│  (gather)    │     │  (engine dispatch)│     │  (consume results)│
└──────────────┘     └────────┬─────────┘     └──────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
              ┌─────▼─────┐      ┌──────▼──────┐
              │  Native   │      │    OPA      │
              │  Engine   │      │   Engine    │
              │           │      │             │
              │ Ansible   │      │ Rego        │
              │ tasks +   │      │ policies +  │
              │ filters   │      │ opa eval    │
              └───────────┘      └─────────────┘
```

**Scan role** — gathers device state. Produces normalized JSON.

**Evaluate role** — dispatches to the configured engine. Does not contain rule logic itself.

**Engine** — contains the compliance logic. Native engine uses Ansible tasks + filter plugins. OPA engine uses Rego policies + `opa eval`.

**Remediate/Report roles** — consume `stig_results`. Do not know or care which engine produced them.

### Config normalization as a first-class concern

Device config gathered by the scan role must be normalized into a structured JSON schema before evaluation. This normalization layer is the bridge between platform-specific CLI output and engine-agnostic policy evaluation.

```text
show running-config    normalize_config     JSON Schema
(CLI text)          ──────────────────>   (structured data)
                       filter plugin        ▲
                                           │
                                    documented schema
                                    (policies/schemas/)
```

The JSON schema is:
- **Published** as a JSON Schema file for machine validation
- **Documented** in markdown for policy authors
- **Annotated** in Rego files via OPA metadata annotations
- **Validated** at runtime before engine evaluation

### Extensibility for future engines

The engine dispatch pattern supports adding new engines without modifying existing code:

```text
roles/evaluate/tasks/
├── main.yaml                    # dispatches by engine
├── engines/
│   ├── native.yaml              # current: include stig/<platform>/ tasks
│   └── opa.yaml                 # new: normalize + opa eval
├── stig/ios/                    # native engine rule tasks
```

Future engines (e.g., InSpec, custom Python) would add a new file under `engines/` and a new `engine:` value.

### Why not replace native with OPA entirely

- **OPA is an optional dependency** — not all users will have the `opa` binary or an OPA server
- **Native engine has zero external dependencies** — works with just Ansible
- **Gradual migration path** — users can start with native, move to OPA when ready
- **Different audiences** — Ansible engineers prefer YAML tasks, security teams prefer Rego policies

## Consequences

- Evaluate role becomes a dispatcher, not a rule container.
- Two evaluation paths to maintain (native tasks + OPA policies).
- `normalize_config` filter becomes critical infrastructure — all engines depend on it.
- Policy authors can choose their preferred language (YAML or Rego).
- Same rules can be used outside Ansible when written in Rego.
- Custom policy support enables partners/vendors to bring their own rules.
