from __future__ import annotations

import re
from typing import Iterable

from .models import ConflictRecord, EvidenceRow, PageRecord

BOARD_PATTERNS = {
    "distribution_board_name": re.compile(r"Distribution\s+Board\s*:\s*'?([^\n']+)" , re.IGNORECASE),
    "distribution_board_location": re.compile(r"Location\s*:\s*([^\n]+)", re.IGNORECASE),
    "main_switch_rating": re.compile(r"D\.B\.\s*Main\s*Sw\.\s*Rating\s*:\s*([^\n]+)", re.IGNORECASE),
    "number_of_ways": re.compile(r"No\.\s*of\s*Ways\s*:\s*(\d+)", re.IGNORECASE),
}

ROW_START_RE = re.compile(r"^(?P<circuit>(?:\d+[A-Z]?(?:[-/][A-Z0-9.]+)+(?:,?\d*[A-Z]?(?:[-/][A-Z0-9.]+)*)*))\s+(?P<rest>.+)$")
DEVICE_HINT_RE = re.compile(r"\b(MCB|MCCB|RCBO|ACB|SPN|TPN|F/SW|F/S|ISOLATOR|SWITCH)\b", re.IGNORECASE)
RATING_HINT_RE = re.compile(r"\b(\d{1,4}A?|C\s*\d{1,3}|B\s*\d{1,3})\b", re.IGNORECASE)


def extract_evidence_from_pages(
    pages: Iterable[PageRecord],
    equipment_keywords: dict,
    room_type_keywords: dict,
    settings: dict,
) -> tuple[list[EvidenceRow], list[ConflictRecord]]:
    evidence_rows: list[EvidenceRow] = []
    conflicts: list[ConflictRecord] = []

    for page in pages:
        text = page.extracted_text or ""
        if not text.strip():
            continue

        board_meta = _extract_board_meta(text)

        if page.page_subtype == "distribution_board_test_result":
            row_items = _extract_distribution_board_rows(page, text, board_meta, equipment_keywords, room_type_keywords)
            evidence_rows.extend(row_items)
            if not row_items:
                conflicts.append(
                    ConflictRecord(
                        school_code=page.school_code,
                        record_id=page.page_id,
                        issue_type="No circuit rows extracted",
                        issue_detail="Distribution board test result page detected, but no circuit rows were parsed.",
                        source_file_name=page.source_file_name,
                        source_page_number=page.source_page_number,
                    )
                )
        elif page.page_subtype == "schematic_as_built":
            evidence_rows.append(
                EvidenceRow(
                    school_code=page.school_code,
                    record_id=f"{page.page_id}_SCH001",
                    source_file_id=page.source_file_id,
                    source_file_name=page.source_file_name,
                    source_page_number=page.source_page_number,
                    source_document_type=page.source_document_type,
                    page_subtype=page.page_subtype,
                    distribution_board_name=board_meta.get("distribution_board_name", ""),
                    distribution_board_location=board_meta.get("distribution_board_location", ""),
                    evidence_snippet=(text[: settings.get("max_evidence_snippet_length", 180)]),
                    extraction_method=page.extraction_method,
                    data_status="Require manual review",
                    manual_review_reason="Schematic pages are recorded for traceability, but detailed circuit parsing is not automated.",
                    source_priority_rank=3,
                )
            )
        else:
            # Keep selected non-tabular pages as context evidence only when they are likely relevant.
            if page.page_subtype in {"wr2_certificate", "inspection_report_index", "checklist", "works_order", "transmittal_cover"}:
                evidence_rows.append(
                    EvidenceRow(
                        school_code=page.school_code,
                        record_id=f"{page.page_id}_CTX001",
                        source_file_id=page.source_file_id,
                        source_file_name=page.source_file_name,
                        source_page_number=page.source_page_number,
                        source_document_type=page.source_document_type,
                        page_subtype=page.page_subtype,
                        distribution_board_name=board_meta.get("distribution_board_name", ""),
                        distribution_board_location=board_meta.get("distribution_board_location", ""),
                        evidence_snippet=text[: settings.get("max_evidence_snippet_length", 180)],
                        extraction_method=page.extraction_method,
                        data_status="Inferred",
                        manual_review_reason="Context page retained for package-level traceability.",
                        source_priority_rank=4,
                    )
                )

    return evidence_rows, conflicts


