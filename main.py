import os
import json
import traceback
from dotenv import load_dotenv

from convertFileToText import convert_file_to_text
from extractInvoiceData import extract_invoice_data_from_gpt
from neo4jService import Neo4jService

def main():
    try:
        # Step 0: Load environment variables
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        hub_api_token = os.getenv("HUB_API_TOKEN")

        file_name = os.getenv("INVOICE_FILE_NAME")
        pdf_url = os.getenv("INVOICE_FILE_URL")

        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_username = os.getenv("NEO4J_USERNAME")
        neo4j_password = os.getenv("NEO4J_PASSWORD")

        suppliers_path = os.getenv("SUPPLIERS_JSON_PATH")
        products_path = os.getenv("PRODUCTS_JSON_PATH")

        # Step 1: Setup directories
        output_dir = f"ocr_output/{file_name}"
        final_result_dir = f"formatted_output/{file_name}"
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(final_result_dir, exist_ok=True)

        # Step 2: Convert PDF to text
        convert_file_to_text(pdf_url, output_dir, hub_api_token)

        # Step 3: Extract invoice data using GPT
        text_path = f"{output_dir}/page1.txt"
        invoice_data = extract_invoice_data_from_gpt(openai_api_key, text_path)
        print("Extracted invoice data:", invoice_data)

        if not invoice_data:
            print("❌ No invoice data extracted. Skipping enrichment.")
            return

        # Step 4: Enrich with Neo4j data
        neo4j = Neo4jService(uri=neo4j_uri, username=neo4j_username, password=neo4j_password)
        neo4j.create_clients(neo4j.load_clients_from_json(suppliers_path))
        neo4j.create_items(neo4j.load_items_from_json(products_path))

        enriched_invoice = neo4j.enrich_invoice(invoice_data)

        # Step 5: Save enriched data
        output_file = f"{final_result_dir}/enriched_{file_name}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(enriched_invoice, f, indent=2, ensure_ascii=False)

        neo4j.close()
        print(f"✅ Enriched invoice saved to: {output_file}")

    except Exception:
        print("❌ An error occurred during invoice processing:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
