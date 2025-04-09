import cv2
import os
import numpy as np
import requests
from pdf2image import convert_from_bytes

import pytesseract
from PIL import Image
from pdf2image import convert_from_path


def detect_rotation(pil_image):
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    try:
        osd = pytesseract.image_to_osd(img, config='--psm 0')
        angle = int([line for line in osd.split('\n') if 'Rotate:' in line][0].split(':')[1])
        return angle
    except Exception:
        return 0  # fallback if detection fails


def smart_preprocess(pil_image):
    # Convert PIL to OpenCV image
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Slight blur reduction using sharpening kernel
    kernel = np.array([[0, -1, 0], 
                       [-1, 5, -1], 
                       [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)

     # Adaptive thresholding for better OCR contrast
    thresh = cv2.adaptiveThreshold(
        sharpened, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    return Image.fromarray(thresh)


def convert_file_to_text(api_url, output_path,token):
    try:
        headers = {
        "Authorization": token
        }
        print(headers)
        response = requests.get(api_url,headers=headers)
        response.raise_for_status()

        print(response)

        # Convert PDF bytes to images
        pdf_bytes = response.content
        pages = convert_from_bytes(pdf_bytes)

        os.makedirs(output_path, exist_ok=True)

        for i, page in enumerate(pages):
            angle = detect_rotation(page)
            print("angel...",angle)
            if angle != 0:
                page = page.rotate(-angle, expand=True)

            processed = smart_preprocess(page)
            ocr_text = pytesseract.image_to_string(processed, config="--psm 6 --oem 3")

            with open(f"{output_path}/page{i+1}.txt", "w", encoding="utf-8") as f:
                f.write(ocr_text)

        print("OCR processing complete.")

    except requests.exceptions.RequestException as e:
        print(f"Failed to download PDF: {e}")


   