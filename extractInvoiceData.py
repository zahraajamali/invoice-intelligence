import re
import json
from langchain_openai import ChatOpenAI


INVOICE_EXTRACTION_PROMPT_TEMPLATE = """
You are a professional invoice analyzer and data extractor.

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

🧾 Here is the invoice text:
---
{invoice_text}
---
"""


def read_text_file(path: str) -> str:
    """Reads and returns the content of a text file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_invoice_extraction_prompt(invoice_text: str) -> str:
    """Fills the invoice prompt template with the provided invoice text."""
    return INVOICE_EXTRACTION_PROMPT_TEMPLATE.format(invoice_text=invoice_text)


def clean_llm_json_response(response_content: str) -> str:
    """Removes triple backticks and ensures clean JSON string."""
    return re.sub(r"^```json\s*|\s*```$", "", response_content.strip())


def extract_invoice_data_from_gpt(openai_api_key: str, invoice_text: str) -> dict | None:
    """
    Extract structured invoice data from a text file using GPT.
    
    Returns a dictionary if successful, or None if the file is empty or extraction fails.
    """
    if not invoice_text:
        return None

    prompt = build_invoice_extraction_prompt(invoice_text)

    llm = ChatOpenAI(
        openai_api_key=openai_api_key,
        temperature=0,
        model="gpt-4o"
    )

    try:
        response = llm.invoke(prompt)
        cleaned_json_str = clean_llm_json_response(response.content)
        return json.loads(cleaned_json_str)
    except Exception as e:
        print("❌ Failed to extract invoice data:", e)
        return None
