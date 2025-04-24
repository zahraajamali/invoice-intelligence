from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import json
import traceback
import json
from neo4jService import Neo4jService
from convertFileToText import convert_bytes_to_text , convert_file_to_text
from extractInvoiceData import extract_invoice_data_from_gpt
from flasgger import Swagger, swag_from
from create_invoice_format import transform_invoice
import logging
import atexit
from functools import wraps
from useOpenAiToParseInvoice import extract_invoice_data_from_pdf

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


load_dotenv()

app = Flask(__name__)
swagger = Swagger(app)


# Load ENV
NEO4J_HOST = os.getenv("NEO4J_HOST", "localhost")
NEO4J_PORT = os.getenv("NEO4J_PORT", "7687") 
NEO4J_URI = f"bolt://{NEO4J_HOST}:{NEO4J_PORT}"

NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
SUPPLIERS_JSON_PATH = os.getenv("SUPPLIERS_JSON_PATH")
PRODUCTS_JSON_PATH = os.getenv("PRODUCTS_JSON_PATH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUB_API_TOKEN = os.getenv("HUB_API_TOKEN")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

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
@swag_from("swagger_docs/update_suppliers.yml")
def update_suppliers():
    logger.info("🔄 Received request to update suppliers")
    return neo4j_service.handle_neo4j_upload(
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
    logger.info("🔄 Received request to update products")
    return neo4j_service.handle_neo4j_upload(
        file_field_name="products",
        creator_func=lambda neo4j, data: (
            neo4j.delete_all_nodes_by_label("Item"),
            neo4j.create_items(data)
        )
    )

@app.route("/download-process", methods=["POST"])
@require_api_key
@swag_from("swagger_docs/download_process.yml")
def download_process_invoice():
    try:
        logger.info("📥 Received request to process invoice from URL")

        data = request.get_json()
        file_url = data.get("file_url")

        if not file_url:
            logger.warning("⚠️ Missing 'file_url' in request body")
            return jsonify({"error": "Missing 'file_url' in request"}), 400

        logger.info(f"🌐 Downloading and processing file from: {file_url}")

        # Convert file to text
        ocr_text = convert_file_to_text(file_url, HUB_API_TOKEN)
        logger.info("📄 OCR completed from file URL")

        # Extract data using GPT
        logger.info("🧠 Extracting invoice data using GPT...")
        invoice_data = extract_invoice_data_from_gpt(OPENAI_API_KEY, ocr_text)

        if not invoice_data:
            logger.error("❌ Invoice extraction failed")
            return jsonify({"error": "Invoice extraction failed"}), 500

        logger.info("🔌 Connecting to Neo4j to enrich invoice data")
        neo4j = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        neo4j.create_clients(neo4j.load_clients_from_json(SUPPLIERS_JSON_PATH))
        neo4j.create_items(neo4j.load_items_from_json(PRODUCTS_JSON_PATH))
        enriched = neo4j.enrich_invoice(invoice_data)
        neo4j.close()
        logger.info("🧩 Invoice enrichment completed")

        transformed_invoice = transform_invoice(enriched)
        logger.info("📦 Invoice successfully transformed and returned")

        return jsonify({"message": "✅ Invoice processed", "data": transformed_invoice}), 200

    except Exception as e:
        logger.exception("❌ Error occurred during download-process invoice")
        return jsonify({"error": str(e)}), 500


@app.route("/process-invoice", methods=["POST"])
@require_api_key
@swag_from("swagger_docs/process_invoice.yml")
def process_invoice():
    try:
        logger.info("📥 Received file upload for invoice processing")

        if 'file' not in request.files:
            logger.warning("⚠️ Missing 'file' in request")
            return jsonify({"error": "Missing file in request"}), 400

        file = request.files['file']
        if file.filename == '':
            logger.warning("⚠️ No file selected")
            return jsonify({"error": "No selected file"}), 400

        logger.info(f"📄 File received: {file.filename}")

        pdf_bytes = file.read()

        result = extract_invoice_data_from_pdf(pdf_bytes)

    
        if result:
            invoice_data = json.dumps(result, indent=2, ensure_ascii=False)
        else:
            logger.error("❌ Invoice extraction failed")
            return jsonify({"error": "Invoice extraction failed"}), 500
        
    

        logger.info("🔌 Connecting to Neo4j to enrich invoice data")
        neo4j = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        neo4j.create_clients(neo4j.load_clients_from_json(SUPPLIERS_JSON_PATH))
        neo4j.create_items(neo4j.load_items_from_json(PRODUCTS_JSON_PATH))
        enriched = neo4j.enrich_invoice(invoice_data)
        neo4j.close()
        logger.info("🧩 Invoice enrichment completed")

        transformed_invoice = transform_invoice(enriched)
        logger.info("📦 Invoice successfully transformed and returned")

        return jsonify({"message": "✅ Invoice processed", "data": transformed_invoice}), 200

    except Exception as e:
        logger.exception("❌ Error occurred during uploaded invoice processing")
        return jsonify({"error": str(e)}), 500


@atexit.register
def shutdown():
    logger.info("🧹 Closing Neo4j connection")
    neo4j_service.close()

if __name__ == "__main__":
    logger.info(f"🚀 Starting Flask server on 0.0.0.0:{FLASK_PORT} (debug={app.debug})")
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=True)
