# 🧾 Invoice Analyzer and Enricher with Neo4j, GPT, and Flask API (Dockerized)

This project automates the extraction of structured invoice data from scanned or PDF invoices using OCR and GPT-4. It enriches invoice information with data from a Neo4j graph database of suppliers and products and exposes a REST API using Flask.

---

## 🚀 Features

- ✅ Extracts structured data from invoice PDFs using OpenAI GPT-4o
- ✅ Uses OCR (`Tesseract`) to process PDF images
- ✅ Enriches data by matching suppliers and items from a Neo4j knowledge graph
- ✅ REST API to process invoices or sync supplier/product data
- ✅ Dockerized for easy deployment

---

## 🧰 Requirements (Local or Docker Host)

- Docker & Docker Compose
- (Optional local run) Python 3.8+ with:
  - Tesseract OCR
  - Poppler (`pdf2image`)
  - Neo4j running locally or remotely

---

## 🐳 Docker Setup

### 1. Clone the project

```bash
git clone https://github.com/your-username/invoice-analyzer.git
cd invoice-analyzer
```

### 2. Add your `.env` configuration

Create a `.env` file in the root directory:

```dotenv
OPENAI_API_KEY=your_openai_key
HUB_API_TOKEN=your_hub_api_token
API_KEY=your_api_key_for_flask

NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=del-ai123

SUPPLIERS_JSON_PATH=datasets/inventory.suppliers.json
PRODUCTS_JSON_PATH=datasets/inventory.products.json
```

### 3. Build and run with Docker Compose

```bash
docker-compose up --build
```

> ⏱ It may take a minute to download and build everything.

---

## 📁 Folder Structure

```
.
├── app.py                         # Flask API app
├── Dockerfile
├── docker-compose.yml
├── .env
├── requirements.txt
├── convertFileToText.py
├── extractInvoiceData.py
├── neo4jService.py
├── datasets/
│   ├── inventory.suppliers.json
│   └── inventory.products.json
├── ocr_output/
├── formatted_output/
└── invoicesFile/
```

---

## 🌐 Flask API Usage

Your API will run on [http://localhost:5000](http://localhost:5000)

Use `X-API-KEY` header (from `.env`) to access protected endpoints.

---

### 🔄 POST `/update-suppliers`

Load suppliers from `datasets/inventory.suppliers.json` into Neo4j.

```bash
curl -X POST http://localhost:5000/update-suppliers \
  -H "X-API-KEY: your_api_key"
```

---

### 🔄 POST `/update-products`

Load products from `datasets/inventory.products.json` into Neo4j.

```bash
curl -X POST http://localhost:5000/update-products \
  -H "X-API-KEY: your_api_key"
```

---

### 🧾 POST `/process-invoice`

Trigger the full OCR + GPT + enrichment pipeline using a remote PDF URL.

```bash
curl -X POST http://localhost:5000/process-invoice \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "file_url": "https://your.server.com/path/to/invoice.pdf",
    "file_name": "invoice2024"
}'
```

---

### 🔍 Neo4j Browser Access

You can explore the data graph visually at:

> 🧠 [http://localhost:7474](http://localhost:7474)  
> Username: `neo4j`  
> Password: `del-ai123`

---

## ✅ Sample Output

```json
{
  "invoice_number": "INV-123",
  "invoice_date": "2024-04-01",
  "provider": {
    "name": "Supplier XYZ",
    "address": "...",
    "contact": {
      "email": "...",
      "phone": "...",
      "fax": null,
      "mobile": null
    },
    "VAT_NUMBER/NIE/CIF": "B12345678"
  },
  "items": [...],
  "total": {...},
  "description": "Late delivery noted in remarks"
}
```

---

## 🧠 Built With

- 🧠 OpenAI GPT-4o
- 🧾 Tesseract OCR
- 📊 Neo4j
- 🌍 Flask
- 🐳 Docker
- 🐍 Python 3.10

---

## 📬 Contact

Feel free to reach out for collaboration or questions!  
**Email:** jamzahra33@gmail.com  
**GitHub:** [@zahraajamali](https://github.com/zahraajamali)
```

---

Let me know if you’d like to add:
- API token authentication
- Swagger/OpenAPI docs
- Docker support for the full stack