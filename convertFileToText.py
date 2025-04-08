import cv2
import numpy as np

import pytesseract
from PIL import Image
from pdf2image import convert_from_path


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

    return Image.fromarray(sharpened)


def convert_file_to_text(fileName):

  pages = convert_from_path(f"invoicesFile/{fileName}.pdf")

  for i, page in enumerate(pages):
      processed = smart_preprocess(page)

      ocr_text = pytesseract.image_to_string(processed, config="--psm 6 ")

      # Save OCR result
      with open(f"ocr_output/{fileName}/page{i}.txt", "w", encoding="utf-8") as f:
          f.write(ocr_text)

   