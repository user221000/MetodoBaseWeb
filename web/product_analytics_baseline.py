"""Pure provisional baseline artifact; no filesystem, network or SQL authority.

The caller must obtain an authorised report and choose a private exclusive
destination. These bytes never establish real-client provenance, grant access,
merge subjects or define a business target. No token/identity is accepted.
"""
import hashlib

from web.product_analytics_domain import canonical, dictionary, validate_report


def build_baseline(report):
    validated = validate_report(report)
    result = {"format_version": 1, "artifact_kind": "r30_observed_facts_snapshot",
        "validation_state": "unreviewed", "business_baseline_established": False, "targets": None,
        "measurement_dictionary": dictionary(),
        "report_hash": hashlib.sha256(canonical(validated)).hexdigest(), "report": validated}
    result["artifact_hash"] = hashlib.sha256(canonical(result)).hexdigest()
    return result


def baseline_bytes(report):
    return canonical(build_baseline(report)) + b"\n"
