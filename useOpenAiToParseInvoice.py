import openai
import json
import os
import logging
import requests
import re

import base64
from pdf2image import convert_from_bytes
from io import BytesIO
from PIL import Image

def pdf_to_base64_image(pdf_bytes):
    """Convert the first page of a PDF to base64-encoded PNG image."""
    images = convert_from_bytes(pdf_bytes)
    buffer = BytesIO()
    images[0].save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

def clean_llm_json_response(response_content: str) -> str:
    """Removes triple backticks and ensures clean JSON string."""
    return re.sub(r"^```json\s*|\s*```$", "", response_content.strip())

def extract_invoice_data_from_pdf(pdf_bytes: bytes) -> dict | None:
    openai.api_key = os.getenv("OPENAI_API_KEY")

    try:
        image_base64 = pdf_to_base64_image(pdf_bytes)

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional Spanish invoice analyzer and data extractor."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                """ 
Read the following unstructured invoice text and return all relevant data in a well-structured JSON format. 
**Note:** In every invoice, the client is always **DEL-INTERNET TELECOM, S.L.U.** with this information:
{{
  address: Pz Mercat La Cava nº 1 Local Delinternet  
  43580 DELTEBRE  
  Tarragona  
  N.I.F : B55606446
}} — so only extract **provider information** and **invoice details**.

If any field is not found or is not applicable, return `null` for that field.

✅ The required JSON format is:

{{
  "invoice_number": ..., // Also appears as "NUM. FACTURA", "NÚMERO FACTURA"
  "invoice_date": ...,   // Also appears as "DATA FACTURA", "FECHA FACTURA"
  "provider": {{
    "name": ...,
    "address": ...,
    "contact": {{
      "email": ...,
      "phone": ...,
      "fax": ...,
      "mobile": ...
    }},
    "VAT_NUMBER/NIE/CIF": ...
  }},
  "items": [
    {{
      "quantity": ...,
      "description": ...,
      "project": ...,
      "unit_price": ...,
      "total": ...
    }}
  ],
  "total": {{
    "base_amount": ...,
    "VAT_rate": ...,
    "VAT_amount": ...,
    "IRPF_rate": ...,
    "IRPF_amount": ...,
    "total_invoice": ...
  }},
  "description": "<Any extra relevant information, notes, or context from the invoice not covered by the fields above.>"
}}

---
"""
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_base64
                            }
                        }
                    ]
                }
            ]
        )

        reply = response.choices[0].message.content
        cleaned_reply = clean_llm_json_response(reply)
        print(cleaned_reply)

        try:
            return json.loads(cleaned_reply)
        except json.JSONDecodeError:
            print("❌ GPT-4o could not parse JSON, returning raw output", e)
            return None

    except Exception as e:
        print("❌ GPT-4o Vision extraction failed:", e)
        return None

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# if __name__ == "__main__":
#     API_KEY = os.getenv("OPENAI_API_KEY")  # Replace with your OpenAI API key
#     # PDF_PATH = "path/to/your/invoice.pdf"
#     hub_api_token = os.getenv("HUB_API_TOKEN")
#     pdf_url = "https://inventory-server.prd.delinternet.com/api/v1/files/79c4a4c73d75e82d76768d0afbe01b0a715da6fe4c576f3d5c2f2515e53865ae.pdf"

#     logger.info(f"📥 Downloading PDF from: {pdf_url}")
#     headers = {"Authorization": hub_api_token}
#     response = requests.get(pdf_url, headers=headers)
#     response.raise_for_status()

#     logger.info("✅ PDF downloaded successfully. Converting to images...")
#     pdf_bytes = response.content

#     result = extract_invoice_data_from_pdf(API_KEY, pdf_bytes)

#     if result:
#         print(json.dumps(result, indent=2, ensure_ascii=False))
#     else:
#         print("❌ No data extracted.")