# Copyright 2026 Red Hat
# GNU General Public License v3.0+

"""Unit tests for network.compliance filter plugins."""

from __future__ import annotations

import json

import pytest
from ansible.errors import AnsibleFilterError

from ansible_collections.network.compliance.plugins.filter.compliance import (
    check_results,
    compliance_summary,
    evaluate_results,
    stig_result,
    to_cklb,
    to_xccdf,
)


# ── Fixtures ──────────────────────────────────────────────────────────


def _make_command_results(interfaces, compliant_pattern):
    """Build a mock registered .results list from ios_command loop."""
    results = []
    for name, config_lines in interfaces:
        results.append(
            {
                "item": {"name": name},
                "stdout": ["\n".join(config_lines)],
            }
        )
    return results


BPDU_COMPLIANT = _make_command_results(
    [
        ("GigabitEthernet0/1", ["interface Gi0/1", " spanning-tree bpduguard enable"]),
        ("GigabitEthernet0/2", ["interface Gi0/2", " spanning-tree bpduguard enable"]),
    ],
    "spanning-tree bpduguard enable",
)

BPDU_NONCOMPLIANT = _make_command_results(
    [
        ("GigabitEthernet0/1", ["interface Gi0/1", " spanning-tree bpduguard enable"]),
        ("GigabitEthernet0/2", ["interface Gi0/2", " switchport mode access"]),
        ("GigabitEthernet0/3", ["interface Gi0/3", " switchport mode access"]),
    ],
    "spanning-tree bpduguard enable",
)

RULES_METADATA = {
    "V-220656": {
        "stig_id": "CISC-L2-000100",
        "rule_id": "SV-220656r856278",
        "severity": "cat2",
        "srg_id": "SRG-NET-000362-L2S-000017",
        "cci": "CCI-002385",
        "title": "BPDU Guard must be enabled on all access ports",
    },
    "V-220649": {
        "stig_id": "CISC-L2-000020",
        "rule_id": "SV-220649r863283",
        "severity": "cat1",
        "srg_id": "SRG-NET-000148-L2S-000015",
        "cci": "CCI-000778",
        "title": "802.1x authentication on access ports",
    },
}


# ── check_results ─────────────────────────────────────────────────────


class TestCheckResults:
    def test_all_compliant(self):
        result = check_results(BPDU_COMPLIANT, "spanning-tree bpduguard enable")
        assert result == []

    def test_some_noncompliant(self):
        result = check_results(BPDU_NONCOMPLIANT, "spanning-tree bpduguard enable")
        assert result == ["GigabitEthernet0/2", "GigabitEthernet0/3"]

    def test_regex_pattern(self):
        result = check_results(BPDU_COMPLIANT, "bpduguard\\s+enable")
        assert result == []

    def test_custom_keys(self):
        results = [
            {"output": {"text": "ntp server 10.0.0.1 prefer"}, "host": "switch1"},
            {"output": {"text": "no ntp"}, "host": "switch2"},
        ]
        result = check_results(results, "ntp server", result_key="output.text", item_key="host")
        assert result == ["switch2"]

    def test_invalid_input(self):
        with pytest.raises(AnsibleFilterError, match="must be a list"):
            check_results("not_a_list", "pattern")

    def test_missing_stdout(self):
        results = [{"item": {"name": "Gi0/1"}}]
        result = check_results(results, "some pattern")
        assert result == ["Gi0/1"]


# ── stig_result ───────────────────────────────────────────────────────


class TestStigResult:
    def test_compliant(self):
        result = stig_result([], pass_msg="All good")
        assert result == {
            "status": "not_a_finding",
            "findings": [],
            "detail": "All good",
        }

    def test_noncompliant(self):
        result = stig_result(
            ["Gi0/2", "Gi0/3"],
            pass_msg="All good",
            fail_msg="Missing: {}",
        )
        assert result == {
            "status": "open",
            "findings": ["Gi0/2", "Gi0/3"],
            "detail": "Missing: Gi0/2, Gi0/3",
        }

    def test_custom_joiner(self):
        result = stig_result(
            ["A", "B"],
            pass_msg="OK",
            fail_msg="Failed: {}",
            joiner=" | ",
        )
        assert result["detail"] == "Failed: A | B"

    def test_invalid_findings(self):
        with pytest.raises(AnsibleFilterError, match="must be a list"):
            stig_result("not_a_list", pass_msg="OK")


# ── evaluate_results ──────────────────────────────────────────────────


class TestEvaluateResults:
    def test_compliant_rule(self):
        result = evaluate_results(
            BPDU_COMPLIANT,
            rule_id="V-220656",
            match="spanning-tree bpduguard enable",
            pass_msg="All ports have BPDU Guard",
            fail_msg="Missing BPDU Guard: {}",
        )
        assert "V-220656" in result
        assert result["V-220656"]["status"] == "not_a_finding"
        assert result["V-220656"]["findings"] == []

    def test_noncompliant_rule(self):
        result = evaluate_results(
            BPDU_NONCOMPLIANT,
            rule_id="V-220656",
            match="spanning-tree bpduguard enable",
            pass_msg="All ports have BPDU Guard",
            fail_msg="Missing BPDU Guard: {}",
        )
        assert result["V-220656"]["status"] == "open"
        assert "GigabitEthernet0/2" in result["V-220656"]["findings"]

    def test_merges_with_existing(self):
        existing = {
            "V-220649": {
                "status": "not_a_finding",
                "findings": [],
                "detail": "All good",
            }
        }
        result = evaluate_results(
            BPDU_COMPLIANT,
            rule_id="V-220656",
            match="spanning-tree bpduguard enable",
            pass_msg="BPDU OK",
            fail_msg="Missing: {}",
            existing_results=existing,
        )
        assert "V-220649" in result
        assert "V-220656" in result
        assert result["V-220649"]["status"] == "not_a_finding"

    def test_does_not_mutate_existing(self):
        existing = {"V-220649": {"status": "open", "findings": ["Gi0/1"], "detail": "x"}}
        original_copy = dict(existing)
        evaluate_results(
            BPDU_COMPLIANT,
            rule_id="V-220656",
            match="bpduguard",
            pass_msg="OK",
            fail_msg="Failed: {}",
            existing_results=existing,
        )
        assert existing == original_copy

    def test_invalid_existing_results(self):
        with pytest.raises(AnsibleFilterError, match="must be a dict"):
            evaluate_results(
                BPDU_COMPLIANT,
                rule_id="V-220656",
                match="pattern",
                pass_msg="OK",
                fail_msg="Failed: {}",
                existing_results="not_a_dict",
            )


