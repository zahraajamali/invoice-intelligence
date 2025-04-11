import re
import json

from langchain_openai import ChatOpenAI


def read_invoice_text(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def build_invoice_extraction_prompt(invoice_text):
    
    return f"""
        You are a professional invoice analyzer and data extractor.

        Read the following unstructured invoice text and return all relevant data in a well-structured JSON format. 
        **Note:** In every invoice, the client is always **DEL-INTERNET TELECOM, S.L.U.** with this information {{address:Pz Mercat La Cava nº 1 Local Delinternet  
43580 DELTEBRE  
Tarragona  
N.I.F : B55606446}} — so only extract provider information and invoice details.

        If any field is not found or is not applicable, return `null` for that field.

        ✅ The required JSON format is:

        {{
          "invoice_number": ..., // Also appears as "NUM. FACTURA", "NÚMERO FACTURA"
          "invoice_date": ..., // Also appears as "DATA FACTURA", "FECHA FACTURA"
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
            "IRPF_rate":...,
            "IRPF_amount":...,
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


def clean_llm_response(content):
    return re.sub(r"^```json\s*|\s*```$", "", content.strip())


def extract_invoice_data_from_gpt(openai_api_key, invoice_file_path):
    invoice_text = read_invoice_text(invoice_file_path)
    if(invoice_text):
      prompt = build_invoice_extraction_prompt(invoice_text)

      llm = ChatOpenAI(openai_api_key=openai_api_key, temperature=0, model="gpt-4o")
      response = llm.invoke(prompt)

      cleaned = clean_llm_response(response.content)
      invoice_data = json.loads(cleaned)
      return invoice_data
    else:
        return None
    


