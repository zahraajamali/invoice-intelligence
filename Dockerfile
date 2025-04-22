FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ✅ Cache pip install unless requirements.txt changes
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ✅ Now copy the rest of your app
COPY . .

CMD ["python", "app.py"]
