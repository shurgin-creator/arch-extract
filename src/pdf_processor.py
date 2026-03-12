"""
PDF processing utilities for converting pages to high-resolution images
and extracting embedded text/tables via PyMuPDF (hybrid extraction).

Lazy page iteration is the primary extraction path: pages are converted and
yielded one at a time to avoid loading the full document into memory.

Super Skills (Phase 3 accuracy boost)
--------------------------------------
1. Enhanced Hybrid Text Extraction  — structured key-value pair detection
   in addition to block-level text; raised char limit to 8 000 per page.
2. OpenCV Pre-processing            — CLAHE contrast enhancement, deskew,
   and unsharp-mask sharpening applied before sending to Gemini.
3. Smart Cropping                   — the title block region (bottom-right
   or bottom-left 35 % × 20 % of the page) is cropped and yielded as a
   third element of the page tuple so Gemini receives a zoomed close-up.
"""

import gc
import io
import os
import re
import sys
from pdf2image import convert_from_bytes
from PIL import Image
from typing import Generator, List, Optional, Tuple
import fitz  # PyMuPDF

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False
    print("WARNING: opencv-python-headless not installed — preprocessing disabled.")


class PDFProcessor:
    """Handles PDF to image conversion, preprocessing, and embedded text extraction."""

    def __init__(self, dpi: int = 300, fmt: str = "png", preprocess: bool = True):
        """
        Initialize PDF processor.

        Args:
            dpi: Resolution in dots per inch (default: 300 for high-res)
            fmt: Image format (default: png for lossless quality)
            preprocess: Apply OpenCV contrast/deskew/sharpen pipeline (default: True).
                        Automatically disabled if opencv is not installed.
        """
        self.dpi = dpi
        self.fmt = fmt
        self.preprocess = preprocess and _CV2_AVAILABLE

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

    def iter_pages(
        self, pdf_bytes: bytes
    ) -> Generator[Tuple[Image.Image, str, Optional[Image.Image]], None, None]:
        """
        Lazily yield (page_image, page_text, title_block_crop) for each page.

        page_image        — full-page PIL Image (preprocessed if enabled)
        page_text         — embedded text string (hybrid extraction)
        title_block_crop  — cropped title block region, or None if not found

        Memory model: keeps the fitz document open for efficient text extraction
        while converting images one page at a time via pdf2image.  After each
        yield, local references are dropped and gc.collect() is called.

        Args:
            pdf_bytes: PDF file as bytes

        Yields:
            Tuple of (PIL Image, page_text str, title_block_crop PIL Image or None)
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            for page_index in range(len(doc)):
                page_num = page_index + 1

                # Convert this single page to an image
                page_images = convert_from_bytes(
                    pdf_bytes,
                    dpi=self.dpi,
                    fmt=self.fmt,
                    poppler_path=self.poppler_path,
                    first_page=page_num,
                    last_page=page_num,
                )
                image = page_images[0]
                del page_images

                # ── Super Skill 2: OpenCV Pre-processing ──────────────────────
                if self.preprocess:
                    image = self.preprocess_image(image)

                # ── Super Skill 3: Smart Cropping (Title Block) ───────────────
                title_block_crop = self._crop_title_block(image)

                # ── Super Skill 1: Enhanced Hybrid Text Extraction ────────────
                fitz_page = doc[page_index]
                page_text = self._extract_page_text_from_fitz_page(fitz_page)

                yield image, page_text, title_block_crop

                del image, page_text, title_block_crop
                gc.collect()
        finally:
            doc.close()

    # ------------------------------------------------------------------
    # Super Skill 2: OpenCV Pre-processing
    # ------------------------------------------------------------------

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Apply a three-stage OpenCV enhancement pipeline to improve Gemini accuracy:

        1. CLAHE (Contrast Limited Adaptive Histogram Equalization) on the LAB
           L-channel — boosts local contrast without blowing out highlights,
           making faint dimension lines and small text stand out.
        2. Deskew via Hough line transform — detects the dominant near-horizontal
           line angle and rotates to correct skew > 0.5°, which is common in
           scanned architectural drawings.
        3. Unsharp mask sharpening — increases perceived sharpness of fine lines
           and annotation text at no quality cost.

        Falls back to the original image on any exception so the pipeline can
        never crash the extraction loop.

        Args:
            image: PIL Image (any mode)

        Returns:
            Enhanced PIL Image in RGB mode
        """
        if not _CV2_AVAILABLE:
            return image
        try:
            # PIL → numpy BGR
            img_np = np.array(image.convert("RGB"))
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            # 1. CLAHE on LAB L-channel
            lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
            l_chan, a_chan, b_chan = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_clahe = clahe.apply(l_chan)
            lab_enhanced = cv2.merge([l_clahe, a_chan, b_chan])
            img_enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

            # 2. Deskew via Hough lines on grayscale
            gray = cv2.cvtColor(img_enhanced, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180,
                threshold=100, minLineLength=100, maxLineGap=10
            )
            if lines is not None:
                angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if x2 != x1:
                        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                        if abs(angle) < 45:  # near-horizontal lines only
                            angles.append(angle)
                if angles:
                    median_angle = float(np.median(angles))
                    if abs(median_angle) > 0.5:  # only correct if skew > 0.5°
                        h, w = img_enhanced.shape[:2]
                        M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
                        img_enhanced = cv2.warpAffine(
                            img_enhanced, M, (w, h),
                            flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_REPLICATE,
                        )

            # 3. Unsharp mask
            gaussian = cv2.GaussianBlur(img_enhanced, (0, 0), 2.0)
            img_sharp = cv2.addWeighted(img_enhanced, 1.5, gaussian, -0.5, 0)

            # numpy BGR → PIL RGB
            img_rgb = cv2.cvtColor(img_sharp, cv2.COLOR_BGR2RGB)
            return Image.fromarray(img_rgb)

        except Exception as e:
            print(f"Preprocessing warning (non-fatal, using original): {e}")
            return image

    # ------------------------------------------------------------------
    # Super Skill 3: Smart Cropping (Title Block Isolation)
    # ------------------------------------------------------------------

    def _crop_title_block(self, image: Image.Image) -> Optional[Image.Image]:
        """
        Isolate the title block region from an architectural drawing.

        Strategy:
        - Primary   : bottom-right 35 % × 20 % of the page (AS/NZS, ISO, most CAD)
        - Fallback  : bottom-left  35 % × 20 % of the page (some US / UK formats)
        - Validation: if the mean pixel value of the crop is ≥ 250 (pure white /
          blank), that region is skipped and we try the fallback.

        Args:
            image: Full-page PIL Image

        Returns:
            Cropped PIL Image, or None if both candidate regions appear blank
        """
        try:
            w, h = image.size
            crop_w = int(w * 0.35)
            crop_h = int(h * 0.20)

            # Primary: bottom-right
            br_crop = image.crop((w - crop_w, h - crop_h, w, h))
            br_arr = np.array(br_crop.convert("L")) if _CV2_AVAILABLE else None
            if br_arr is None or br_arr.mean() < 250:
                return br_crop

            # Fallback: bottom-left
            bl_crop = image.crop((0, h - crop_h, crop_w, h))
            bl_arr = np.array(bl_crop.convert("L")) if _CV2_AVAILABLE else None
            if bl_arr is None or bl_arr.mean() < 250:
                return bl_crop

            return None  # Both regions appear blank — no crop sent

        except Exception as e:
            print(f"Title block crop warning (non-fatal): {e}")
            return None

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

        Super Skill 1 — Enhanced Hybrid Text Extraction:
        - Structural key-value pairs (SCALE: 1:100, DATE: 01/01/2024, etc.)
          are extracted first via regex and always included in full (≤ 2 000 chars).
        - Block-level body text is extracted, sorted in reading order, and
          truncated to 6 000 chars (raised from 4 000).
        - Table reconstruction via multi-span line detection is unchanged.
        - Total output capped at 8 000 chars.

        Args:
            page: fitz.Page object

        Returns:
            Extracted text string (max 8 000 chars)
        """
        try:
            # ── Key-Value pairs (always included, captures title block fields) ──
            kv_text = self._extract_key_value_pairs(page)

            # ── Body text blocks in reading order ────────────────────────────
            text_blocks = page.get_text("blocks")
            text_blocks_sorted = sorted(text_blocks, key=lambda b: (round(b[1] / 50), b[0]))

            lines = []
            for block in text_blocks_sorted:
                if block[6] == 0:  # block_type 0 = text (1 = image)
                    raw = block[4].strip()
                    if raw:
                        lines.append(raw)

            body_text = "\n".join(lines)
            if len(body_text) > 6000:
                body_text = body_text[:6000] + "\n[BODY TEXT TRUNCATED at 6 000 chars]"

            # ── Table reconstruction ──────────────────────────────────────────
            table_text = self._extract_tables(page)

            # ── Assemble final output ─────────────────────────────────────────
            parts = []
            if kv_text:
                parts.append("[KEY-VALUE PAIRS DETECTED]\n" + kv_text)
            if body_text:
                parts.append(body_text)
            if table_text:
                parts.append("\n[TABLES DETECTED]\n" + table_text)

            raw_text = "\n\n".join(parts)

            # Hard cap on total output
            if len(raw_text) > 8000:
                raw_text = raw_text[:8000] + "\n[TRUNCATED — text exceeded 8 000 char limit]"

            return raw_text

        except Exception:
            return ""

    def _extract_key_value_pairs(self, page) -> str:
        """
        Detect structured key-value pairs in the page text using regex.

        Matches patterns common in architectural title blocks:
          SCALE: 1:100
          DATE = 01/01/2024
          DRG NO: A101
          CLIENT  ACME Corp       (label then value on same block, separated by spaces)

        Args:
            page: fitz.Page object

        Returns:
            Formatted string of key-value pairs (max 2 000 chars), or ""
        """
        try:
            raw = page.get_text("text")
            # Pattern: ALL-CAPS label (2–30 chars) followed by : or = and a value
            kv_pattern = re.compile(
                r'([A-Z][A-Z0-9 /\-\.]{1,29}?)\s*[:=]\s*([^\n]{1,80})',
                re.MULTILINE,
            )
            pairs = kv_pattern.findall(raw)
            if not pairs:
                return ""
            lines = [
                f"{k.strip()}: {v.strip()}"
                for k, v in pairs
                if v.strip() and len(v.strip()) > 0
            ]
            result = "\n".join(lines[:60])  # at most 60 pairs
            return result[:2000]
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

    def render_page_with_highlight(
        self,
        pdf_bytes: bytes,
        page_num: int,
        bounding_box: List[float],
        highlight_type: str = "region",
        dpi: int = 200,
    ) -> Image.Image:
        """
        Render a single PDF page and draw a highlight overlay over the bounding box.

        The page is converted to grayscale so the colored overlay stands out clearly.
        Preprocessing (CLAHE, deskew) is applied so pixel coordinates match those
        seen by Gemini during extraction.

        Args:
            pdf_bytes: PDF file as bytes
            page_num: 1-based page number to render
            bounding_box: [ymin, xmin, ymax, xmax] in 0-1000 normalized coordinates
            highlight_type: "region" — semi-transparent yellow fill (alpha 0.35);
                            "text"   — green outline rectangle only
            dpi: Render resolution (default 200 — lower for speed at view time)

        Returns:
            PIL Image with highlight overlay
        """
        def _plain_render():
            imgs = convert_from_bytes(
                pdf_bytes, dpi=dpi, fmt="png",
                poppler_path=self.poppler_path,
                first_page=page_num, last_page=page_num,
            )
            return imgs[0]

        if not _CV2_AVAILABLE:
            return _plain_render()

        try:
            page_images = convert_from_bytes(
                pdf_bytes, dpi=dpi, fmt="png",
                poppler_path=self.poppler_path,
                first_page=page_num, last_page=page_num,
            )
            image = page_images[0]
            del page_images

            # Apply the same preprocessing pipeline used during extraction so
            # the bounding box coordinates Gemini returned align with the pixels.
            if self.preprocess:
                image = self.preprocess_image(image)

            w, h = image.size
            ymin, xmin, ymax, xmax = bounding_box

            # Map 0-1000 normalized coordinates to pixel coordinates
            x1 = int(xmin / 1000 * w)
            y1 = int(ymin / 1000 * h)
            x2 = int(xmax / 1000 * w)
            y2 = int(ymax / 1000 * h)

            # PIL → numpy BGR
            img_np = np.array(image.convert("RGB"))
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            # Grayscale base with 3 channels so color overlays work
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            img_display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            if highlight_type == "region":
                # Semi-transparent yellow filled rectangle — black lines show through
                overlay = img_display.copy()
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 255), -1)  # BGR yellow
                img_display = cv2.addWeighted(overlay, 0.35, img_display, 0.65, 0)
            else:
                # "text" — clean green outline only, 3px thick
                cv2.rectangle(img_display, (x1, y1), (x2, y2), (0, 200, 100), 3)

            # numpy BGR → PIL RGB
            img_rgb = cv2.cvtColor(img_display, cv2.COLOR_BGR2RGB)
            return Image.fromarray(img_rgb)

        except Exception as e:
            print(f"render_page_with_highlight warning (non-fatal): {e}")
            return _plain_render()

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
