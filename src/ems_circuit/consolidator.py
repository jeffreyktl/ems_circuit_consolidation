from __future__ import annotations

from collections import defaultdict

from .models import CircuitRegisterRow, ConflictRecord, EvidenceRow


def consolidate_evidence(evidence_rows: list[EvidenceRow], settings: dict) -> tuple[list[CircuitRegisterRow], list[ConflictRecord]]:
    grouped: dict[tuple[str, str, str], list[EvidenceRow]] = defaultdict(list)
    conflicts: list[ConflictRecord] = []

    for row in evidence_rows:
        if not row.circuit_reference and not row.distribution_board_name:
            continue
        key = (row.school_code, row.distribution_board_name.strip().upper(), row.circuit_reference.strip().upper())
        grouped[key].append(row)

    register: list[CircuitRegisterRow] = []

    for key, rows in grouped.items():
        school_code, _, _ = key
        primary = min(rows, key=lambda item: item.source_priority_rank)
        equipment_type = _pick_first(rows, "equipment_type_confirmed") or _pick_first(rows, "equipment_type_inferred")
        room_type = _pick_first(rows, "room_type_confirmed") or _pick_first(rows, "room_type_inferred")
        special_system = _pick_first(rows, "special_system_type")
        data_status = _merge_status(rows)
        conflict_flag = "No"
        notes: list[str] = []

        board_names = {row.distribution_board_name for row in rows if row.distribution_board_name}
        descriptions = {row.circuit_description_raw for row in rows if row.circuit_description_raw}
        if len(board_names) > 1:
            conflict_flag = "Yes"
            notes.append("Multiple board names found across evidence rows.")
        if len(descriptions) > 1:
            notes.append("Multiple raw descriptions found; check source evidence.")

        monitoring, monitoring_reason = _monitoring_decision(equipment_type, special_system, settings)
        control, control_reason = _control_decision(equipment_type, special_system, settings)

        register.append(
            CircuitRegisterRow(
                school_code=school_code,
                record_id=primary.record_id,
                distribution_board_name=primary.distribution_board_name,
                distribution_board_location=primary.distribution_board_location,
                circuit_reference=primary.circuit_reference,
                breaker_type=primary.breaker_type,
                breaker_rating=primary.breaker_rating,
                circuit_description_raw=primary.circuit_description_raw,
                equipment_type_confirmed=primary.equipment_type_confirmed,
                equipment_type_inferred=equipment_type,
                room_type_confirmed=primary.room_type_confirmed,
                room_type_inferred=room_type,
                special_system_type=special_system,
                likely_suitable_for_monitoring=monitoring,
                monitoring_rationale=monitoring_reason,
                likely_suitable_for_control=control,
                control_rationale=control_reason,
                primary_source_file_name=primary.source_file_name,
                primary_source_page=primary.source_page_number,
                primary_source_document_type=primary.source_document_type,
                supporting_document_count=len(rows),
                conflict_flag=conflict_flag,
                data_status=data_status,
                manual_review_reason=primary.manual_review_reason,
                notes="; ".join(notes),
            )
        )

    register.sort(key=lambda row: (row.distribution_board_name, row.circuit_reference))
    return register, conflicts


def _pick_first(rows: list[EvidenceRow], field_name: str) -> str:
    for row in rows:
        value = getattr(row, field_name, "")
        if value:
            return value
    return ""


def _merge_status(rows: list[EvidenceRow]) -> str:
    if any(row.data_status == "Require manual review" for row in rows):
        return "Require manual review"
    if any(row.data_status == "Uncertain" for row in rows):
        return "Uncertain"
    if any(row.data_status == "Inferred" for row in rows):
        return "Inferred"
    return "Confirmed"


def _monitoring_decision(equipment_type: str, special_system: str, settings: dict) -> tuple[str, str]:
    if special_system in settings["monitoring_logic"].get("no", []):
        return "No", f"Excluded because the load appears to be a special system: {special_system}."
    if equipment_type in settings["monitoring_logic"].get("yes", []):
        return "Yes", f"Likely monitorable based on inferred equipment type: {equipment_type}."
    if equipment_type in settings["monitoring_logic"].get("possible", []):
        return "Possible", f"Potentially monitorable, but the load may be too mixed or operationally unclear: {equipment_type}."
    if not equipment_type:
        return "Uncertain", "No reliable equipment type could be inferred from the current evidence."
    return "Possible", f"No hard rule configured for inferred equipment type: {equipment_type}."


def _control_decision(equipment_type: str, special_system: str, settings: dict) -> tuple[str, str]:
    if special_system or equipment_type in settings["control_logic"].get("no", []):
        label = special_system or equipment_type or "unidentified load"
        return "No", f"Not recommended for automatic control without detailed engineering review: {label}."
    if equipment_type in settings["control_logic"].get("yes", []):
        return "Yes", f"Potentially suitable for EMS control based on inferred equipment type: {equipment_type}."
    if equipment_type in settings["control_logic"].get("possible", []):
        return "Possible", f"May be suitable for control, but further operational review is needed: {equipment_type}."
    if not equipment_type:
        return "Uncertain", "Control suitability cannot be assessed because the equipment type is unclear."
    return "Possible", f"No hard rule configured for inferred equipment type: {equipment_type}."
