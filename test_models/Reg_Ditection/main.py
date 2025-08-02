import streamlit as st
from PIL import Image
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# Streamlit UI setup
st.set_page_config(page_title="📝 Handwritten OCR with TrOCR", layout="centered")
st.title("🖋️ Handwritten Image to Text Converter")
st.markdown("Extract handwritten text from images using **Microsoft TrOCR**")

# Load TrOCR model
@st.cache_resource
def load_model():
    processor = TrOCRProcessor.from_pretrained("./trocr-finetuned")
    model = VisionEncoderDecoderModel.from_pretrained("./trocr-finetuned")
    # processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    # model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    return processor, model

processor, model = load_model()

# File upload
uploaded_file = st.file_uploader("Upload a handwritten image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="📸 Uploaded Image", use_container_width=True)

    # Run TrOCR
    with st.spinner("🔍 Extracting text..."):
        pixel_values = processor(images=image, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values)
        output_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    # Display result
    st.subheader("🧠 Extracted Text:")
    st.text_area("Result", output_text, height=200)

    # Save option
    if st.button("💾 Save Text as File"):
        with open("extracted_text.txt", "w", encoding="utf-8") as f:
            f.write(output_text)
        st.success("Text saved as `extracted_text.txt`")


