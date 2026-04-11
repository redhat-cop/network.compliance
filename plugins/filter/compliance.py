# Copyright 2026 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Filter plugins for network compliance evaluation and reporting."""

from __future__ import annotations

import json
import re

from ansible.errors import AnsibleFilterError


def check_results(results, match, result_key="stdout.0", item_key="item.name"):
    """Extract non-compliant items from registered command loop output.

    Takes the ``.results`` list from a registered loop task (e.g.,
    ``ios_command`` run per interface) and returns the identifiers of
    items whose output does NOT match the expected pattern.

    Args:
        results: List of registered loop results (``_register.results``).
        match: Regex pattern that compliant output must contain.
        result_key: Dot-notation path to the output text to check.
            Default ``stdout.0`` (first element of stdout list).
        item_key: Dot-notation path to the item identifier to return.
            Default ``item.name``.

    Returns:
        List of non-compliant item identifiers.

    Example::

        {{ _eval.results | network.compliance.check_results(
             match='spanning-tree bpduguard enable') }}
        # -> ['GigabitEthernet0/2', 'GigabitEthernet0/5']
    """
    if not isinstance(results, list):
        raise AnsibleFilterError(
            "check_results: input must be a list (registered .results), "
            f"got {type(results).__name__}"
        )

    pattern = re.compile(match)
    non_compliant = []

    for entry in results:
        output = _resolve_path(entry, result_key)
        identifier = _resolve_path(entry, item_key)

        if output is None:
            non_compliant.append(identifier)
            continue

        if not pattern.search(str(output)):
            non_compliant.append(identifier)

    return non_compliant


def stig_result(findings, pass_msg, fail_msg="Non-compliant items: {}", joiner=", "):
    """Build a STIG evaluation result dict from a findings list.

    Converts a list of non-compliant items into the standardized
    ``stig_results`` entry structure used across evaluate, remediate,
    and report roles.

    Args:
        findings: List of non-compliant item identifiers.
            Empty list means compliant.
        pass_msg: Message when no findings (status = ``not_a_finding``).
        fail_msg: Message template when findings exist (status = ``open``).
            Use ``{}`` as placeholder for the joined findings list.
        joiner: String to join findings in the fail message. Default ``, ``.

    Returns:
        Dict with ``status``, ``findings``, and ``detail`` keys.

    Example::

        {{ my_findings | network.compliance.stig_result(
             pass_msg='All ports compliant',
             fail_msg='Non-compliant: {}') }}
        # -> {'status': 'open', 'findings': ['Gi0/2'], 'detail': 'Non-compliant: Gi0/2'}
    """
    if not isinstance(findings, list):
        raise AnsibleFilterError(
            f"stig_result: findings must be a list, got {type(findings).__name__}"
        )

    is_compliant = len(findings) == 0

    return {
        "status": "not_a_finding" if is_compliant else "open",
        "findings": findings,
        "detail": pass_msg
        if is_compliant
        else fail_msg.format(joiner.join(str(f) for f in findings)),
    }


def evaluate_results(
    results,
    rule_id,
    match,
    pass_msg,
    fail_msg,
    existing_results=None,
    result_key="stdout.0",
    item_key="item.name",
    joiner=", ",
):
    """Full evaluate pipeline: check results + build status + merge.

    Combines ``check_results`` and ``stig_result`` into a single call,
    then merges the result into the existing ``stig_results`` dict.

    Args:
        results: List of registered loop results.
        rule_id: V-key identifier (e.g., ``V-220656``).
        match: Regex pattern that compliant output must contain.
        pass_msg: Message when compliant.
        fail_msg: Message template when non-compliant. Use ``{}``
            as placeholder for the findings list.
        existing_results: Existing ``stig_results`` dict to merge into.
            Default ``None`` (starts empty).
        result_key: Dot-notation path to output text. Default ``stdout.0``.
        item_key: Dot-notation path to item identifier. Default ``item.name``.
        joiner: String to join findings. Default ``, ``.

    Returns:
        Merged ``stig_results`` dict with the new rule added.

    Example::

        {{ _eval.results | network.compliance.evaluate_results(
             rule_id='V-220656',
             match='spanning-tree bpduguard enable',
             pass_msg='All ports have BPDU Guard',
             fail_msg='Missing BPDU Guard: {}',
             existing_results=stig_results) }}
    """
    if existing_results is None:
        existing_results = {}

    if not isinstance(existing_results, dict):
        raise AnsibleFilterError(
            "evaluate_results: existing_results must be a dict, "
            f"got {type(existing_results).__name__}"
        )

    findings = check_results(results, match, result_key, item_key)
    result = stig_result(findings, pass_msg, fail_msg, joiner)

    merged = dict(existing_results)
    merged[rule_id] = result
    return merged


