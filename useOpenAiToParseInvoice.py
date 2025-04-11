import openai
import os
import time
import json
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 1. Upload your file (PDF)
file_path = "invoicesFile/invoice2.pdf"
file = openai.files.create(
    file=open(file_path, "rb"),
    purpose="assistants"
)

# 2. Create an Assistant
assistant = openai.beta.assistants.create(
    name="Invoice Extractor",
    instructions="""
    You are a professional invoice analyzer.
    Extract invoice data from the attached PDF and return it in this JSON format:
    
    {
      "invoice_number": ...,
      "invoice_date": ...,
      "provider": {
        "name": ...,
        "address": ...,
        "contact": {
          "email": ...,
          "phone": ...,
          "fax": ...,
          "mobile": ...
        },
        "C.I.F.": ...
      },
      "items": [
        {
          "quantity": ...,
          "description": ...,
          "project": ...,
          "unit_price": ...,
          "total": ...
        }
      ],
      "total": {
        "base_amount": ...,
        "VAT_rate": ...,
        "VAT_amount": ...,
        "total_invoice": ...
      },
      "description": "<Any extra relevant info or context from the invoice>"
    }
    """,
    model="gpt-4o"
)

# 3. Create a thread and attach the file
thread = openai.beta.threads.create()

# 4. Send message with file
message = openai.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Please analyze this invoice PDF and extract the data as structured JSON.",
    attachments=[
        {
            "file_id": file.id,
            "tools": [{"type": "file_search"}]
        }
    ]
)

# 5. Run the assistant on the thread
run = openai.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

# 6. Wait for completion
while True:
    run_status = openai.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )
    if run_status.status == "completed":
        break
    elif run_status.status == "failed":
        raise Exception("Run failed.")
    time.sleep(1)

# 7. Get the response
messages = openai.beta.threads.messages.list(thread_id=thread.id)

# 8. Extract JSON from the last assistant message
response_content = messages.data[0].content[0].text.value
print(response_content)

# 9. Clean and load JSON if needed
try:
    clean_json = response_content.strip().strip("```json").strip("```")
    invoice_data = json.loads(clean_json)
    print(json.dumps(invoice_data, indent=2))
except Exception as e:
    print("Failed to parse JSON:", e)
    print(response_content)