def _extract_board_meta(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, pattern in BOARD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            result[key] = _clean(match.group(1))
    return result


def _extract_distribution_board_rows(
    page: PageRecord,
    text: str,
    board_meta: dict[str, str],
    equipment_keywords: dict,
    room_type_keywords: dict,
) -> list[EvidenceRow]:
    results: list[EvidenceRow] = []
    lines = [_clean(line) for line in text.splitlines() if _clean(line)]

    for idx, line in enumerate(lines, start=1):
        if line.lower().startswith(("remarks", "declaration", "all cable are", "test results are satisfactory")):
            continue
        row_match = ROW_START_RE.match(line)
        if not row_match:
            continue
        if not DEVICE_HINT_RE.search(line) and not RATING_HINT_RE.search(line):
            # Many OCR'd row starts are noisy; require at least some device/rating clue.
            continue

        circuit_reference = _clean(row_match.group("circuit"))
        row_rest = _clean(row_match.group("rest"))
        breaker_type = _extract_breaker_type(row_rest)
        breaker_rating = _extract_breaker_rating(row_rest)
        description = _extract_description(row_rest)
        equipment_type = _match_keywords(description, equipment_keywords)
        room_type = _match_keywords(description + " " + board_meta.get("distribution_board_location", ""), room_type_keywords)
        special_system = _infer_special_system(description)

        results.append(
            EvidenceRow(
                school_code=page.school_code,
                record_id=f"{page.page_id}_ROW{idx:03d}",
                source_file_id=page.source_file_id,
                source_file_name=page.source_file_name,
                source_page_number=page.source_page_number,
                source_document_type=page.source_document_type,
                page_subtype=page.page_subtype,
                distribution_board_name=board_meta.get("distribution_board_name", ""),
                distribution_board_location=board_meta.get("distribution_board_location", ""),
                circuit_reference=circuit_reference,
                breaker_type=breaker_type,
                breaker_rating=breaker_rating,
                circuit_description_raw=description,
                location_served_raw=board_meta.get("distribution_board_location", ""),
                equipment_type_inferred=equipment_type,
                room_type_inferred=room_type,
                special_system_type=special_system,
                evidence_snippet=line[:180],
                extraction_method=page.extraction_method,
                data_status="Inferred" if equipment_type or room_type or description else "Require manual review",
                manual_review_reason="Check OCR/table parsing against source page if the row is important.",
                source_priority_rank=1,
            )
        )

    return results


def _extract_breaker_type(text: str) -> str:
    match = DEVICE_HINT_RE.search(text)
    return match.group(1).upper() if match else ""


def _extract_breaker_rating(text: str) -> str:
    match = RATING_HINT_RE.search(text)
    return _clean(match.group(1)).upper() if match else ""


def _extract_description(text: str) -> str:
    description = DEVICE_HINT_RE.sub(" ", text)
    description = RATING_HINT_RE.sub(" ", description, count=1)
    description = re.sub(r"\s+", " ", description).strip(" -:;,")
    return description


def _match_keywords(text: str, mapping: dict) -> str:
    haystack = text.lower()
    for label, keywords in mapping.items():
        for keyword in keywords:
            if keyword.lower() in haystack:
                return label
    return ""


def _infer_special_system(description: str) -> str:
    haystack = description.lower()
    if any(term in haystack for term in ["emergency lighting", "exit sign", "smoke detector", "fap", "fsp", "fire"]):
        return "fire / life safety"
    if any(term in haystack for term in ["pv", "solar", "inverter"]):
        return "pv system"
    if any(term in haystack for term in ["server", "computer room", "it"]):
        return "server / it equipment"
    return ""


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()
