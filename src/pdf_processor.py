"""
PDF processing utilities for converting pages to high-resolution images
and extracting embedded text/tables via PyMuPDF (hybrid extraction).

Lazy page iteration is the primary extraction path: pages are converted and
yielded one at a time to avoid loading the full document into memory.
"""

import gc
import io
import os
import sys
from pdf2image import convert_from_bytes
from PIL import Image
from typing import Generator, List, Tuple
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

    # ------------------------------------------------------------------
    # Lazy extraction (primary path — avoids OOM on large PDFs)
    # ------------------------------------------------------------------

    def get_page_count(self, pdf_bytes: bytes) -> int:
        """
        Return total page count without rendering any images.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            Number of pages in the PDF
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count

    def iter_pages(self, pdf_bytes: bytes) -> Generator[Tuple[Image.Image, str], None, None]:
        """
        Lazily yield (PIL.Image, page_text) for each page, one at a time.

        Keeps the fitz document open across all pages for efficient text
        extraction while converting images one page at a time via pdf2image.
        After yielding, drops local references and calls gc.collect() so the
        consumer's deletion triggers prompt memory release.

        Args:
            pdf_bytes: PDF file as bytes

        Yields:
            Tuple of (PIL Image for page, extracted text string for page)
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            for page_index in range(len(doc)):
                page_num = page_index + 1

                # Convert this single page to an image (first_page/last_page avoids
                # loading the entire PDF into Poppler memory at once)
                page_images = convert_from_bytes(
                    pdf_bytes,
                    dpi=self.dpi,
                    fmt=self.fmt,
                    poppler_path=self.poppler_path,
                    first_page=page_num,
                    last_page=page_num,
                )
                image = page_images[0]
                del page_images  # Free the list wrapper immediately

                # Extract text for this page using the open fitz doc
                fitz_page = doc[page_index]
                page_text = self._extract_page_text_from_fitz_page(fitz_page)

                yield image, page_text

                # Drop generator-side references; consumer already del'd its copy,
                # so after gc.collect() the PIL Image object is freed.
                del image, page_text
                gc.collect()
        finally:
            doc.close()

    # ------------------------------------------------------------------
    # Bulk extraction (kept for backward compatibility / refine path)
    # ------------------------------------------------------------------

    def convert_pdf_bytes(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Convert PDF from bytes to images (all pages at once).

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
        Extract embedded text from each PDF page using PyMuPDF.
        Returns one text string per page.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            List of text strings, one per page (empty string if no text on page)
        """
        page_texts = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            for page_index in range(len(doc)):
                page_texts.append(
                    self._extract_page_text_from_fitz_page(doc[page_index])
                )
        except Exception as e:
            print(f"PyMuPDF text extraction warning: {e}")
            page_texts = [""] * len(page_texts) if page_texts else []
        finally:
            doc.close()
        return page_texts

    def convert_pdf_bytes_with_text(self, pdf_bytes: bytes) -> Tuple[List[Image.Image], List[str]]:
        """
        Combined hybrid extraction: converts PDF to images AND extracts embedded text.
        NOTE: Loads all pages into memory — use iter_pages() for large PDFs.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            Tuple of (list of PIL Images, list of per-page text strings)
        """
        images = self.convert_pdf_bytes(pdf_bytes)
        page_texts = self.extract_text_per_page(pdf_bytes)

        while len(page_texts) < len(images):
            page_texts.append("")

        print(f"Hybrid extraction: {len(images)} pages, {sum(len(t) for t in page_texts)} total text chars extracted")
        return images, page_texts

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_page_text_from_fitz_page(self, page) -> str:
        """
        Extract and process text from a single fitz.Page object.
        Truncates to 4000 chars to prevent token overflows.

        Args:
            page: fitz.Page object

        Returns:
            Extracted text string (max 4000 chars)
        """
        try:
            text_blocks = page.get_text("blocks")
            # Sort top-to-bottom, left-to-right (natural reading order)
            text_blocks_sorted = sorted(text_blocks, key=lambda b: (round(b[1] / 50), b[0]))

            lines = []
            for block in text_blocks_sorted:
                if block[6] == 0:  # block_type 0 = text (1 = image)
                    raw = block[4].strip()
                    if raw:
                        lines.append(raw)

            table_text = self._extract_tables(page)
            if table_text:
                lines.append("\n[TABLES DETECTED]\n" + table_text)

            raw_text = "\n".join(lines)
            # Aggressively truncate to prevent token limit errors on dense CAD PDFs
            if len(raw_text) > 4000:
                raw_text = raw_text[:4000] + "\n[TRUNCATED - text exceeded 4000 char limit]"
            return raw_text
        except Exception:
            return ""

    def _extract_tables(self, page) -> str:
        """
        Reconstruct table rows from multi-span lines using PyMuPDF dict mode.

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
        buffer = io.BytesIO()
        image.save(buffer, format=self.fmt.upper())
        return buffer.getvalue()
