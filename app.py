import streamlit as st
import os, shutil, zipfile, re, tempfile
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
from PIL import Image

# 📍 Path Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Ganti kalau pakai Windows

# 📁 Setup folder kerja
UPLOAD_DIR = "upload_pdf"
SPLIT_DIR = "split_pdf"
RESULT_DIR = "hasil_rename"
ZIP_NAME = "rename_result.zip"

for folder in [UPLOAD_DIR, SPLIT_DIR, RESULT_DIR]:
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

# 🧾 Header UI
st.title("📄 Split & Rename PDF STP berdasarkan Nomor Surat")
st.markdown("""
Upload PDF hasil scan. Sistem akan melakukan:
1. ✂️ Split file menjadi per 2 halaman,
2. ➕ Tambahkan halaman billing jika ditemukan,
3. 🔍 OCR halaman pertama dari hasil split,
4. 🏷️ Rename file berdasarkan Nomor: xxx/xxx/...,
5. 📦 Kompres semua hasil menjadi ZIP.
""")

uploaded_files = st.file_uploader("Upload file PDF hasil scan", type="pdf", accept_multiple_files=True)

# Fungsi deteksi billing
def is_billing_page_image(image):
    text = pytesseract.image_to_string(image, lang="eng+ind").lower()
    return "billing" in text

# Fungsi split per 2 halaman + billing
def split_pdf_with_billing(pdf_path, output_dir):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    images = convert_from_path(pdf_path, dpi=200)
    
    i = 0
    part = 1
    split_paths = []

    while i < total_pages:
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        if i + 1 < total_pages:
            writer.add_page(reader.pages[i + 1])
        i += 2

        if i < total_pages and is_billing_page_image(images[i]):
            writer.add_page(reader.pages[i])
            i += 1

        output_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(pdf_path))[0]}_part_{part:03d}.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)
        split_paths.append(output_path)
        part += 1

    return split_paths

# Fungsi OCR
def extract_nomor_ocr(path):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            images = convert_from_path(path, dpi=400, first_page=1, last_page=1, output_folder=tmpdir)
            if not images:
                return None
            img = images[0]
            w, h = img.size
            cropped = img.crop((int(w * 0.05), int(h * 0.05), int(w * 0.95), int(h * 0.25)))
            text = pytesseract.image_to_string(cropped).upper()
            text = text.replace("O", "0").replace("I", "1").replace("L", "1").replace("：", ":")
            text = re.sub(r"[\t\r\n]+", " ", text)
            text = re.sub(r"\s+", " ", text)

            # Logging hasil OCR ke UI
            st.code(text, language="text")

            match = re.search(r'(?i)(?:N[O0]M[O0]R)[\s:]*([0-9]{4,6}(?:[/|\.][0-9]{1,5}){4})', text)
            if match:
                return match.group(1).replace("/", ".").replace("|", ".")
    except Exception as e:
        st.warning(f"❌ OCR gagal untuk {os.path.basename(path)}: {e}")
    return None

# 🚀 Jalankan Proses
if uploaded_files:
    progress = st.progress(0)
    all_split_files = []

    for idx, uploaded_file in enumerate(uploaded_files):
        filename = uploaded_file.name
        filepath = os.path.join(UPLOAD_DIR, filename.replace(" ", "_"))
        with open(filepath, "wb") as f:
            f.write(uploaded_file.read())

        st.info(f"🔧 Memproses file: `{filename}`")
        split_paths = split_pdf_with_billing(filepath, SPLIT_DIR)
        all_split_files.extend(split_paths)
        progress.progress((idx + 1) / len(uploaded_files))

    st.markdown("---")
    st.subheader("🏷️ Rename berdasarkan hasil OCR")

    renamed_files = []
    failed_files = []

    for idx, split_path in enumerate(all_split_files):
        st.markdown(f"**📄 File:** `{os.path.basename(split_path)}`")

        nomor = extract_nomor_ocr(split_path)

        if nomor:
            new_name = f"{nomor}.pdf"
        else:
            new_name = f"UNKNOWN_{idx+1:03d}.pdf"
            failed_files.append(os.path.basename(split_path))
            st.warning(f"⚠️ Gagal menemukan nomor surat. Dinamai: `{new_name}`")

        output_path = os.path.join(RESULT_DIR, new_name)
        shutil.copyfile(split_path, output_path)
        renamed_files.append(output_path)

        st.success(f"✅ {os.path.basename(split_path)} → {new_name}")
        progress.progress((idx + 1) / len(all_split_files))

    if failed_files:
        st.error(f"🚨 {len(failed_files)} file gagal dikenali nomor suratnya.")
        st.code("\n".join(failed_files))
    else:
        st.success("🎉 Semua file berhasil di-OCR dan dinamai dengan benar!")

    # ZIP hasil
    zip_path = ZIP_NAME
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in renamed_files:
            zipf.write(path, arcname=os.path.basename(path))

    with open(zip_path, "rb") as f:
        st.download_button("⬇️ Download ZIP Hasil Rename", f, file_name=ZIP_NAME)
