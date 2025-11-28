from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image
import os
import uuid
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "change-this-secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_PDF = {".pdf"}
ALLOWED_IMG = {".png", ".jpg", ".jpeg"}

def allowed(filename, s):
    return os.path.splitext(filename)[1].lower() in s

def parse_pages(p):
    if not p:
        return []
    res = []
    for part in p.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            for i in range(int(a), int(b) + 1):
                res.append(i)
        else:
            res.append(int(part))
    return res

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/merge", methods=["GET", "POST"])
def merge_pdf():
    if request.method == "POST":
        fs = request.files.getlist("pdf_files")
        if not fs or fs[0].filename == "":
            flash("Please select at least two PDF files.")
            return redirect(request.url)
        merger = PdfMerger()
        saved = []
        try:
            for f in fs:
                if f and allowed(f.filename, ALLOWED_PDF):
                    fn = secure_filename(f.filename)
                    p = os.path.join(UPLOAD_FOLDER, fn)
                    f.save(p)
                    saved.append(p)
                    merger.append(p)
            out = os.path.join(UPLOAD_FOLDER, "merged_output.pdf")
            with open(out, "wb") as x:
                merger.write(x)
            merger.close()
            for s in saved:
                try: os.remove(s)
                except: pass
            return send_file(out, as_attachment=True)
        except Exception as e:
            merger.close()
            flash(f"Error merging PDFs: {e}")
            return redirect(request.url)
    return render_template("merge.html")

@app.route("/split", methods=["GET", "POST"])
def split_pdf():
    if request.method == "POST":
        f = request.files.get("pdf_file")
        pages = parse_pages(request.form.get("pages", ""))
        if not f or f.filename == "":
            flash("Please upload a PDF file.")
            return redirect(request.url)
        if not allowed(f.filename, ALLOWED_PDF):
            flash("Only PDF files are allowed.")
            return redirect(request.url)
        if not pages:
            flash("Please enter pages (e.g. 1-3,5).")
            return redirect(request.url)

        fn = secure_filename(f.filename)
        ip = os.path.join(UPLOAD_FOLDER, fn)
        f.save(ip)
        try:
            r = PdfReader(ip)
            w = PdfWriter()
            total = len(r.pages)
            for p in pages:
                if 1 <= p <= total:
                    w.add_page(r.pages[p - 1])
            out = os.path.join(UPLOAD_FOLDER, "split_output.pdf")
            with open(out, "wb") as x:
                w.write(x)
            try: os.remove(ip)
            except: pass
            return send_file(out, as_attachment=True)
        except Exception as e:
            flash(f"Error splitting PDF: {e}")
            return redirect(request.url)
    return render_template("split.html")

@app.route("/img2pdf", methods=["GET", "POST"])
def img2pdf():
    if request.method == "POST":
        imgs = request.files.getlist("images")
        if not imgs or imgs[0].filename == "":
            flash("Please select at least one image.")
            return redirect(request.url)
        pil_imgs = []
        saved = []
        try:
            for im in imgs:
                if allowed(im.filename, ALLOWED_IMG):
                    fn = secure_filename(im.filename)
                    p = os.path.join(UPLOAD_FOLDER, fn)
                    im.save(p)
                    saved.append(p)
                    pil_imgs.append(Image.open(p).convert("RGB"))
            if not pil_imgs:
                flash("No valid images were uploaded.")
                return redirect(request.url)
            out = os.path.join(UPLOAD_FOLDER, "images_output.pdf")
            first, *rest = pil_imgs
            first.save(out, save_all=True, append_images=rest)
            for s in saved:
                try: os.remove(s)
                except: pass
            return send_file(out, as_attachment=True)
        except Exception as e:
            flash(f"Error converting images: {e}")
            return redirect(request.url)
    return render_template("img_to_pdf.html")

