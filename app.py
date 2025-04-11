from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import json
import traceback

from neo4jService import Neo4jService
from convertFileToText import convert_file_to_text
from extractInvoiceData import extract_invoice_data_from_gpt

load_dotenv()

app = Flask(__name__)

# Load ENV
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
SUPPLIERS_JSON_PATH = os.getenv("SUPPLIERS_JSON_PATH")
PRODUCTS_JSON_PATH = os.getenv("PRODUCTS_JSON_PATH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUB_API_TOKEN = os.getenv("HUB_API_TOKEN")

from functools import wraps

# Load API key from env
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get("X-API-KEY")
        if not provided_key or provided_key != SERVICE_API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route("/update-suppliers", methods=["POST"])
@require_api_key
def update_suppliers():
    try:
        neo4j = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        suppliers = neo4j.load_clients_from_json(SUPPLIERS_JSON_PATH)
        neo4j.create_clients(suppliers)
        neo4j.close()
        return jsonify({"message": "✅ Supplier data updated"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/update-products", methods=["POST"])
@require_api_key
def update_products():
    try:
        neo4j = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        products = neo4j.load_items_from_json(PRODUCTS_JSON_PATH)
        neo4j.create_items(products)
        neo4j.close()
        return jsonify({"message": "✅ Product data updated"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/process-invoice", methods=["POST"])
@require_api_key
def process_invoice():
    try:
        data = request.get_json()
        file_url = data.get("file_url")
        file_name = data.get("file_name", "invoice")

        if not file_url:
            return jsonify({"error": "Missing 'file_url' in request"}), 400

        output_dir = f"ocr_output/{file_name}"
        final_result_dir = f"formatted_output/{file_name}"
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(final_result_dir, exist_ok=True)

        # Convert file to text
        convert_file_to_text(file_url, output_dir, HUB_API_TOKEN)

        # Extract data using GPT
        invoice_text_path = f"{output_dir}/page1.txt"
        invoice_data = extract_invoice_data_from_gpt(OPENAI_API_KEY, invoice_text_path)

        if not invoice_data:
            return jsonify({"error": "Invoice extraction failed"}), 500

        # Enrich with Neo4j
        neo4j = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        neo4j.create_clients(neo4j.load_clients_from_json(SUPPLIERS_JSON_PATH))
        neo4j.create_items(neo4j.load_items_from_json(PRODUCTS_JSON_PATH))
        enriched = neo4j.enrich_invoice(invoice_data)
        neo4j.close()

        result_path = f"{final_result_dir}/enriched_{file_name}.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)

        return jsonify({"message": "✅ Invoice processed", "data": enriched}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
