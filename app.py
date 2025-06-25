import streamlit as st
import os, shutil, zipfile
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
from PIL import Image
import tempfile
import re
from datetime import datetime

# 📍 SET path ke tesseract.exe di Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # GANTI JIKA PERLU

# 📁 Setup folder kerja
UPLOAD_DIR = "upload_pdf"
RESULT_DIR = "hasil_rename"
ZIP_NAME = "rename_result.zip"

for folder in [UPLOAD_DIR, RESULT_DIR]:
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

# 🧾 Header
st.title("📄 Rename PDF berdasarkan Nomor: xxx/xxx/... (OCR)")
st.markdown("Upload PDF hasil scan (2 halaman per file). Sistem akan melakukan OCR halaman pertama dan me-*rename* file berdasarkan nomor surat di dalamnya.")

# 📤 Upload PDF
uploaded_files = st.file_uploader("Upload file PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    progress = st.progress(0)
    renamed_files = []

    for idx, uploaded_file in enumerate(uploaded_files):
        filename = uploaded_file.name
        filepath = os.path.join(UPLOAD_DIR, filename)

        # Simpan file
        with open(filepath, "wb") as f:
            f.write(uploaded_file.read())

        # 🔎 Extract nomor dari OCR
        def extract_nomor_ocr(path):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    images = convert_from_path(path, dpi=350, first_page=1, last_page=1, output_folder=tmpdir)

                    if not images:
                        return None

                    img = images[0]
                    w, h = img.size
                    cropped = img.crop((0, 0, w, int(h * 0.35)))

                    text = pytesseract.image_to_string(cropped)
                    text = text.replace("O", "0").replace("I", "1").replace("l", "1").replace("：", ":")
                    text = re.sub(r"[\t\r\n]+", " ", text)
                    text = re.sub(r"\s+", " ", text)

                    match = re.search(r'(?i)(?:N[o0]m[o0]r|Nomar|N[o0]rn[o0]r)\s*[:]?[\s]*([0-9]{4,6}(?:[/|\.][0-9]{1,5}){4})', text)
                    if match:
                        return match.group(1).replace("/", ".").replace("|", ".")
            except Exception as e:
                print(f"❌ OCR gagal untuk {os.path.basename(path)}: {e}")
            return None

        nomor = extract_nomor_ocr(filepath)

        if nomor:
            new_name = f"{nomor}.pdf"
        else:
            new_name = f"UNKNOWN_{filename}"

        # Salin isi PDF
        reader = PdfReader(filepath)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output_path = os.path.join(RESULT_DIR, new_name)
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        renamed_files.append(new_name)
        st.write(f"✅ {filename} → {new_name}")
        progress.progress((idx + 1) / len(uploaded_files))

    # ZIP hasil
    zip_path = ZIP_NAME
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in os.listdir(RESULT_DIR):
            zipf.write(os.path.join(RESULT_DIR, f), arcname=f)

    with open(zip_path, "rb") as f:
        st.download_button("⬇️ Download Hasil Rename (ZIP)", f, file_name=ZIP_NAME)

