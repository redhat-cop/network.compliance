============================
network.compliance Release Notes
============================

.. contents:: Topics

v0.1.0
======

Release Summary
---------------

Initial release of the network.compliance collection with STIG compliance
evaluation and remediation for Cisco IOS-XE Layer 2 Switch devices.

Major Changes
-------------

- Added scan role for device discovery and interface classification.
- Added evaluate role with 9 STIG rules (1 CAT I, 6 CAT II, 2 CAT III).
- Added remediate role with conditional remediation gated on evaluation results.
- Added report role with CKLB and XCCDF output via filter plugins.
- Added filter plugins: check_results, stig_result, evaluate_results, to_cklb, to_xccdf.
