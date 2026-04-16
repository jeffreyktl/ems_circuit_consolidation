# EMS Circuit Consolidation

A conservative, traceable Python starter project for consolidating school electrical circuit information into an EMS planning workbook.

## What this project does

- scans one school folder at a time under `data/raw/<SCHOOL_CODE>/`
- inventories all PDF files
- extracts native PDF text first
- optionally applies OCR when native text is weak or unavailable
- classifies each page into practical subtypes such as:
  - transmittal cover
  - WR2 certificate
  - checklist
  - works order
  - inspection report index
  - distribution board test result schedule
  - schematic / as-built drawing
  - unknown
- performs conservative field extraction from page text
- keeps source traceability for every extracted evidence row
- consolidates evidence into a circuit register
- writes an Excel workbook and CSV intermediate outputs

## Important design principle

This project is intentionally conservative.

It does **not invent values** when the source is missing, ambiguous, or unreadable.
Unclear items are marked for manual review.

## Folder layout

```text
ems_circuit_consolidation/
├─ README.md
├─ requirements.txt
├─ run_pipeline.py
├─ config/
│  ├─ settings.yaml
│  ├─ equipment_keywords.yaml
│  ├─ room_type_keywords.yaml
│  └─ page_type_rules.yaml
├─ data/
│  ├─ raw/
│  │  └─ <SCHOOL_CODE>/
│  │     └─ *.pdf
│  ├─ working/
│  │  └─ <SCHOOL_CODE>/
│  │     ├─ page_images/
│  │     ├─ text/
│  │     ├─ file_inventory.csv
│  │     ├─ page_index.csv
│  │     ├─ source_evidence.csv
│  │     └─ conflicts_review.csv
│  └─ output/
│     ├─ <SCHOOL_CODE>_EMS_Circuit_Consolidation.xlsx
│     └─ <SCHOOL_CODE>_circuit_register.csv
├─ logs/
└─ src/
   └─ ems_circuit/
      ├─ __init__.py
      ├─ config_loader.py
      ├─ models.py
      ├─ logging_utils.py
      ├─ pdf_processing.py
      ├─ page_classifier.py
      ├─ entity_extractor.py
      ├─ consolidator.py
      ├─ workbook_writer.py
      └─ pipeline.py
```

## Installation

```bash
pip install -r requirements.txt
```

If OCR is enabled, install the Tesseract OCR engine and make sure it is available in PATH.

## Run

```bash
python run_pipeline.py --project-root . --school SCH001 --enable-ocr
```

Or process every school folder under `data/raw/`:

```bash
python run_pipeline.py --project-root . --enable-ocr
```

## Outputs

### CSV / intermediate
- `file_inventory.csv`: file-level inventory
- `page_index.csv`: page-level text, rotation, subtype, and extraction details
- `source_evidence.csv`: one row per extracted evidence item
- `conflicts_review.csv`: unresolved issues or conflicting data
- `<SCHOOL_CODE>_circuit_register.csv`: consolidated circuit register

### Excel workbook
- `Summary`
- `Circuit_Register`
- `Source_Evidence`
- `Conflicts_Review`
- `Missing_Documents`
- `Page_Index`

## Current limitations

- table extraction from scanned board-test pages is heuristic, not perfect
- schematic interpretation is intentionally limited and conservative
- OCR quality depends heavily on scan quality and page orientation
- some circuit rows may remain `Require manual review`

## Recommended use

1. place each school's PDFs under `data/raw/<SCHOOL_CODE>/`
2. run the pipeline
3. review the `Conflicts_Review` sheet and low-confidence rows
4. refine config keyword files as you encounter new document patterns
