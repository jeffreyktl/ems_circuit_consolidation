from __future__ import annotations

from .models import PageRecord


def classify_page(page: PageRecord, rules: dict) -> PageRecord:
    haystack = f"{page.source_file_name}\n{page.extracted_text}".lower()
    selected_subtype = "unknown"

    for subtype, payload in rules.items():
        patterns = payload.get("patterns", [])
        if any(pattern.lower() in haystack for pattern in patterns):
            selected_subtype = subtype
            break

    page.page_subtype = selected_subtype
    page.source_document_type = _map_document_type(selected_subtype)
    page.review_status = _default_review_status(page)
    return page


def _map_document_type(page_subtype: str) -> str:
    mapping = {
        "transmittal_cover": "transmittal / cover memo",
        "wr2_certificate": "WR2 / certificate",
        "inspection_report_index": "inspection report",
        "checklist": "checklist",
        "works_order": "works order",
        "distribution_board_test_result": "distribution board test result schedule",
        "schematic_as_built": "schematic / as-built drawing",
    }
    return mapping.get(page_subtype, "unknown")


def _default_review_status(page: PageRecord) -> str:
    if page.page_subtype in {"distribution_board_test_result", "wr2_certificate", "schematic_as_built"}:
        return "Inferred"
    return "Require manual review"
