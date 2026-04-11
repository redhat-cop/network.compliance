# Contributing to network.compliance

## Setting up the development environment

```bash
# Clone the repository
git clone https://github.com/redhat-cop/network.compliance.git
cd network.compliance

# Install ansible-dev-tools (bundles ansible-lint, molecule, tox, pytest, ade, and more)
pip install ansible-dev-tools

# Create isolated virtual environment with collection installed in editable mode
ade install -e . --venv .venv
source .venv/bin/activate

# Verify setup
ansible-galaxy collection list | grep network.compliance
adt --version
```

The `ade install -e .` command:

- Creates a Python virtual environment at `.venv/`
- Installs `ansible-core` and all collection dependencies (`cisco.ios`, `ansible.utils`, etc.)
- Installs Python dependencies from `requirements.txt` (`jmespath`, `xmltodict`)
- Symlinks the collection source so edits are reflected immediately
- Configures `ansible.cfg` for workspace isolation

## Contributing with an AI Agent

This repository supports agentic development via [Agent Skills](https://agentskills.io). Skills are auto-discovered from `.agents/skills/` by Claude Code, Cursor, GitHub Copilot, VS Code, and other compatible tools.

**Before writing code, produce documentation first:**

1. **Research** — investigate the problem space and document findings in `docs/research/NNNN-<topic>.md` (use `docs/research/template.md`)
2. **ADR** — if your change involves an architecture or design decision, record it in `docs/adr/NNNN-<decision>.md` (use `docs/adr/template.md`)
3. **Spec** — write or update a spec in `docs/specs/NNNN-<feature>.md` with goal, design, file manifest, acceptance criteria, and verification steps (use `docs/specs/template.md`)
4. **Review and approve** — get spec approval before implementation begins

**Then implement using the appropriate skill:**

| Task | Skill | Location |
|------|-------|----------|
| Set up dev environment | `dev-environment-setup` | `.agents/skills/dev-environment-setup/SKILL.md` |
| Add a STIG rule | `stig-rule-development` | `.agents/skills/stig-rule-development/SKILL.md` |
| Write tests | `compliance-testing` | `.agents/skills/compliance-testing/SKILL.md` |
| Add a platform | `platform-onboarding` | `.agents/skills/platform-onboarding/SKILL.md` |
| Review a PR | `collection-review` | `.agents/skills/collection-review/SKILL.md` |

## Development Workflow

1. **Research and spec** — document the problem, produce an ADR if needed, write or update a spec
2. **Pick a STIG rule** — identify the V-key, STIG ID, and severity from the [DISA STIG Library](https://public.cyber.mil/stigs/)
3. **Implement** — follow the workflow in `.agents/skills/stig-rule-development/SKILL.md`
4. **Test** — write a Molecule scenario covering both compliant and non-compliant states
5. **Lint** — ensure `tox -e lint` passes before submitting

## Running CI checks locally

```bash
# Auto-fix all lint and format issues
tox -e fix

# Run all CI checks (recommended before pushing)
tox -e ci

# Individual checks
tox -e lint           # ansible-lint
tox -e unit           # unit tests (filter plugins)
tox -e ruff           # Python lint + format
tox -e sanity         # ansible-test sanity (requires Docker)
tox -e gitleaks       # secret scanning
tox -e molecule       # all Molecule scenarios

# Set up pre-commit hooks (runs checks on every commit)
pre-commit install
```

## Conventions

- **File extensions**: `.yaml` for YAML, `.j2` for Jinja2 templates
- **Module references**: always use FQCNs (`cisco.ios.ios_config`, not `ios_config`)
- **Task names**: `STIG | <STIG_ID> | <V-key> | <severity> | <description>`
- **Tags**: every task tagged with STIG ID, V-key, Rule ID, severity, CCI
- **Variables**: `compliance_` prefix for user-facing, `_` prefix for internal
- **Error handling**: `block/rescue` instead of `ignore_errors: true`
- **Sensitive values**: `no_log: true` on passwords, keys, communities
- **Line length**: 160 characters max

## PR Checklist

- [ ] Rule metadata added to `evaluate/vars/stig/<platform>/catN.yaml`
- [ ] Task names and tags follow conventions
- [ ] FQCNs used for all modules
- [ ] `check_mode` works for evaluate tasks
- [ ] Remediation is idempotent
- [ ] `no_log` on sensitive values
- [ ] `argument_specs.yml` updated
- [ ] Molecule scenario added (pass + fail cases)
- [ ] Changelog fragment in `changelogs/fragments/`
- [ ] `tox -e ci` passes locally
