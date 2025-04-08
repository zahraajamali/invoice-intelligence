from pdf2image import convert_from_path
import pytesseract
import os
import re
from pprint import pprint
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

from neo4j import GraphDatabase
import copy
import json

import cv2
import numpy as np
from PIL import Image

import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# simple ocr but not accurate

# # Convert PDF to list of images (1 per page)
# pages = convert_from_path("invoice.pdf", dpi=200)

# # Create output folder if it doesn't exist
# output_dir = "ocr_output"
# os.makedirs(output_dir, exist_ok=True)

# # Loop through pages and OCR each one
# for page_num, image in enumerate(pages):
#     text = pytesseract.image_to_string(image,config="--psm 6 ")
#     print(f"--- Page {page_num + 1} ---")
#     print(text)

#     # Write text to file
#     output_path = os.path.join(output_dir, f"page{page_num + 1}.txt")
#     with open(output_path, "w", encoding="utf-8") as f:
#         f.write(text)

# with open("ocr_output/page1.txt", "r", encoding="utf-8") as file:
#     raw_text = file.read()


# Step 1: Convert PDF to images
pages = convert_from_path("invoice2.pdf")

# Step 2: Output folder setup
output_dir = "ocr_output"
os.makedirs(output_dir, exist_ok=True)

def smart_preprocess(pil_image):
    """Mild enhancement only - avoids overprocessing"""
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

# Step 3: Process each page
for i, page in enumerate(pages):
    processed = smart_preprocess(page)

    # Use a better Tesseract config
    ocr_text = pytesseract.image_to_string(processed, config="--psm 6 ")

    # Save OCR result
    with open("ocr_output/page2.txt", "w", encoding="utf-8") as f:
        f.write(ocr_text)

    

# # lang chain step

with open("ocr_output/page2.txt", "r", encoding="utf-8") as f:
    invoice_text = f.read()

llm = ChatOpenAI(openai_api_key=openai_api_key, temperature=0,model="gpt-4o")

