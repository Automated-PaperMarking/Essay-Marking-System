import os
import re
import subprocess
import fitz  # PyMuPDF
from markdownify import markdownify as md

# ===== CONFIGURATION =====
pdf_input = "marking.pdf"
markdown_output = "marking.md"
questions_folder = "questions_md"
use_docling = False  # Set to True if you want to use docling instead of HTML method

# ===== METHOD 1: PyMuPDF + markdownify (HTML-based Markdown) =====
def convert_pdf_to_markdown_html(pdf_path, md_path):
    print("🔁 Using PyMuPDF + markdownify method...")
    html_text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            html_text += page.get_text("html")

    markdown = md(html_text)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"✅ Markdown saved to {md_path}")

# ===== METHOD 2: docling CLI =====
def convert_pdf_to_markdown_docling(pdf_path, md_path):
    print("🔁 Using docling CLI method...")
    command = [
        "docling", "parse", pdf_path,
        "--output-format", "markdown"
    ]
    with open(md_path, "w", encoding="utf-8") as output_file:
        subprocess.run(command, stdout=output_file, check=True)
    print(f"✅ Markdown saved to {md_path}")

# ===== CLEANING FUNCTION =====
def remove_gibberish(text):
    lines = text.splitlines()
    cleaned = [
        line for line in lines
        if not re.fullmatch(r"[A-Za-z0-9+/=]{30,}", line.strip())
    ]
    return "\n".join(cleaned)

# ===== SPLITTING QUESTIONS =====
def split_questions_to_folder(markdown_path, output_folder):
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()

    cleaned_content = remove_gibberish(content)

    # Split by Q1. Q2. Q3. etc.
    questions = re.split(r"\b(Q\d{1,2})\.\s*", cleaned_content, flags=re.IGNORECASE)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for i in range(1, len(questions), 2):
        q_num = questions[i].strip().upper()
        q_text = questions[i + 1].strip()
        file_name = os.path.join(output_folder, f"{q_num}.md")
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(f"### {q_num}\n\n{q_text}")
        print(f"✅ Saved: {file_name}")

# ===== RUN THE PIPELINE =====
if use_docling:
    convert_pdf_to_markdown_docling(pdf_input, markdown_output)
else:
    convert_pdf_to_markdown_html(pdf_input, markdown_output)

split_questions_to_folder(markdown_output, questions_folder)
