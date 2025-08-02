import streamlit as st
from PIL import Image
import pytesseract
import openai
import difflib
import os

# Set your OpenAI API Key
openai.api_key = "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"

st.title("📝 Handwritten Essay Grader using LLM")

# Upload image
uploaded_file = st.file_uploader("Upload a handwritten essay image", type=["png", "jpg", "jpeg"])

# Text areas for user input
model_answer = st.text_area("✍️ Enter Model Answer (reference answer):", height=200)

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Essay", use_column_width=True)

    # OCR to extract text
    with st.spinner("🔍 Extracting text from image..."):
        extracted_text = pytesseract.image_to_string(image)
        st.subheader("📜 Extracted Essay Text")
        st.text_area("OCR Output:", extracted_text, height=200)

    if st.button("🔎 Grade Essay"):
        with st.spinner("⚙️ Grading in progress..."):
            prompt = f"""
You are an expert essay evaluator. Compare the student's answer with the model answer and give a score out of 10.

Model Answer:
{model_answer}

Student Answer:
{extracted_text}

Return:
1. Score out of 10
2. Justification for the score
3. Suggestions for improvement
"""

            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )

            result = response.choices[0].message.content
            st.subheader("📊 Evaluation Result")
            st.markdown(result)

