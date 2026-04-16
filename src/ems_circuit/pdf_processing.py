from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Iterable

import fitz
import pytesseract
from PIL import Image

from .models import PageRecord, SourceFileRecord


def discover_school_folders(raw_root: Path, school_code: str | None = None) -> list[Path]:
    if school_code:
        target = raw_root / school_code
        return [target] if target.exists() else []

    if not raw_root.exists():
        return []

    return sorted([path for path in raw_root.iterdir() if path.is_dir()])


def inventory_pdf_files(school_dir: Path, supported_extensions: Iterable[str]) -> list[SourceFileRecord]:
    records: list[SourceFileRecord] = []
    allowed_exts = {ext.lower() for ext in supported_extensions}

    for pdf_path in sorted(school_dir.rglob("*")):
        if not pdf_path.is_file():
            continue
        if pdf_path.suffix.lower() not in allowed_exts:
            continue

        try:
            with fitz.open(pdf_path) as doc:
                page_count = doc.page_count
        except Exception:
            page_count = 0

        file_hash = hashlib.md5(str(pdf_path).encode("utf-8")).hexdigest()[:10]

        records.append(
            SourceFileRecord(
                school_code=school_dir.name,
                source_file_id=f"{school_dir.name}_{file_hash}",
                source_file_name=pdf_path.name,
                source_file_path=str(pdf_path),
                extension=pdf_path.suffix.lower(),
                file_size_bytes=pdf_path.stat().st_size,
                page_count=page_count,
            )
        )

    return records


def _resolve_tesseract_cmd(settings: dict) -> str | None:
    configured = (settings.get("tesseract_cmd") or "").strip()
    if configured and Path(configured).exists():
        return configured

    env_path = os.environ.get("TESSERACT_CMD", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    common_windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in common_windows_paths:
        if Path(candidate).exists():
            return candidate

    discovered = shutil.which("tesseract")
    if discovered:
        return discovered

    return None


def _configure_tesseract(settings: dict) -> bool:
    cmd = _resolve_tesseract_cmd(settings)
    if not cmd:
        return False

    pytesseract.pytesseract.tesseract_cmd = cmd
    return True


def _best_ocr_text(image: Image.Image, try_rotations: bool) -> tuple[str, int]:
    candidates: list[tuple[str, int]] = []
    angles = [0, 90, 180, 270] if try_rotations else [0]

    for angle in angles:
        test_image = image.rotate(angle, expand=True) if angle else image
        text = pytesseract.image_to_string(test_image, lang="eng")
        score = sum(ch.isalnum() for ch in text)
        candidates.append((text, score))

    return max(candidates, key=lambda item: item[1]) if candidates else ("", 0)


def extract_pages(
    source: SourceFileRecord,
    working_school_dir: Path,
    settings: dict,
) -> list[PageRecord]:
    pages: list[PageRecord] = []

    text_dir = working_school_dir / "text"
    image_dir = working_school_dir / "page_images"
    text_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    enable_ocr = bool(settings.get("enable_ocr", False))
    native_text_min_chars = int(settings.get("native_text_min_chars", 40))
    ocr_zoom = float(settings.get("ocr_zoom", 2.0))
    ocr_try_rotations = bool(settings.get("ocr_try_rotations", True))
    save_page_images = bool(settings.get("save_page_images", True))
    save_text_files = bool(settings.get("save_text_files", True))

    ocr_ready = False
    if enable_ocr:
        ocr_ready = _configure_tesseract(settings)
        if not ocr_ready:
            raise RuntimeError(
                "OCR is enabled, but Tesseract could not be found. "
                "Set 'tesseract_cmd' in config/settings.yaml or install Tesseract OCR."
            )

    with fitz.open(source.source_file_path) as doc:
        for index, page in enumerate(doc, start=1):
            page_id = f"{source.school_code}_{source.source_file_id}_p{index:04d}"

            image_path = image_dir / f"{page_id}.png"
            text_path = text_dir / f"{page_id}.txt"

            pix = page.get_pixmap(
                matrix=fitz.Matrix(ocr_zoom, ocr_zoom),
                alpha=False,
            )

            if save_page_images:
                pix.save(image_path)
            else:
                pix.save(image_path)

            native_text = (page.get_text("text") or "").strip()
            ocr_text = ""
            extraction_method = "native"

            should_try_ocr = enable_ocr and len(native_text) < native_text_min_chars

            if should_try_ocr:
                with Image.open(image_path) as image:
                    ocr_text, _ = _best_ocr_text(image, try_rotations=ocr_try_rotations)
                ocr_text = ocr_text.strip()
                extraction_method = "ocr" if not native_text else "native+ocr"

            final_text = native_text if len(native_text) >= len(ocr_text) else ocr_text
            if not final_text:
                extraction_method = "none"

            if save_text_files:
                text_path.write_text(final_text, encoding="utf-8")
            else:
                text_path.write_text(final_text, encoding="utf-8")

            pages.append(
                PageRecord(
                    school_code=source.school_code,
                    source_file_id=source.source_file_id,
                    source_file_name=source.source_file_name,
                    source_page_number=index,
                    page_id=page_id,
                    rotation=page.rotation,
                    width=page.rect.width,
                    height=page.rect.height,
                    image_path=str(image_path),
                    text_path=str(text_path),
                    native_text_chars=len(native_text),
                    ocr_text_chars=len(ocr_text),
                    extraction_method=extraction_method,
                    extracted_text=final_text,
                )
            )

    return pages