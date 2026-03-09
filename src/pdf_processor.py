"""
PDF processing utilities for converting pages to high-resolution images.
"""

import os
import sys
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
from typing import List


class PDFProcessor:
    """Handles PDF to image conversion."""

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

    def convert_pdf_file(self, file_path: str) -> List[Image.Image]:
        """
        Convert all pages of a PDF file to images.

        Args:
            file_path: Path to the PDF file

        Returns:
            List of PIL Image objects
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        try:
            images = convert_from_path(
                file_path,
                dpi=self.dpi,
                fmt=self.fmt,
                poppler_path=self.poppler_path
            )
            return images
        except Exception as e:
            raise RuntimeError(f"Error converting PDF: {str(e)}")

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
