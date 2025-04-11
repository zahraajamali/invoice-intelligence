Absolutely! Here's everything you need:

---

## 📄 README.md

```markdown
# 🧾 Invoice Analyzer and Enricher with Neo4j & GPT

This project automates the extraction of structured invoice data from scanned or PDF invoices using OCR and GPT-4. It enriches invoice information with data from a Neo4j graph database of suppliers and products.

---

## 🚀 Features

- ✅ Extracts structured data from invoice PDFs using OpenAI GPT-4o
- ✅ Uses OCR (`Tesseract`) to process PDF images
- ✅ Enriches data by matching suppliers and items from a Neo4j knowledge graph
- ✅ Supports PDF downloads from secure URLs (with tokens)

---

## 🧰 Requirements

- Python 3.8+
- Tesseract OCR installed
- Neo4j running locally (or remote)
- OpenAI API key
- [Poppler](https://poppler.freedesktop.org/) (for `pdf2image`)

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/invoice-analyzer.git
cd invoice-analyzer
```

### 2. Set up virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install external tools

#### Tesseract OCR:
- **macOS**: `brew install tesseract`
- **Ubuntu**: `sudo apt install tesseract-ocr`
- **Windows**: [Download Tesseract](https://github.com/tesseract-ocr/tesseract/wiki)

#### Poppler for `pdf2image`:
- **macOS**: `brew install poppler`
- **Ubuntu**: `sudo apt install poppler-utils`
- **Windows**: [Download Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)

---

## 🔐 Environment Setup

Create a `.env` file in the project root:

```dotenv
OPENAI_API_KEY=your_openai_key_here
HUB_API_TOKEN=your_hub_api_token_here
```

---

## 📁 Folder Structure

```
.
├── convertFileToText.py
├── extractInvoiceData.py
├── neo4jService.py
├── main.py
├── datasets/
│   ├── inventory.suppliers.json
│   └── inventory.products.json
├── invoicesFile/
│   └── invoice2.pdf
├── ocr_output/
├── formatted_output/
├── requirements.txt
└── .env
```

---

## ⚙️ How to Use

### Run the full pipeline

```bash
python main.py
```

This will:
1. Download the invoice PDF
2. Convert it to text using OCR
3. Extract structured invoice data with GPT-4
4. Enrich it using Neo4j supplier & product data
5. Save the final enriched invoice JSON

---

## 🧪 Sample Output

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
- 🐍 Python

---

## 📬 Contact

Feel free to reach out for collaboration or questions!  
**Email:** yourname@company.com  
**GitHub:** [@yourusername](https://github.com/yourusername)
```