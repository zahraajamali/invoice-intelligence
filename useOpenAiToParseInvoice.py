import openai
import os
from dotenv import load_dotenv


client = openai.OpenAI()



load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

with open("invoicesFile/invoice.pdf", "rb") as f:
    file = openai.files.create(file=f, purpose="assistants")

# 2. Create a new assistant 
assistant = openai.beta.assistants.create(
    name="Invoice Parser",
    instructions="You're a professional invoice analyzer. Extract structured data from invoices in JSON format.",
    model="gpt-4o",
)

# 3. Create a thread and attach the file
thread = openai.beta.threads.create()

# 4. Add user message to thread, referencing file
openai.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Extract structured invoice data from the attached PDF.",
      attachments=[
        {
            "file_id": file.id,
            "tools": [{"type": "file_search"}]  # This part is mandatory
        }
    ]
)

run = openai.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

# 6. Wait for the run to complete
import time
while True:
    run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    if run_status.status == "completed":
        break
    elif run_status.status in ["failed", "cancelled", "expired"]:
        raise Exception(f"Run failed with status: {run_status.status}")
    time.sleep(1)

messages = openai.beta.threads.messages.list(thread_id=thread.id)
for msg in reversed(messages.data):
    if msg.role == "assistant":
        print(msg.content[0].text.value)
        break