import streamlit as st
from PIL import Image
import cv2
import numpy as np
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, pipeline

# Setup Streamlit
st.set_page_config(page_title="🖋️ Handwritten OCR + LLM Correction", layout="centered")
st.title("🖋️ Handwritten Image to Text Converter with LLM Correction")

# Load models
@st.cache_resource
def load_models():
    processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    corrector = pipeline("text2text-generation", model="vennify/t5-base-grammar-correction")
    return processor, model, corrector

processor, model, corrector = load_models()

# Preprocess image
def preprocess_image(image):
    image = np.array(image.convert("L"))  # Grayscale
    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    image = cv2.GaussianBlur(image, (5, 5), 0)
    image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY_INV, 11, 12)
    return Image.fromarray(cv2.bitwise_not(image))

# File upload
uploaded_file = st.file_uploader("📷 Upload a handwritten image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    original_image = Image.open(uploaded_file).convert("RGB")
    st.image(original_image, caption="📸 Original Image", use_column_width=True)

    # Preprocessing
    st.subheader("🧹 Preprocessing")
    preprocessed_image = preprocess_image(original_image)
    st.image(preprocessed_image, caption="🧼 Preprocessed Image", use_column_width=True)

    # Extract text with TrOCR
    with st.spinner("🔍 Extracting text..."):
        pixel_values = processor(images=preprocessed_image, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values)
        raw_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    st.subheader("📄 Raw Extracted Text:")
    st.text_area("Before Correction", raw_text, height=150)

    # Correct text
    with st.spinner("🧠 Correcting with LLM..."):
        corrected = corrector(raw_text, max_length=256)[0]['generated_text']

    st.subheader("✅ Cleaned & Corrected Text:")
    st.text_area("After Correction", corrected, height=150)

    # Save
    if st.button("💾 Save to File"):
        with open("corrected_output.txt", "w", encoding="utf-8") as f:
            f.write(corrected)
        st.success("Saved to `corrected_output.txt`")
