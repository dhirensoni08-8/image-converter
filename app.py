from flask import Flask, render_template, request, send_from_directory
from PIL import Image
import os
import zipfile
import shutil
from pathlib import Path
import patoolib

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

def convert_image(source, target_folder, target_format, sanitize_special=False):
    img = Image.open(source)
    base_name = Path(source).stem
    if sanitize_special:
        base_name = "".join(c if c.isalnum() or c == " " else "" for c in base_name)
        base_name = base_name.replace(" ", "_")
    target_path = os.path.join(target_folder, f"{base_name}.{target_format.lower()}")
    img.save(target_path, target_format.upper())
    return target_path

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/convert", methods=["POST"])
def convert():
    # uploads ko pehle clear karo
    shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    target_format = request.form['format']
    sanitize_special = request.form.get("sanitize_special")

    files = request.files.getlist("file")
    converted_folders = []

    for file in files:
        filename = file.filename
        upload_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(upload_path)

        # folder name
        base_upload_name = Path(filename).stem
        safe_foldername = "".join(c if c.isalnum() or c == " " else "" for c in base_upload_name).replace(" ", "_")

        target_folder = os.path.join(CONVERTED_FOLDER, safe_foldername)
        os.makedirs(target_folder, exist_ok=True)

        # zip
        if filename.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(upload_path, 'r') as zip_ref:
                    zip_ref.extractall(UPLOAD_FOLDER)
                for root, _, files_in in os.walk(UPLOAD_FOLDER):
                    for f in files_in:
                        if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")):
                            src = os.path.join(root, f)
                            convert_image(src, target_folder, target_format, sanitize_special=bool(sanitize_special))
            except Exception as e:
                return f"Error extracting ZIP: {e}", 400

        # rar
        elif filename.lower().endswith(".rar"):
            try:
                patoolib.extract_archive(upload_path, outdir=UPLOAD_FOLDER)
                for root, _, files_in in os.walk(UPLOAD_FOLDER):
                    for f in files_in:
                        if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")):
                            src = os.path.join(root, f)
                            convert_image(src, target_folder, target_format, sanitize_special=bool(sanitize_special))
            except Exception as e:
                return f"Error extracting RAR: {e}", 400

        # single images
        elif filename.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")):
            convert_image(upload_path, target_folder, target_format, sanitize_special=bool(sanitize_special))

        else:
            return "❌ Only images, ZIP, or RAR supported.", 400

        # zip bana do
        result_zip = os.path.join(target_folder, f"{safe_foldername}.zip")
        with zipfile.ZipFile(result_zip, "w") as zipf:
            for file_in in os.listdir(target_folder):
                if not file_in.endswith(".zip"):
                    zipf.write(os.path.join(target_folder, file_in), file_in)
        converted_folders.append((safe_foldername, result_zip))

    return render_template("index.html", converted_folders=converted_folders)

@app.route("/download/<folder>/<filename>")
def download(folder, filename):
    return send_from_directory(os.path.join(CONVERTED_FOLDER, folder), filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