# ── to_cklb ───────────────────────────────────────────────────────────


class TestToCklb:
    def test_valid_cklb_structure(self):
        results = {
            "V-220656": {
                "status": "not_a_finding",
                "findings": [],
                "detail": "All ports have BPDU Guard",
            },
            "V-220649": {
                "status": "open",
                "findings": ["Gi0/1"],
                "detail": "Non-compliant: Gi0/1",
            },
        }
        output = to_cklb(results, RULES_METADATA, "switch01", "10.0.0.1")
        cklb = json.loads(output)

        assert cklb["title"] == "switch01"
        assert cklb["target_data"]["host_name"] == "switch01"
        assert cklb["target_data"]["ip_address"] == "10.0.0.1"
        assert len(cklb["stigs"]) == 1
        assert len(cklb["stigs"][0]["rules"]) == 2

    def test_rule_fields(self):
        results = {
            "V-220656": {"status": "open", "findings": ["Gi0/2"], "detail": "Missing"},
        }
        output = to_cklb(results, RULES_METADATA, "switch01")
        cklb = json.loads(output)
        rule = cklb["stigs"][0]["rules"][0]

        assert rule["group_id"] == "V-220656"
        assert rule["rule_id"] == "SV-220656r856278"
        assert rule["severity"] == "medium"
        assert rule["status"] == "open"

    def test_not_reviewed_default(self):
        results = {}
        output = to_cklb(results, RULES_METADATA, "switch01")
        cklb = json.loads(output)

        for rule in cklb["stigs"][0]["rules"]:
            assert rule["status"] == "not_reviewed"

    def test_invalid_input(self):
        with pytest.raises(AnsibleFilterError):
            to_cklb("not_a_dict", {}, "host")


# ── to_xccdf ─────────────────────────────────────────────────────────


class TestToXccdf:
    def test_valid_xml_structure(self):
        results = {
            "V-220656": {"status": "not_a_finding", "findings": [], "detail": "OK"},
        }
        output = to_xccdf(results, RULES_METADATA, "switch01", "10.0.0.1")

        assert '<?xml version="1.0"' in output
        assert "<target>switch01</target>" in output
        assert "<target-address>10.0.0.1</target-address>" in output
        assert "<result>pass</result>" in output
        assert "sm:detail" in output
        assert "sm:resultEngine" in output

    def test_status_mapping(self):
        results = {
            "V-220656": {"status": "open", "findings": ["Gi0/2"], "detail": "Failed"},
        }
        output = to_xccdf(results, RULES_METADATA, "switch01")
        assert "<result>fail</result>" in output

    def test_not_reviewed_maps_to_notchecked(self):
        results = {}
        output = to_xccdf(results, RULES_METADATA, "switch01")
        assert "<result>notchecked</result>" in output

    def test_xml_escaping(self):
        results = {
            "V-220656": {
                "status": "open",
                "findings": ["Gi0/1"],
                "detail": 'Missing <config> & "quotes"',
            },
        }
        output = to_xccdf(results, RULES_METADATA, "switch01")
        assert "&lt;config&gt;" in output
        assert "&amp;" in output
        assert "&quot;" in output

    def test_invalid_input(self):
        with pytest.raises(AnsibleFilterError):
            to_xccdf("not_a_dict", {}, "host")


# ── compliance_summary ────────────────────────────────────────────────


class TestComplianceSummary:
    def test_mixed_results(self):
        results = {
            "V-220649": {"status": "not_a_finding", "findings": [], "detail": "OK"},
            "V-220656": {"status": "open", "findings": ["Gi0/2"], "detail": "Missing"},
            "V-220657": {"status": "not_a_finding", "findings": [], "detail": "OK"},
        }
        summary = compliance_summary(results)
        assert summary == {"total": 3, "passed": 2, "open": 1, "not_reviewed": 0}

    def test_all_passed(self):
        results = {
            "V-220649": {"status": "not_a_finding", "findings": [], "detail": "OK"},
            "V-220656": {"status": "not_a_finding", "findings": [], "detail": "OK"},
        }
        summary = compliance_summary(results)
        assert summary == {"total": 2, "passed": 2, "open": 0, "not_reviewed": 0}

    def test_empty_results(self):
        summary = compliance_summary({})
        assert summary == {"total": 0, "passed": 0, "open": 0, "not_reviewed": 0}

    def test_not_reviewed(self):
        results = {
            "V-220649": {"status": "not_reviewed", "findings": [], "detail": ""},
        }
        summary = compliance_summary(results)
        assert summary == {"total": 1, "passed": 0, "open": 0, "not_reviewed": 1}

    def test_invalid_input(self):
        with pytest.raises(AnsibleFilterError):
            compliance_summary("not_a_dict")