@app.route("/edit_pages", methods=["GET", "POST"])
def edit_pages():
    # same page-level editor as before
    if request.method == "POST":
        f = request.files.get("pdf_file")
        delete = parse_pages(request.form.get("delete_pages", ""))
        order = parse_pages(request.form.get("new_order", ""))
        rr = parse_pages(request.form.get("rotate_right", ""))
        rl = parse_pages(request.form.get("rotate_left", ""))
        if not f or f.filename == "":
            flash("Please upload a PDF file.")
            return redirect(request.url)
        if not allowed(f.filename, ALLOWED_PDF):
            flash("Only PDF files are allowed.")
            return redirect(request.url)
        fn = secure_filename(f.filename)
        ip = os.path.join(UPLOAD_FOLDER, fn)
        f.save(ip)
        try:
            r = PdfReader(ip)
            w = PdfWriter()
            total = len(r.pages)
            if not order:
                order = list(range(1, total + 1))
            for p in order:
                if p in delete:
                    continue
                if 1 <= p <= total:
                    page = r.pages[p - 1]
                    if p in rr:
                        page.rotate(90)
                    if p in rl:
                        page.rotate(-90)
                    w.add_page(page)
            out = os.path.join(UPLOAD_FOLDER, "edited_output.pdf")
            with open(out, "wb") as x:
                w.write(x)
            try: os.remove(ip)
            except: pass
            return send_file(out, as_attachment=True)
        except Exception as e:
            flash(f"Error editing PDF pages: {e}")
            return redirect(request.url)
    return render_template("edit_pages.html")

# ---------- SIMPLE TEXT EDITOR ----------

@app.route("/text_editor", methods=["GET", "POST"])
def text_editor_upload():
    # Step 1: upload PDF and show text
    if request.method == "POST":
        f = request.files.get("pdf_file")
        if not f or f.filename == "":
            flash("Please upload a PDF file.")
            return redirect(request.url)
        if not allowed(f.filename, ALLOWED_PDF):
            flash("Only PDF files are allowed.")
            return redirect(request.url)

        # Save PDF
        fn = secure_filename(f.filename)
        pdf_id = str(uuid.uuid4())
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{pdf_id}.pdf")
        f.save(pdf_path)

        # Extract text from all pages
        try:
            reader = PdfReader(pdf_path)
            extracted = []
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                extracted.append(f"--- Page {i} ---\n{text}\n")
            full_text = "\n".join(extracted)

            # Save extracted text to .txt for later
            txt_path = os.path.join(UPLOAD_FOLDER, f"{pdf_id}.txt")
            with open(txt_path, "w", encoding="utf-8") as tf:
                tf.write(full_text)

            return render_template("text_editor.html", pdf_id=pdf_id, text=full_text)
        except Exception as e:
            flash(f"Error reading PDF text: {e}")
            return redirect(request.url)

    return render_template("text_upload.html")

@app.route("/text_editor/apply", methods=["POST"])
def text_editor_apply():
    pdf_id = request.form.get("pdf_id")
    new_text = request.form.get("updated_text", "")

    if not pdf_id:
        flash("Missing document ID.")
        return redirect(url_for('text_editor_upload'))

    try:
        # Create new PDF from updated text
        output_pdf_path = os.path.join(UPLOAD_FOLDER, f"text_edited_{pdf_id}.pdf")
        doc = SimpleDocTemplate(output_pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph(new_text.replace("\n", "<br/>"), styles["Normal"])]
        doc.build(story)

        return send_file(output_pdf_path, as_attachment=True)
    except Exception as e:
        flash(f"Error creating edited PDF: {e}")
        return redirect(url_for('text_editor_upload'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)


# ---- Auto Cleanup Setup ----
import subprocess
import threading

def run_cleanup():
    subprocess.call(['python3', 'delete.py'])
    threading.Timer(600, run_cleanup).start()  # 600 seconds = 10 minutes

run_cleanup()
# ---- End Cleanup Setup ----
