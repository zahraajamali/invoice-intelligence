import os
import json
import traceback
from dotenv import load_dotenv


from convertFileToText import convert_file_to_text
from extractInvoiceData import extract_invoice_data_from_gpt
from neo4jService import Neo4jService


if __name__ == "__main__":

    try:
        # Step 0 : setup config
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        hub_api_token = os.getenv("HUB_API_TOKEN")
        file_name = 'invoice'
        url = "https://inventory-server.prd.delinternet.com/api/v1/files/79c4a4c73d75e82d76768d0afbe01b0a715da6fe4c576f3d5c2f2515e53865ae.pdf"

        # Step 1: add directory
        output_dir = f"ocr_output/{file_name}"
        os.makedirs(output_dir, exist_ok=True)
        final_result_dir = f"formatted_output/{file_name}"
        os.makedirs(final_result_dir, exist_ok=True)

        # Step 2: convert file to text
        convert_file_to_text(url,output_dir,hub_api_token)

        # Step 3 : extract invoice data
        invoice_data= extract_invoice_data_from_gpt(openai_api_key,f"{output_dir}/page1.txt")
        print("invoice_data...",invoice_data)

        # Step 4 : enrich Invoice with Neo4j
        if(invoice_data):
            neo4j = Neo4jService(uri="bolt://localhost:7687", username="neo4j", password="del-ai123")

            clients = neo4j.load_clients_from_json("datasets/inventory.suppliers.json")
            items = neo4j.load_items_from_json("datasets/inventory.products.json")
            neo4j.create_clients(clients)
            neo4j.create_items(items)


            enriched_invoice = neo4j.enrich_invoice(invoice_data)

            with open(f"{final_result_dir}/enriched_{file_name}.json", "w", encoding="utf-8") as f:
                json.dump(enriched_invoice, f, indent=2, ensure_ascii=False)

            neo4j.close()
        else:
            print('No invoice data extracted. Skipping enrichment step.')
    
    except Exception as e:
        print("An error occurred during invoice data extraction from GPT.")
        traceback.print_exc()

