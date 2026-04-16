from __future__ import annotations

import csv
from pathlib import Path

from .config_loader import ConfigBundle
from .consolidator import consolidate_evidence
from .entity_extractor import extract_evidence_from_pages
from .logging_utils import setup_logger
from .page_classifier import classify_page
from .pdf_processing import discover_school_folders, extract_pages, inventory_pdf_files
from .workbook_writer import write_workbook


def run_pipeline(project_root: Path, school_code: str | None = None, enable_ocr_override: bool = False) -> None:
    project_root = project_root.resolve()
    configs = ConfigBundle(project_root)
    settings = configs.settings.copy()
    if enable_ocr_override:
        settings["enable_ocr"] = True

    raw_root = project_root / "data" / "raw"
    working_root = project_root / "data" / "working"
    output_root = project_root / "data" / "output"
    log_root = project_root / "logs"

    school_folders = discover_school_folders(raw_root, school_code)
    if not school_folders:
        raise FileNotFoundError(f"No matching school folders found under: {raw_root}")

    for school_dir in school_folders:
        school_code_value = school_dir.name
        logger = setup_logger(log_root / f"{school_code_value}_processing.log")
        logger.info("Processing school folder: %s", school_dir)

        working_school_dir = working_root / school_code_value
        working_school_dir.mkdir(parents=True, exist_ok=True)

        files = inventory_pdf_files(school_dir, settings.get("supported_extensions", [".pdf"]))
        logger.info("Detected %s PDF file(s)", len(files))
        _write_csv(working_school_dir / "file_inventory.csv", [file.to_dict() for file in files])

        pages = []
        for source_file in files:
            file_pages = extract_pages(source_file, working_school_dir, settings)
            pages.extend(file_pages)
        logger.info("Processed %s page(s)", len(pages))

        classified_pages = [classify_page(page, configs.page_type_rules) for page in pages]
        _write_csv(working_school_dir / "page_index.csv", [page.to_dict() for page in classified_pages])

        evidence_rows, extraction_conflicts = extract_evidence_from_pages(
            classified_pages,
            configs.equipment_keywords,
            configs.room_type_keywords,
            settings,
        )
        logger.info("Extracted %s evidence row(s)", len(evidence_rows))
        _write_csv(working_school_dir / "source_evidence.csv", [row.to_dict() for row in evidence_rows])

        circuit_rows, consolidation_conflicts = consolidate_evidence(evidence_rows, settings)
        all_conflicts = extraction_conflicts + consolidation_conflicts
        logger.info("Built %s consolidated circuit row(s)", len(circuit_rows))
        _write_csv(working_school_dir / "conflicts_review.csv", [row.to_dict() for row in all_conflicts])
        _write_csv(output_root / f"{school_code_value}_circuit_register.csv", [row.to_dict() for row in circuit_rows])

        workbook_path = output_root / f"{school_code_value}_EMS_Circuit_Consolidation.xlsx"
        write_workbook(
            output_path=workbook_path,
            school_code=school_code_value,
            files=files,
            pages=classified_pages,
            evidence_rows=evidence_rows,
            circuit_rows=circuit_rows,
            conflicts=all_conflicts,
        )
        logger.info("Wrote workbook: %s", workbook_path)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with path.open("w", newline="", encoding="utf-8") as handle:
            handle.write("")
        return

    headers = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
