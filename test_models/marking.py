import fitz  # PyMuPDF
from markdownify import markdownify as md

# Step 1: Extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("html")  # HTML extraction for better structure
    return text

# Step 2: Convert HTML to Markdown
def convert_html_to_markdown(html_text, output_md_path):
    markdown = md(html_text)
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"✅ Markdown saved to {output_md_path}")

# Usage
pdf_path = "marking.pdf"
output_md_path = "marking_sheet.md"
html_text = extract_text_from_pdf(pdf_path)
convert_html_to_markdown(html_text, output_md_path)
