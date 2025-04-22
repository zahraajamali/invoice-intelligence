from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import json
import traceback
import json
from neo4jService import Neo4jService
from convertFileToText import convert_file_to_text
from extractInvoiceData import extract_invoice_data_from_gpt
from flasgger import Swagger, swag_from

load_dotenv()

app = Flask(__name__)
swagger = Swagger(app)


# Load ENV
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
SUPPLIERS_JSON_PATH = os.getenv("SUPPLIERS_JSON_PATH")
PRODUCTS_JSON_PATH = os.getenv("PRODUCTS_JSON_PATH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUB_API_TOKEN = os.getenv("HUB_API_TOKEN")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

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

def handle_neo4j_upload(file_field_name, creator_func):
    try:
        if file_field_name not in request.files:
            return jsonify({"error": f"No file part named '{file_field_name}' in the request"}), 400

        file = request.files[file_field_name]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        data = json.load(file)

        neo4j = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        cleaned_data = [neo4j.flatten_oid_fields(item) for item in data]
        creator_func(neo4j, cleaned_data)
        neo4j.close()

        return jsonify({"message": f"✅ {file_field_name.capitalize()} data updated"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def delete_all_nodes_by_label(self, label):
    with self.driver.session() as session:
        session.run(f"""
            MATCH (n:{label})
            DETACH DELETE n
        """)


@app.route("/update-suppliers", methods=["POST"])
@require_api_key
@swag_from("swagger_docs/update_suppliers.yml")
def update_suppliers():
    return handle_neo4j_upload(
        file_field_name="suppliers",
        creator_func=lambda neo4j, data: (
            neo4j.delete_all_nodes_by_label("Client"),
            neo4j.create_clients(data)
        )
    )

@app.route("/update-products", methods=["POST"])
@require_api_key
@swag_from("swagger_docs/update_products.yml")
def update_products():
    return handle_neo4j_upload(
        file_field_name="products",
        creator_func=lambda neo4j, data: (
            neo4j.delete_all_nodes_by_label("Item"),
            neo4j.create_items(data)
        )
    )

@app.route("/process-invoice", methods=["POST"])
@require_api_key
@swag_from("swagger_docs/process_invoice.yml")
def process_invoice():
    try:
        data = request.get_json()
        file_url = data.get("file_url")

        if not file_url:
            return jsonify({"error": "Missing 'file_url' in request"}), 400

        # Convert file to text
        ocr_text=convert_file_to_text(file_url, HUB_API_TOKEN)

        # Extract data using GPT
        invoice_data = extract_invoice_data_from_gpt(OPENAI_API_KEY, ocr_text)

        if not invoice_data:
            return jsonify({"error": "Invoice extraction failed"}), 500

        # Enrich with Neo4j
        neo4j = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        neo4j.create_clients(neo4j.load_clients_from_json(SUPPLIERS_JSON_PATH))
        neo4j.create_items(neo4j.load_items_from_json(PRODUCTS_JSON_PATH))
        enriched = neo4j.enrich_invoice(invoice_data)
        neo4j.close()

        return jsonify({"message": "✅ Invoice processed", "data": enriched}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=FLASK_PORT, debug=True)
