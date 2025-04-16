import os
import cv2
import numpy as np
import requests
import pytesseract

from PIL import Image
from pdf2image import convert_from_bytes


def detect_rotation(pil_image: Image.Image) -> int:
    """Detect rotation angle using Tesseract OSD."""
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    try:
        osd = pytesseract.image_to_osd(img, config="--psm 0")
        angle_line = next(line for line in osd.split("\n") if "Rotate:" in line)
        return int(angle_line.split(":")[1].strip())
    except Exception:
        return 0  # fallback if detection fails


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
        print("📄 Converting PDF bytes to images...")
        pages = convert_from_bytes(pdf_bytes)
        all_texts = []

        for i, page in enumerate(pages):
            print(f"\n📝 Processing page {i + 1}...")
            angle = detect_rotation(page)
            print(f"🔄 Detected rotation: {angle}°")

            if angle != 0:
                page = page.rotate(-angle, expand=True)

            processed_image = smart_preprocess(page)
            ocr_text = pytesseract.image_to_string(
                processed_image, config="--psm 4 --oem 3"
            )

            all_texts.append(ocr_text)
            print(f"✅ OCR complete for page {i + 1}")

        print("🎉 All pages processed successfully.")
        return all_texts

    except Exception as e:
        print(f"❌ Error during in-memory OCR processing: {e}")
        raise


def convert_file_to_text(api_url: str, output_path: str, token: str):
    """Download a PDF from a URL, process it with OCR, and save each page's text."""
    try:
        print(f"📥 Downloading PDF from: {api_url}")
        headers = {"Authorization": token}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        print("✅ PDF downloaded successfully. Converting to images...")
        pdf_bytes = response.content
        pages = convert_from_bytes(pdf_bytes)

        os.makedirs(output_path, exist_ok=True)

        for i, page in enumerate(pages):
            print(f"\n📝 Processing page {i + 1}...")
            angle = detect_rotation(page)
            print(f"🔄 Detected rotation: {angle}°")

            if angle != 0:
                page = page.rotate(-angle, expand=True)

            processed_image = smart_preprocess(page)
            ocr_text = pytesseract.image_to_string(processed_image, config="--psm 4 --oem 3")

            text_output_path = os.path.join(output_path, f"page{i + 1}.txt")
            with open(text_output_path, "w", encoding="utf-8") as f:
                f.write(ocr_text)

            print(f"✅ Saved OCR output to: {text_output_path}")

        print("\n🎉 OCR processing complete.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to download PDF: {e}")
    except Exception as e:
        print(f"❌ Unexpected error during OCR processing: {e}")
