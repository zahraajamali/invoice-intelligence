import os
import cv2
import numpy as np
import requests
import pytesseract
import logging

from PIL import Image
from pdf2image import convert_from_bytes

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def detect_rotation(pil_image: Image.Image) -> int:
    """Detect rotation angle using Tesseract OSD."""
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    try:
        osd = pytesseract.image_to_osd(img, config="--psm 0")
        angle_line = next(line for line in osd.split("\n") if "Rotate:" in line)
        angle = int(angle_line.split(":")[1].strip())
        logger.info(f"🔄 Detected rotation: {angle}°")
        return angle
    except Exception as e:
        logger.warning(f"⚠️ Failed to detect rotation: {e}")
        return 0  # fallback


def smart_preprocess(pil_image: Image.Image) -> Image.Image:
    """Enhance image for better OCR using grayscale and adaptive thresholding."""
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15, 8
    )

    return Image.fromarray(thresh)


def convert_bytes_to_text(pdf_bytes: bytes) -> list[str]:
    """Convert a PDF (given as bytes) into text per page (in memory)."""
    try:
        logger.info("📄 Converting PDF bytes to images...")
        pages = convert_from_bytes(pdf_bytes)
        all_texts = []

        for i, page in enumerate(pages):
            logger.info(f"📝 Processing page {i + 1}...")
            angle = detect_rotation(page)

            if angle != 0:
                page = page.rotate(-angle, expand=True)

            processed_image = smart_preprocess(page)
            ocr_text = pytesseract.image_to_string(
                processed_image, config="--psm 4 --oem 3"
            )

            all_texts.append(ocr_text)
            logger.info(f"✅ OCR complete for page {i + 1}")

        logger.info("🎉 All pages processed successfully.")
        return all_texts

    except Exception as e:
        logger.error(f"❌ Error during in-memory OCR processing: {e}", exc_info=True)
        raise


def convert_file_to_text(api_url: str, token: str):
    """Download a PDF from a URL, process it with OCR, and save each page's text."""
    try:
        logger.info(f"📥 Downloading PDF from: {api_url}")
        headers = {"Authorization": token}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        logger.info("✅ PDF downloaded successfully. Converting to images...")
        pdf_bytes = response.content
        pages = convert_from_bytes(pdf_bytes)

        for i, page in enumerate(pages):
            logger.info(f"📝 Processing page {i + 1}...")
            angle = detect_rotation(page)

            if angle != 0:
                page = page.rotate(-angle, expand=True)

            processed_image = smart_preprocess(page)
            ocr_text = pytesseract.image_to_string(
                processed_image, config="--psm 4 --oem 3"
            )

            logger.info("✅ OCR processing complete.")
            return ocr_text

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to download PDF: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"❌ Unexpected error during OCR processing: {e}", exc_info=True)
