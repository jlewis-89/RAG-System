"""
Document Text Extraction Service.
Supports clean text, markdown, and multi-page PDF extraction using pdfplumber or pypdf.
"""

import os
import re
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Union

logger = logging.getLogger(__name__)


class DocumentExtractionError(Exception):
    """Raised when text cannot be extracted from a file."""
    pass


def clean_extracted_text(text: str) -> str:
    """
    Cleans raw extracted text:
    - Normalizes line endings to '\n'
    - Strips page break markers ('\x0c')
    - Recombines hyphenated words across line boundaries (common in government PDFs)
    - Normalizes non-breaking spaces and non-standard whitespace
    """
    if not text:
        return ""

    # Replace form feeds and special spaces
    cleaned = text.replace('\x0c', '\n\n').replace('\u00a0', ' ').replace('\ufeff', '')
    cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')

    # Fix hyphenated words across lines (e.g. 'rea-\nsonably' -> 'reasonably')
    cleaned = re.sub(r'(\b[A-Za-z]{2,})-\n\s*([a-z]{2,}\b)', r'\1\2', cleaned)

    # Clean multiple consecutive blank lines (limit to max 2)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()


def extract_from_plain_text(path: Path) -> Tuple[str, Dict[str, Any]]:
    """Extracts text from UTF-8, UTF-8-BOM, or Latin-1 text and markdown files."""
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    raw_content = None
    used_encoding = None

    for enc in encodings:
        try:
            with open(path, 'r', encoding=enc) as f:
                raw_content = f.read()
                used_encoding = enc
                break
        except (UnicodeDecodeError, LookupError):
            continue

    if raw_content is None:
        raise DocumentExtractionError(f"Failed to decode text file at {path} using encodings: {encodings}")

    cleaned = clean_extracted_text(raw_content)
    metadata = {
        "file_name": path.name,
        "extension": path.suffix.lower(),
        "encoding": used_encoding,
        "char_count": len(cleaned),
        "source_type": "text/markdown"
    }
    return cleaned, metadata


def extract_from_pdf(path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Extracts text from PDF documents.
    Prefers pdfplumber for superior columnar and layout extraction,
    with automatic fallback to pypdf or PyPDF2.
    """
    # 1. Attempt pdfplumber
    try:
        import pdfplumber
        logger.info(f"Extracting PDF using pdfplumber: {path}")
        extracted_pages = []
        # Support empty password for protected/owner-restricted PDFs
        try:
            pdf_ctx = pdfplumber.open(path, password="")
        except Exception:
            pdf_ctx = pdfplumber.open(path)

        with pdf_ctx as pdf:
            total_pages = len(pdf.pages)
            for idx, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text() or page.extract_text(layout=True) or ""
                except Exception:
                    page_text = ""
                if page_text.strip():
                    extracted_pages.append(page_text.strip())

        full_text = "\n\n".join(extracted_pages)
        cleaned = clean_extracted_text(full_text)
        metadata = {
            "file_name": path.name,
            "extension": ".pdf",
            "pages_count": total_pages,
            "extractor": "pdfplumber",
            "char_count": len(cleaned),
            "source_type": "pdf"
        }
        return cleaned, metadata
    except ImportError:
        logger.debug("pdfplumber not available, trying pypdf")
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed for {path}: {e}. Falling back to pypdf...")

    # 2. Attempt pypdf
    try:
        import pypdf
        logger.info(f"Extracting PDF using pypdf: {path}")
        reader = pypdf.PdfReader(str(path))
        if getattr(reader, 'is_encrypted', False):
            try:
                reader.decrypt("")
            except Exception:
                pass

        extracted_pages = []
        total_pages = len(reader.pages)
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            if page_text.strip():
                extracted_pages.append(page_text.strip())

        full_text = "\n\n".join(extracted_pages)
        cleaned = clean_extracted_text(full_text)
        metadata = {
            "file_name": path.name,
            "extension": ".pdf",
            "pages_count": total_pages,
            "extractor": "pypdf",
            "char_count": len(cleaned),
            "source_type": "pdf"
        }
        return cleaned, metadata
    except ImportError:
        logger.debug("pypdf not available, trying PyPDF2")
    except Exception as e:
        logger.warning(f"pypdf extraction failed for {path}: {e}. Falling back to PyPDF2...")

    # 3. Attempt PyPDF2
    try:
        import PyPDF2
        logger.info(f"Extracting PDF using PyPDF2: {path}")
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            extracted_pages = []
            total_pages = len(reader.pages)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(page_text.strip())

        full_text = "\n\n".join(extracted_pages)
        cleaned = clean_extracted_text(full_text)
        metadata = {
            "file_name": path.name,
            "extension": ".pdf",
            "pages_count": total_pages,
            "extractor": "PyPDF2",
            "char_count": len(cleaned),
            "source_type": "pdf"
        }
        return cleaned, metadata
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"PyPDF2 extraction also failed for {path}: {e}")

    # If neither library is available
    raise DocumentExtractionError(
        f"Cannot extract PDF file '{path}'. None of the supported PDF extraction libraries "
        f"(pdfplumber, pypdf, PyPDF2) are installed or usable in the current Python environment.\n"
        f"Please install via: pip install pypdf pdfplumber"
    )


def extract_text_from_file(file_path: Union[str, Path]) -> Tuple[str, Dict[str, Any]]:
    """
    Main entry point for extracting text from any supported file format
    (.txt, .md, .markdown, .pdf, .json, .html).
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix in ('.txt', '.md', '.markdown', '.rst', '.json', '.html', '.htm'):
        return extract_from_plain_text(path)
    elif suffix == '.pdf':
        return extract_from_pdf(path)
    else:
        # Attempt text read as fallback
        logger.info(f"Unrecognized file extension '{suffix}', attempting plain text decode...")
        return extract_from_plain_text(path)
