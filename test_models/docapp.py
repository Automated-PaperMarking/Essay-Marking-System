import streamlit as st
from docling.document_converter import DocumentConverter
from PIL import Image
import tempfile
import os

st.set_page_config(page_title="Docling Handwritten Image to Markdown", layout="centered")
st.title("📝 Image to Markdown Text using Docling OCR")

st.write(
    "Upload an image containing handwritten or printed text. "
    "Docling will attempt to extract the text and convert it into Markdown format."
)

uploaded_file = st.file_uploader("📷 Upload an image file (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Save uploaded file to a temporary file (Docling works with file paths)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_filepath = tmp_file.name

    # Display image
    image = Image.open(tmp_filepath)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    if st.button("Extract Text and Convert to Markdown"):
        with st.spinner("Processing with Docling OCR..."):
            try:
                # Initialize Docling document converter
                converter = DocumentConverter()
                
                # Convert the image file to a Docling document object
                doc = converter.convert(tmp_filepath).document
                
                # Export extracted document content to Markdown format
                markdown_text = doc.export_to_markdown()

                # Display the markdown text in a text area
                st.subheader("Extracted Markdown Content:")
                st.text_area("Markdown Text", value=markdown_text, height=300)

                # Provide a download button for markdown file
                st.download_button(
                    label="📥 Download as Markdown File",
                    data=markdown_text,
                    file_name="extracted_text.md",
                    mime="text/markdown"
                )

            except Exception as e:
                st.error(f"An error occurred during OCR processing: {e}")

    # Clean up temporary file
    os.unlink(tmp_filepath)
