from __future__ import annotations

import argparse
from pathlib import Path

from src.ems_circuit.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EMS circuit consolidation pipeline")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--school", type=str, default=None, help="Single school code to process")
    parser.add_argument("--enable-ocr", action="store_true", help="Enable OCR fallback for weak text pages")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(project_root=args.project_root, school_code=args.school, enable_ocr_override=args.enable_ocr)


if __name__ == "__main__":
    main()
