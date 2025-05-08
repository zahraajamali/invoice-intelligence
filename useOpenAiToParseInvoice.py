import openai
import json
import os
import logging
import requests
import re
import time

import base64
from pdf2image import convert_from_bytes
from io import BytesIO
from PIL import Image


invoice_schema = {
    "name": "extract_invoice_data",
    "description": "Extract structured invoice data from an unstructured invoice text.",
    "parameters": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "invoice_date": {"type": "string"},
            "provider": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {"type": "string"},
                    "contact": {
                        "type": "object",
                        "properties": {
                            "email": {"type": ["string", "null"]},
                            "phone": {"type": ["string", "null"]},
                            "fax": {"type": ["string", "null"]},
                            "mobile": {"type": ["string", "null"]}
                        },
                        "required": ["email", "phone", "fax", "mobile"]
                    },
                    "VAT_NUMBER/NIE/CIF": {"type": "string"}
                },
                "required": ["name", "address", "contact", "VAT_NUMBER/NIE/CIF"]
            },
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "quantity": {"type": "number"},
                        "description": {"type": "string"},
                        "unit": {"type": ["string", "null"]},
                        "unit_price": {"type": "number"},
                        "total": {"type": "number"}
                    },
                    "required": ["quantity", "description", "unit_price", "total", "project"]
                }
            },
            "total": {
                "type": "object",
                "properties": {
                    "base_amount": {"type": "number"},
                    "VAT_rate": {"type": "number"},
                    "VAT_amount": {"type": "number"},
                    "IRPF_rate": {"type": ["number", "null"]},
                    "IRPF_amount": {"type": ["number", "null"]},
                    "total_invoice": {"type": "number"}
                },
                "required": ["base_amount", "VAT_rate", "VAT_amount", "IRPF_rate", "IRPF_amount", "total_invoice"]
            },
            "description": {"type": "string"}
        },
        "required": ["invoice_number", "invoice_date", "provider", "items", "total", "description"]
    }
}

def pdf_to_base64_image(pdf_bytes):
    """Convert all pages of a PDF to a list of base64-encoded PNG images."""
    images = convert_from_bytes(pdf_bytes)
    base64_images = []
    for image in images:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        base64_images.append(f"data:image/png;base64,{img_str}")
    return base64_images

def clean_llm_json_response(response_content: str) -> str:
    """Removes triple backticks and ensures clean JSON string."""
    return re.sub(r"^```json\s*|\s*```$", "", response_content.strip())

def extract_invoice_data_from_pdf(pdf_bytes: bytes) -> dict | None:
    openai.api_key = os.getenv("OPENAI_API_KEY")

    try:
        image_base64_list = pdf_to_base64_image(pdf_bytes)
        t1 = time.perf_counter()

        messages = []

        messages.append({
            "role": "system",
            "content": "You are a professional Spanish invoice analyzer and data extractor."
        })

        messages.append({
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
                        """
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64_list[0] 
                    }
                }
            ]
        })

        for img_str in image_base64_list[1:]:
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": img_str
                        }
                    }
                ]
            })

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            functions=[invoice_schema],
            function_call={"name": "extract_invoice_data"},
            temperature=0
        )

        t2 = time.perf_counter()
        print(f"⏱️ OpenAI API call time: {t2 - t1:.2f} seconds")

        function_response = response.choices[0].message.function_call

        if function_response and function_response.arguments:
            parsed_args = json.loads(function_response.arguments)
            return parsed_args
        else:
            print("❌ GPT-4o could not parse JSON, returning raw output")
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