def to_cklb(
    stig_results_dict, rules, hostname, ip_address="", comment="Evaluated by network.compliance"
):
    """Generate CKLB JSON from stig_results and stig_rules.

    Produces a DISA STIG Viewer compatible checklist (CKLB) file.

    Args:
        stig_results_dict: The ``stig_results`` dict keyed by V-key.
        rules: The ``stig_rules`` metadata dict keyed by V-key.
        hostname: Target device hostname.
        ip_address: Target device IP address.
        comment: Comment to include in each rule entry.

    Returns:
        CKLB JSON string.
    """
    if not isinstance(stig_results_dict, dict):
        raise AnsibleFilterError(
            f"to_cklb: stig_results must be a dict, got {type(stig_results_dict).__name__}"
        )
    if not isinstance(rules, dict):
        raise AnsibleFilterError(f"to_cklb: rules must be a dict, got {type(rules).__name__}")

    severity_map = {"cat1": "high", "cat2": "medium", "cat3": "low"}

    cklb_rules = []
    for v_key, rule_meta in rules.items():
        result = stig_results_dict.get(v_key, {})
        cklb_rules.append(
            {
                "group_id": v_key,
                "rule_id": rule_meta.get("rule_id", ""),
                "rule_version": rule_meta.get("stig_id", ""),
                "severity": severity_map.get(rule_meta.get("severity", ""), ""),
                "status": result.get("status", "not_reviewed"),
                "overrides": {},
                "comments": comment,
                "finding_details": result.get("detail", ""),
                "srg_id": rule_meta.get("srg_id", ""),
            }
        )

    cklb = {
        "title": hostname,
        "id": "",
        "stigs": [
            {
                "stig_name": "Cisco IOS XE Switch L2S Security Technical Implementation Guide",
                "display_name": "Cisco IOS XE Switch L2S",
                "stig_id": "Cisco_IOS_XE_Switch_L2S_STIG",
                "version": "3",
                "rules": cklb_rules,
            }
        ],
        "target_data": {
            "target_type": "Non-Computing",
            "host_name": hostname,
            "ip_address": ip_address,
            "technology_area": "Internal Network",
        },
    }

    return json.dumps(cklb, indent=2)


def to_xccdf(stig_results_dict, rules, hostname, ip_address="", collection_version="0.1.0"):
    """Generate XCCDF XML from stig_results and stig_rules.

    Produces NIST XCCDF 1.2 XML with STIG Manager namespace extensions.

    Args:
        stig_results_dict: The ``stig_results`` dict keyed by V-key.
        rules: The ``stig_rules`` metadata dict keyed by V-key.
        hostname: Target device hostname.
        ip_address: Target device IP address.
        collection_version: Collection version string.

    Returns:
        XCCDF XML string.
    """
    if not isinstance(stig_results_dict, dict):
        raise AnsibleFilterError(
            f"to_xccdf: stig_results must be a dict, got {type(stig_results_dict).__name__}"
        )
    if not isinstance(rules, dict):
        raise AnsibleFilterError(f"to_xccdf: rules must be a dict, got {type(rules).__name__}")

    status_map = {
        "not_a_finding": "pass",
        "open": "fail",
        "not_reviewed": "notchecked",
    }

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<TestResult xmlns="http://checklists.nist.gov/xccdf/1.2"',
        '            xmlns:sm="http://github.com/nuwcdivnpt/stig-manager"',
        f'            id="xccdf_network.compliance_testresult_{hostname}"',
        '            test-system="network.compliance"',
        f'            version="{collection_version}">',
        f"  <target>{hostname}</target>",
        f"  <target-address>{ip_address}</target-address>",
    ]

    for v_key, rule_meta in rules.items():
        result = stig_results_dict.get(v_key, {})
        status = result.get("status", "not_reviewed")
        xccdf_status = status_map.get(status, "notchecked")
        detail = _xml_escape(result.get("detail", ""))
        rule_id = rule_meta.get("rule_id", v_key.replace("V-", "SV-"))

        lines.append(f'  <rule-result idref="{rule_id}">')
        lines.append(f"    <result>{xccdf_status}</result>")
        lines.append(f"    <sm:detail>{detail}</sm:detail>")
        lines.append("    <sm:resultEngine>")
        lines.append("      <product>network.compliance</product>")
        lines.append(f"      <version>{collection_version}</version>")
        lines.append("    </sm:resultEngine>")
        lines.append("  </rule-result>")

    lines.append("</TestResult>")
    return "\n".join(lines)


def _resolve_path(obj, path):
    """Resolve a dot-notation path against an object.

    Supports dict keys and integer list indices.
    Returns None if the path cannot be resolved.
    """
    current = obj
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def _xml_escape(text):
    """Escape special characters for XML content."""
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    return text


def compliance_summary(stig_results_dict):
    """Summarize compliance evaluation results.

    Args:
        stig_results_dict: The ``stig_results`` dict keyed by V-key.

    Returns:
        Dict with ``total``, ``passed``, ``open``, and ``not_reviewed`` counts.
    """
    if not isinstance(stig_results_dict, dict):
        raise AnsibleFilterError(
            f"compliance_summary: input must be a dict, got {type(stig_results_dict).__name__}"
        )

    passed = 0
    open_count = 0
    not_reviewed = 0

    for result in stig_results_dict.values():
        status = (
            result.get("status", "not_reviewed") if isinstance(result, dict) else "not_reviewed"
        )
        if status == "not_a_finding":
            passed += 1
        elif status == "open":
            open_count += 1
        else:
            not_reviewed += 1

    return {
        "total": len(stig_results_dict),
        "passed": passed,
        "open": open_count,
        "not_reviewed": not_reviewed,
    }


class FilterModule:
    """Network compliance filter plugins."""

    def filters(self):
        """Return filter plugin mappings."""
        return {
            "check_results": check_results,
            "stig_result": stig_result,
            "evaluate_results": evaluate_results,
            "compliance_summary": compliance_summary,
            "to_cklb": to_cklb,
            "to_xccdf": to_xccdf,
        }
