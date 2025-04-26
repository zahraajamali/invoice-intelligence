# app/services/invoice_processor.py

import openai
import json
import os
import io
import time
import re

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

openai.api_key = OPENAI_API_KEY

# Helper to clean GPT responses
def clean_assistant_json(response_text: str) -> str:
    """
    Cleans triple backticks ``` or ```json from Assistant's reply if exists.
    """
    if not response_text:
        return ""
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_text.strip(), flags=re.MULTILINE)
    return cleaned.strip()

# Helper to validate extracted JSON structure
def validate_invoice_structure(data: dict) -> bool:
    """
    Ensures the response matches expected invoice JSON structure.
    """
    required_top_fields = ["invoice_number", "invoice_date", "provider", "items", "total", "description"]
    required_provider_fields = ["name", "address", "contact", "VAT_NUMBER/NIE/CIF"]
    required_contact_fields = ["email", "phone", "fax", "mobile"]
    required_total_fields = ["base_amount", "VAT_rate", "VAT_amount", "IRPF_rate", "IRPF_amount", "total_invoice"]

    # Check top level fields
    if not all(field in data for field in required_top_fields):
        return False

    # Check provider subfields
    provider = data.get("provider", {})
    if not all(field in provider for field in required_provider_fields):
        return False

    # Check contact subfields
    contact = provider.get("contact", {})
    if not all(field in contact for field in required_contact_fields):
        return False

    # Check total subfields
    total = data.get("total", {})
    if not all(field in total for field in required_total_fields):
        return False

    # Check items is a list
    if not isinstance(data.get("items"), list):
        return False

    return True

# Main function
def extract_invoice_data_from_uploaded_file(file_storage_obj) -> dict | None:
    try:
        # Step 1: Read file into memory
        file_bytes = file_storage_obj.read()
        file_io = io.BytesIO(file_bytes)
        file_io.name = file_storage_obj.filename

        # Step 2: Upload file to OpenAI
        uploaded_file = openai.files.create(
            file=file_io,
            purpose="assistants"
        )

        # Step 3: Create a thread
        thread = openai.beta.threads.create()

        # Step 4: Send a message to the thread with file attachment
        message = openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=(
                "You are a professional invoice analyzer. "
                "Please read the attached invoice carefully and respond ONLY in strict JSON format. "
                "The JSON must contain: invoice_number, invoice_date, provider (with name, address, contact, VAT_NUMBER/NIE/CIF), items list, total, and description. "
                "Do not return any explanations. Return only JSON."
            ),
            attachments=[
                {
                    "file_id": uploaded_file.id,
                    "tools": [{"type": "file_search"}]
                }
            ]
        )

        # Step 5: Run the Assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            tool_choice="auto"
        )

        # Step 6: Polling for completion
        start_time = time.time()
        while run.status not in ("completed", "failed", "cancelled", "expired"):
            if time.time() - start_time > 60:
                raise Exception("Assistant run timed out after 60 seconds.")
            time.sleep(2)
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if run.status != "completed":
            raise Exception(f"Run failed with status: {run.status}")

        # Step 7: Fetch the response
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        final_message = messages.data[0].content[0].text.value

        print("🔵 Raw Assistant Message:", final_message)

        if not final_message.strip():
            raise Exception("Assistant response was empty. No invoice data extracted.")

        # Step 8: Clean triple backticks and parse JSON
        cleaned_message = clean_assistant_json(final_message)

        try:
            extracted_json = json.loads(cleaned_message)
        except json.JSONDecodeError as e:
            raise Exception(f"Assistant response was not valid JSON. Details: {str(e)}")

        # Step 9: Validate JSON structure
        if not validate_invoice_structure(extracted_json):
            raise Exception("Extracted JSON does not match the expected invoice format.")

        return extracted_json

    except Exception as e:
        print(f"❌ Error during assistant extraction: {e}")
        return None
