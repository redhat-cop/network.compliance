# RESEARCH-0001: STIG Standards and Compliance Frameworks

## Summary

Mapped the DISA STIG data model (identifiers, severity, artifact formats) and compared compliance frameworks to justify STIG as the primary target.

## Findings

### STIG Identifier Hierarchy

| ID | Format | Example | Purpose |
|----|--------|---------|---------|
| V-Key | V-NNNNNN | V-220649 | Primary vulnerability identifier |
| Rule ID | SV-NNNNNNrNNNNNN | SV-220649r863283 | Rule with revision tracking |
| STIG ID | CISC-L2-NNNNNN | CISC-L2-000020 | Human-readable control ref |
| SRG ID | SRG-NET-NNNNNN-... | SRG-NET-000148-L2S-000015 | Security Requirements Guide |
| CCI | CCI-NNNNNN | CCI-000044 | NIST 800-53 crosswalk |

Severity: CAT I (high/critical), CAT II (medium), CAT III (low). Updated quarterly by DISA.

### Framework Comparison

| Framework | Mandate | Why not primary |
|-----------|---------|-----------------|
| **STIG** (selected) | DoD, Federal, contractors | -- |
| CIS Benchmarks | Voluntary | Less granular, no V-key traceability |
| NIST 800-53 | Federal (FISMA) | Control families, not device-specific |

STIG selected because: mandatory for largest customer base, most granular (per-device controls), existing tooling ecosystem, and CCI crosswalk covers NIST 800-53. The `compliance_framework` dispatch pattern supports adding CIS later.

### STIG Manager Integration

- Open-source (NUWCDIVNPT) web dashboard for fleet compliance tracking
- API: `POST /api/collections/{collectionId}/reviews` with OIDC auth
- Accepts XCCDF with `sm:detail`/`sm:resultEngine` namespace extensions
- Also supports `stigman-watcher` for file-based auto-import

## References

- https://public.cyber.mil/stigs/
- https://www.stigviewer.com/stigs
- https://github.com/NUWCDIVNPT/stig-manager
- https://www.cisecurity.org/cis-benchmarks
