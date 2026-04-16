from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SourceFileRecord:
    school_code: str
    source_file_id: str
    source_file_name: str
    source_file_path: str
    extension: str
    file_size_bytes: int
    page_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PageRecord:
    school_code: str
    source_file_id: str
    source_file_name: str
    source_page_number: int
    page_id: str
    rotation: int
    width: float
    height: float
    image_path: str
    text_path: str
    native_text_chars: int
    ocr_text_chars: int
    extraction_method: str
    page_subtype: str = "unknown"
    source_document_type: str = "unknown"
    review_status: str = "Require manual review"
    extracted_text: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["text_preview"] = self.extracted_text[:180]
        return data


@dataclass
class EvidenceRow:
    school_code: str
    record_id: str
    source_file_id: str
    source_file_name: str
    source_page_number: int
    source_document_type: str
    page_subtype: str
    distribution_board_name: str = ""
    distribution_board_location: str = ""
    circuit_reference: str = ""
    breaker_type: str = ""
    breaker_rating: str = ""
    circuit_description_raw: str = ""
    location_served_raw: str = ""
    equipment_type_confirmed: str = ""
    equipment_type_inferred: str = ""
    room_type_confirmed: str = ""
    room_type_inferred: str = ""
    special_system_type: str = ""
    evidence_snippet: str = ""
    extraction_method: str = ""
    data_status: str = "Require manual review"
    manual_review_reason: str = ""
    source_priority_rank: int = 99

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CircuitRegisterRow:
    school_code: str
    record_id: str
    distribution_board_name: str
    distribution_board_location: str
    circuit_reference: str
    breaker_type: str
    breaker_rating: str
    circuit_description_raw: str
    equipment_type_confirmed: str
    equipment_type_inferred: str
    room_type_confirmed: str
    room_type_inferred: str
    special_system_type: str
    likely_suitable_for_monitoring: str
    monitoring_rationale: str
    likely_suitable_for_control: str
    control_rationale: str
    primary_source_file_name: str
    primary_source_page: int
    primary_source_document_type: str
    supporting_document_count: int
    conflict_flag: str
    data_status: str
    manual_review_reason: str
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConflictRecord:
    school_code: str
    record_id: str
    issue_type: str
    issue_detail: str
    source_file_name: str
    source_page_number: int

    def to_dict(self) -> dict:
        return asdict(self)
