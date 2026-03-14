"""
Extract text from uploaded images (OCR) and PDFs for expense extraction.
Used by POST /add-document-expenses to process "these are my expenses" uploads.
"""
import os
from typing import Optional

# ----- OCR (EasyOCR) -----
OCR_AVAILABLE = False
try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    pass


def run_ocr(image_path: str, lang: Optional[list] = None) -> str:
    """Run OCR on an image file. Returns extracted text. Requires easyocr."""
    if not OCR_AVAILABLE:
        return ""
    try:
        reader = easyocr.Reader(lang or ["en"], gpu=False, verbose=False)
        result = reader.readtext(image_path, detail=0)
        return " ".join(result).strip() if result else ""
    except Exception:
        return ""


# ----- PDF (PyMuPDF) -----
PDF_AVAILABLE = False
try:
    import pymupdf
    PDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        pymupdf = fitz
        PDF_AVAILABLE = True
    except ImportError:
        pass


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file. Returns concatenated text from all pages."""
    if not PDF_AVAILABLE:
        return ""
    try:
        doc = pymupdf.open(pdf_path)
        parts = []
        for page in doc:
            parts.append(page.get_text())
        doc.close()
        return "\n".join(parts).strip() if parts else ""
    except Exception:
        return ""


def get_text_from_file(file_path: str, content_type: str, filename: str) -> str:
    """
    Get text from a file based on type.
    - Images (png, jpeg, jpg, webp): OCR.
    - PDF: extract text.
    Returns empty string if unsupported or extraction fails.
    """
    ct = (content_type or "").lower()
    fn = (filename or "").lower()
    if "pdf" in ct or fn.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    if any(x in ct or fn.endswith("." + x) for x in ("png", "jpeg", "jpg", "webp", "gif", "bmp")):
        return run_ocr(file_path)
    return ""
