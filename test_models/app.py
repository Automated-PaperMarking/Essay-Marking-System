import streamlit as st
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq

# Page config
st.set_page_config(page_title="📝 Handwritten Text Extractor", layout="centered")

st.title("🖋️ Handwritten Image to Text Converter")
st.markdown("This app extracts handwritten text from images using the **DeepSeek-VL LLM**.")

# Load the model & processor once
@st.cache_resource
def load_deepseek_model():
    model_name = "deepseek-ai/deepseek-vl-7b"
    processor = AutoProcessor.from_pretrained(model_name)
    model = AutoModelForVision2Seq.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"  # Sends to GPU if available
    )
    return processor, model

processor, model = load_deepseek_model()

# Upload image
uploaded_file = st.file_uploader("Upload a handwritten image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="📸 Uploaded Image", use_column_width=True)

    # Prompt for vision-language model
    prompt = "<|user|>\nWhat is the handwritten text in this image?\n<|image|>\n<image_placeholder>\n<|endofimage|>\n<|assistant|>"

    with st.spinner("🔍 Extracting text using DeepSeek-VL..."):
        # Preprocess input
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(
            "cuda" if torch.cuda.is_available() else "cpu",
            torch.float16 if torch.cuda.is_available() else torch.float32
        )

        # Generate output
        generated_ids = model.generate(**inputs, max_new_tokens=256)
        extracted_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    st.subheader("🧠 Extracted Text:")
    st.text_area("Result", extracted_text, height=200)

    # Save button
    if st.button("💾 Save Text as File"):
        with open("extracted_text.txt", "w", encoding="utf-8") as f:
            f.write(extracted_text)
        st.success("Text saved as `extracted_text.txt`")
