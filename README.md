# 🧾 AutoSupplierInvoice: Intelligent Invoice Processing & Enrichment with OCR, GPT-4o & Neo4j

This project automates the extraction, analysis, and enrichment of supplier invoices using a powerful pipeline that combines:
- 🖼️ OCR (Tesseract + OpenCV preprocessing)
- 🤖 LLM (GPT-4o via LangChain + OpenAI)
- 🧠 Graph enrichment with Neo4j
- 📄 JSON export of enriched invoice data

---

## 📦 Features

- Extract invoice data from scanned PDFs using Tesseract OCR
- Clean and enhance scanned text with smart image preprocessing (OpenCV)
- Structure invoice details using GPT-4o via LangChain
- Match supplier and product data from a Neo4j graph database
- Output a structured, enriched invoice as a JSON file

---

## 🧰 Tech Stack

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [OpenAI GPT-4o](https://openai.com/)
- [LangChain](https://www.langchain.com/)
- [Neo4j](https://neo4j.com/)
- OpenCV & PIL for image processing
- dotenv for API key handling

---
