import os
import re
import fitz  # This should work if PyMuPDF is correctly installed
import cv2
import numpy as np
from flask import Flask, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path

app = Flask(__name__)

# Folder paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Base directory
PDF_FOLDER = os.path.join(BASE_DIR, "Solutions")  # Folder where PDFs are stored
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")  # Folder where images are uploaded

# Flask configuration
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure required directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)


### TEXT SEARCH FUNCTION ###
def search_text_in_pdfs(query):
    results = []
    for filename in os.listdir(PDF_FOLDER):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, filename)
            doc = fitz.open(pdf_path)

            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                matches = re.findall(rf"(.{{0,50}}{query}.{{0,50}})", text, re.IGNORECASE)
                
                for match in matches:
                    highlighted_match = match.replace(query, f"<mark>{query}</mark>")
                    pdf_link = url_for('serve_pdf', filename=filename, _external=True) + f"#page={page_num+1}"
                    results.append((filename, highlighted_match, pdf_link))
    
    return results


### IMAGE SEARCH FUNCTIONS ###
def extract_images_from_pdfs():
    """Extract images from PDFs for comparison."""
    extracted_images = []
    for filename in os.listdir(PDF_FOLDER):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, filename)
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                images = doc[page_num].get_images(full=True)
                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_np = np.frombuffer(image_bytes, dtype=np.uint8)
                    image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
                    extracted_images.append((image, pdf_path, page_num + 1))
    
    return extracted_images


def compare_images(image1, image2):
    """Compare two images using ORB feature matching."""
    orb = cv2.ORB_create()

    keypoints1, descriptors1 = orb.detectAndCompute(image1, None)
    keypoints2, descriptors2 = orb.detectAndCompute(image2, None)

    if descriptors1 is None or descriptors2 is None:
        return 0  # No match if no keypoints found

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(descriptors1, descriptors2)

    if len(matches) == 0:
        return 0

    good_matches = [m for m in matches if m.distance < 50]  # Lower distance = better match
    return len(good_matches)


@app.route("/")
def home():
    return render_template("index.html", result=None)


@app.route("/search", methods=["POST"])
def search():
    query = request.form["query"]
    text_results = search_text_in_pdfs(query)
    
    if text_results:
        return render_template("index.html", text_results=text_results)
    else:
        return render_template("index.html", result="No matching text found.")


@app.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return render_template("index.html", result="No file selected.")

    file = request.files["file"]
    if file.filename == "":
        return render_template("index.html", result="No file selected.")

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        uploaded_image = cv2.imread(file_path)
        uploaded_image_gray = cv2.cvtColor(uploaded_image, cv2.COLOR_BGR2GRAY)

        extracted_images = extract_images_from_pdfs()

        best_match = None
        highest_score = 0
        for pdf_image, pdf_path, page in extracted_images:
            pdf_image_gray = cv2.cvtColor(pdf_image, cv2.COLOR_BGR2GRAY)
            score = compare_images(uploaded_image_gray, pdf_image_gray)

            if score > highest_score and score > 10:  # Minimum keypoint matches for similarity
                highest_score = score
                best_match = (pdf_path, page)

        if best_match:
            pdf_name = os.path.basename(best_match[0])
            result = f"Image found in {pdf_name} on Page {best_match[1]} <a href='/serve_pdf/{pdf_name}#page={best_match[1]}'>Open PDF</a>"
            return render_template("index.html", result=result)

    return render_template("index.html", result="No matching image found.")


@app.route("/serve_pdf/<filename>")
def serve_pdf(filename):
    return send_from_directory(PDF_FOLDER, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
