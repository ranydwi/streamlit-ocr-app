# Gunakan image Python ringan
FROM python:3.10-slim

# Install dependencies OS: poppler, tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy project ke dalam container
WORKDIR /app
COPY . .

# Install dependencies Python
RUN pip install --no-cache-dir -r requirements.txt

# Jalankan Streamlit app
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