prompt = f"""
You are a professional invoice analyzer and data extractor.

Read the following unstructured invoice text and return all relevant data in a well-structured JSON format. 
**Note:** In every invoice, the client is always **DEL-INTERNET TELECOM, S.L.U.** — so only extract provider information and invoice details.

If any field is not found or is not applicable, return `null` for that field.

✅ The required JSON format is:

{{
  "invoice_number": ...,
  "invoice_date": ...,
  "provider": {{
    "name": ...,
    "address": ...,
    "contact": {{
      "email": ...,
      "phone": ...,
      "fax": ...,
      "mobile": ...
    }},
    "C.I.F.": ...
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

response = llm.invoke(prompt)
print(response.content)
# invoice_data = eval(response.content)
raw_json = response.content

# Remove the markdown-style ```json wrapper
clean_json = re.sub(r"^```json\s*|\s*```$", "", raw_json.strip())

# Now parse it as a real Python object
invoice_data = json.loads(clean_json)




# Neo4j driver
uri = "bolt://localhost:7687"
username = "neo4j"
password = "del-ai123"
# del-ai123

driver = GraphDatabase.driver(uri, auth=(username, password))




def flatten_oid_fields(data):
    """Recursively replace Mongo-style ObjectId and Date fields with primitive values."""
    if isinstance(data, dict):
        if "$oid" in data and len(data) == 1:
            return data["$oid"]
        elif "$date" in data and len(data) == 1:
            return data["$date"]
        else:
            return {k: flatten_oid_fields(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [flatten_oid_fields(i) for i in data]
    else:
        return data


# Load your JSON files
with open("inventory.suppliers.json", "r") as f:
    raw_clients = json.load(f)
    clients = [flatten_oid_fields(c) for c in raw_clients]

with open("inventory.products.json", "r") as f:
    raw_items = json.load(f)
    items = [flatten_oid_fields(i) for i in raw_items]

# ---- NEO4J INSERTIONS ----

def create_clients(tx, clients):
     for client in clients:
        tx.run("""
            MERGE (c:Client {company: $company})
            SET c.commercial_name = $commercial_name,
                c.description = $description,
                c.emails = $emails,
                c.phones = $phones,
                c.creator_id = $creator_id,
                c.created_at = $created_at,
                c.updated_at = $updated_at
        """,
        company=client["company"],
        commercial_name=client.get("commercial_name", ""),
        description=client.get("description", ""),
        emails=client.get("emails", []),
        phones=client.get("phones", []),
        creator_id=client.get("creator"),
        created_at=client.get("createdAt"),
        updated_at=client.get("updatedAt")
        )



def create_items(tx, items):
      for item in items:
        warehouse_ids = [w.get("warehouseId") for w in item.get("warehouses", [])]

        tx.run("""
            MERGE (i:Item {name: $name})
            SET i.englishName = $englishName,
                i.totalProductQuantity = $quantity,
                i.unit = $unit,
                i.threshold = $threshold,
                i.category_id = $category_id,
                i.creator_id = $creator_id,
                i.warehouse_ids = $warehouse_ids
        """,
        name=item["name"],
        englishName=item.get("englishName", ""),
        quantity=item.get("totalProductQuantity", 0),
        unit=item.get("unit", ""),
        threshold=item.get("threshold", 0),
        category_id=item.get("category"),
        creator_id=item.get("creator"),
        warehouse_ids=warehouse_ids
        )



# ---- RUN TRANSACTIONS ----
with driver.session() as session:
    session.execute_write(create_clients, clients)
    session.execute_write(create_items, items)



# ----------- QUERY HELPERS --------------

def find_supplier(tx, company_name,client_email):
    result = tx.run("""
        MATCH (c:Client)
        WITH c,
            apoc.text.distance(toLower(c.company), toLower($company_name)) AS name_to_company,
            apoc.text.distance(toLower(c.commercial_name), toLower($company_name)) AS name_to_commercial,
            apoc.text.distance(toLower(c.company), toLower($client_email)) AS email_to_company,
            apoc.text.distance(toLower(c.commercial_name), toLower($client_email)) AS email_to_commercial

        WITH c,
            CASE WHEN name_to_company < name_to_commercial THEN name_to_company ELSE name_to_commercial END AS name_score,
            CASE WHEN email_to_company < email_to_commercial THEN email_to_company ELSE email_to_commercial END AS email_score

        WITH c, (name_score + email_score) / 2 AS final_score
        ORDER BY final_score ASC
        RETURN c, final_score
        LIMIT 1
    """, company_name=company_name, client_email=client_email)

    record = result.single()
    if record and record["final_score"] < 10:
        return dict(record["c"])
    return None
    


def find_item(tx, description):
    result = tx.run("""
        MATCH (i:Item)
        WITH i, apoc.text.distance(toLower(i.name), toLower($desc)) AS score
        ORDER BY score ASC
        RETURN i, score
        LIMIT 1
    """, desc=description)
    
    record = result.single()
    
    if record and record["score"] < 10:  # adjust this threshold if needed
        return dict(record["i"])
    
    return None


# ----------- PROCESS INVOICE --------------

def enrich_invoice(invoice):
    enriched_invoice = copy.deepcopy(invoice)
    with driver.session() as session:

        # Search for supplier
        supplier_data = session.execute_read(find_supplier, invoice["provider"]["name"],invoice["provider"]["contact"]["email"])
        enriched_invoice["supplier"] = supplier_data if supplier_data else None

        # Search for each item
        enriched_items = []
        for item in invoice["items"]:
            product_data = session.execute_read(find_item, item["description"])
            enriched_item = item.copy()
            enriched_item["product"] = product_data if product_data else None
            enriched_items.append(enriched_item)

        enriched_invoice["items"] = enriched_items

    return enriched_invoice


# ----------- RUN IT ----------------

enriched = enrich_invoice(invoice_data)
print(enriched)

with open("enriched_invoice2.json", "w", encoding="utf-8") as f:
    json.dump(enriched, f, indent=2, ensure_ascii=False)