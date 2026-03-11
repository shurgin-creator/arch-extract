"""
PDF processing utilities for converting pages to high-resolution images
and extracting embedded text/tables via PyMuPDF (hybrid extraction).
"""

import os
import sys
from pdf2image import convert_from_bytes
from PIL import Image
from typing import List, Dict, Tuple
import fitz  # PyMuPDF


class PDFProcessor:
    """Handles PDF to image conversion and embedded text extraction."""

    def __init__(self, dpi: int = 300, fmt: str = "png"):
        """
        Initialize PDF processor.

        Args:
            dpi: Resolution in dots per inch (default: 300 for high-res)
            fmt: Image format (default: png for lossless quality)
        """
        self.dpi = dpi
        self.fmt = fmt

        # Set poppler path based on platform
        if sys.platform == "darwin" and os.path.exists("/opt/homebrew/bin"):
            self.poppler_path = "/opt/homebrew/bin"
        else:
            self.poppler_path = None

    def convert_pdf_bytes(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Convert PDF from bytes to images.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            List of PIL Image objects
        """
        try:
            images = convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                fmt=self.fmt,
                poppler_path=self.poppler_path
            )
            return images
        except Exception as e:
            raise RuntimeError(f"Error converting PDF from bytes: {str(e)}")

    def extract_text_per_page(self, pdf_bytes: bytes) -> List[str]:
        """
        Extract embedded text and table content from each PDF page using PyMuPDF.
        Returns one text string per page with all machine-readable text preserved.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            List of text strings, one per page (empty string if no text on page)
        """
        page_texts = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_index in range(len(doc)):
                page = doc[page_index]

                # Extract plain text blocks with positional awareness
                text_blocks = page.get_text("blocks")  # list of (x0, y0, x1, y1, text, block_no, block_type)
                page_width = page.rect.width
                page_height = page.rect.height

                # Sort blocks top-to-bottom, left-to-right (natural reading order)
                text_blocks_sorted = sorted(text_blocks, key=lambda b: (round(b[1] / 50), b[0]))

                lines = []
                for block in text_blocks_sorted:
                    if block[6] == 0:  # block_type 0 = text (1 = image)
                        raw = block[4].strip()
                        if raw:
                            lines.append(raw)

                # Also extract any table-like structures using dict mode
                table_text = self._extract_tables(page)
                if table_text:
                    lines.append("\n[TABLES DETECTED]\n" + table_text)

                raw_text = "\n".join(lines)
                # Aggressively truncate to prevent token limit errors on dense CAD PDFs
                if len(raw_text) > 4000:
                    raw_text = raw_text[:4000] + "\n[TRUNCATED - text exceeded 4000 char limit]"
                page_texts.append(raw_text)

            doc.close()
        except Exception as e:
            print(f"PyMuPDF text extraction warning: {e}")
            # Graceful fallback: return empty strings so extraction still proceeds
            page_texts = [""] * len(page_texts) if page_texts else []

        return page_texts

    def convert_pdf_bytes_with_text(self, pdf_bytes: bytes) -> Tuple[List[Image.Image], List[str]]:
        """
        Combined hybrid extraction: converts PDF to images AND extracts embedded text.
        Both operations run on the same bytes buffer — no double file I/O.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            Tuple of (list of PIL Images, list of per-page text strings)
        """
        images = self.convert_pdf_bytes(pdf_bytes)
        page_texts = self.extract_text_per_page(pdf_bytes)

        # Pad page_texts if PyMuPDF found fewer pages than pdf2image (edge case)
        while len(page_texts) < len(images):
            page_texts.append("")

        print(f"Hybrid extraction: {len(images)} pages, {sum(len(t) for t in page_texts)} total text chars extracted")
        return images, page_texts

    def _extract_tables(self, page) -> str:
        """
        Attempt to extract table-like structures from a page using PyMuPDF's
        text dict mode to reconstruct rows of aligned text spans.

        Args:
            page: fitz.Page object

        Returns:
            Formatted table string, or empty string if none found
        """
        try:
            blocks = page.get_text("dict")["blocks"]
            table_rows = []
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if len(spans) >= 2:  # Multiple spans on same line = likely table row
                        row_text = " | ".join(s["text"].strip() for s in spans if s["text"].strip())
                        if row_text:
                            table_rows.append(row_text)
            return "\n".join(table_rows)
        except Exception:
            return ""

    def get_image_bytes(self, image: Image.Image) -> bytes:
        """
        Convert PIL Image to bytes for API transmission.

        Args:
            image: PIL Image object

        Returns:
            Image as bytes
        """
        import io
        buffer = io.BytesIO()
        image.save(buffer, format=self.fmt.upper())
        return buffer.getvalue()
