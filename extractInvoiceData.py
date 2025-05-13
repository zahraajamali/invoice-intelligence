import re
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# ---------------- STEP 2: Function Schema ---------------- #
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
                        "quantity": {"type": "string"},
                        "description": {"type": "string"},
                        "project": {"type": ["string", "null"]},
                        "unit_price": {"type": "string"},
                        "total": {"type": "string"}
                    },
                    "required": ["quantity", "description", "unit_price", "total", "project"]
                }
            },
            "total": {
                "type": "object",
                "properties": {
                    "base_amount": {"type": "string"},
                    "VAT_rate": {"type": "string"},
                    "VAT_amount": {"type": "string"},
                    "IRPF_rate": {"type": ["string", "null"]},
                    "IRPF_amount": {"type": ["string", "null"]},
                    "total_invoice": {"type": "string"}
                },
                "required": ["base_amount", "VAT_rate", "VAT_amount", "IRPF_rate", "IRPF_amount", "total_invoice"]
            },
            "description": {"type": "string"}
        },
        "required": ["invoice_number", "invoice_date", "provider", "items", "total", "description"]
    }
}


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

    prompt = f"""You are a professional invoice analyzer and data extractor.

Read the following unstructured invoice text and return all relevant data in a well-structured JSON format. 
**Note:** In every invoice, the client is always **DEL-INTERNET TELECOM, S.L.U.** with this information:
{{
  address: Pz Mercat La Cava nº 1 Local Delinternet  
  43580 DELTEBRE  
  Tarragona  
  N.I.F : B55606446
}} — so only extract **provider information** and **invoice details**.\n\n---\n{invoice_text}\n---"""

    llm = ChatOpenAI(
        openai_api_key=openai_api_key,
        temperature=0,
        model="gpt-4o"
    )

    try:
      response = llm.invoke(
            [HumanMessage(content=prompt)],
            functions=[invoice_schema]
        )
      if "function_call" in response.additional_kwargs:
          args = json.loads(response.additional_kwargs["function_call"]["arguments"])
          return json.dumps(args, indent=2)
      else:
          print("❌ No structured response returned.")
          return None
    except Exception as e:
      print("❌ Error during GPT call:", e)
      return None


