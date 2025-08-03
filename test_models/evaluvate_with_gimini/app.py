import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import fitz  # PyMuPDF
from markdownify import markdownify as md
import re
import uuid

# ===== CONFIGURATION =====
MARKING_PDF = "marking.pdf"
MARKING_MD = "marking.md"
QUESTIONS_FOLDER = "questions_md"
STUDENT_ANSWERS_FOLDER = "student_answers_md"

# ===== INITIALIZE SESSION STATE =====
if 'marking_md_content' not in st.session_state:
    st.session_state.marking_md_content = ""
if 'student_md_files' not in st.session_state:
    st.session_state.student_md_files = {}
if 'evaluation_results' not in st.session_state:
    st.session_state.evaluation_results = {}

# ===== GEMINI API SETUP =====
try:
    gemini_api_key = st.secrets["gemini"]["API_KEY"]
    genai.configure(api_key=gemini_api_key)
except KeyError:
    st.error("Gemini API key not found in secrets. Please add it to `D:\\Essay\\.streamlit\\secrets.toml`.")
    st.stop()

model = genai.GenerativeModel("gemini-2.5-flash")

# ===== PDF TO MARKDOWN CONVERSION =====
def convert_pdf_to_markdown_html(pdf_path, md_path):
    html_text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            html_text += page.get_text("html")
    markdown = md(html_text)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    return markdown

def remove_gibberish(text):
    lines = text.splitlines()
    cleaned = [
        line for line in lines
        if not re.fullmatch(r"[A-Za-z0-9+/=]{30,}", line.strip())
    ]
    return "\n".join(cleaned)

def split_questions_to_folder(markdown_path, output_folder):
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    cleaned_content = remove_gibberish(content)
    questions = re.split(r"\b(Q\d{1,2})\.\s*", cleaned_content, flags=re.IGNORECASE)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for i in range(1, len(questions), 2):
        q_num = questions[i].strip().upper()
        q_text = questions[i + 1].strip()
        file_name = os.path.join(output_folder, f"{q_num}.md")
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(f"### {q_num}\n\n{q_text}")

# ===== IMAGE TO MARKDOWN CONVERSION =====

def image_to_markdown(image):
    try:
        img_data = io.BytesIO()
        image.save(img_data, format="JPEG")
        img_data.seek(0)
        prompt = "Extract all handwritten text from this image as accurately as possible and format it as Markdown."
        response = model.generate_content(
            [prompt, Image.open(img_data)],
            stream=True
        )
        response.resolve()
        extracted_text = ""
        for chunk in response:
            if chunk.text:
                extracted_text += chunk.text
        return extracted_text if extracted_text else None
    except Exception as e:
        st.error(f"Error processing image: {e}")
        return None



# ===== EVALUATION FUNCTION =====
def evaluate_answer(marking_md, student_md, reg_number):
    try:
        prompt = f"""
        You are an academic evaluator. Below are two texts:
        1. **Marking Scheme**: Contains the expected answers or key points for an essay question.
        2. **Student Answer**: The student's response to the essay question.

        **Task**:
        - Compare the student's answer with the marking scheme.
        - Identify which key points from the marking scheme are present, partially present, or missing in the student's answer.
        - Provide a concise evaluation, including:
          - A score out of 100 based on completeness and accuracy.
          - A brief explanation of the score, highlighting strengths and weaknesses.

        **Marking Scheme**:
        {marking_md}

        **Student Answer**:
        {student_md}

        Format the response in Markdown with a score and explanation.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error evaluating answer: {e}")
        return None

# ===== STREAMLIT INTERFACE =====
st.set_page_config(page_title="Essay Paper Evaluation System", layout="wide")
st.title("📝 Essay Paper Evaluation System")

# Section 1: Upload Marking Scheme PDF
st.header("Upload Marking Scheme")
marking_pdf = st.file_uploader("Upload Marking Scheme PDF", type=["pdf"])
if marking_pdf:
    with open(MARKING_PDF, "wb") as f:
        f.write(marking_pdf.read())
    marking_md_content = convert_pdf_to_markdown_html(MARKING_PDF, MARKING_MD)
    split_questions_to_folder(MARKING_MD, QUESTIONS_FOLDER)
    st.session_state.marking_md_content = marking_md_content
    st.subheader("Marking Scheme (Markdown)")
    st.markdown(marking_md_content)

# Section 2: Upload Student Answer Image
st.header("Upload Student Answer")
student_image = st.file_uploader("Upload Student Answer Image", type=["jpg", "jpeg", "png"])
if student_image:
    image = Image.open(student_image).convert("RGB")
    st.image(image, caption="Student Answer Image", use_column_width=True)

    if st.button("Extract Text from Image"):
        with st.spinner("Extracting text..."):
            extracted_md = image_to_markdown(image)  # No reg_number passed
            if extracted_md:
                # Find line starting with 'Reg Number:' and containing '$'
                match = re.search(r"Reg\s*Number:\s*\$([^\n\r]+)", extracted_md, re.IGNORECASE)

                if match:
                    reg_number_raw = match.group(1)
                    reg_number = reg_number_raw.replace(" ", "")  # EG / 2020 / 3905 → EG/2020/3905
                    safe_reg_number = reg_number.replace("/", "_").replace("\\", "_")

                    # Save Markdown file under correct name
                    if not os.path.exists(STUDENT_ANSWERS_FOLDER):
                        os.makedirs(STUDENT_ANSWERS_FOLDER)
                    md_path = os.path.join(STUDENT_ANSWERS_FOLDER, f"{safe_reg_number}.md")
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(extracted_md)

                    # Save to session state
                    st.session_state.student_md_files[safe_reg_number] = extracted_md
                    st.subheader(f"Extracted Student Answer (Reg: {reg_number})")
                    st.markdown(extracted_md)
                else:
                    st.error("Registration number not found in the extracted text. Make sure it starts with `Reg Number: $...`")

                

# Section 3: Evaluate Student Answer
st.header("Evaluate Student Answer")
if st.session_state.marking_md_content and st.session_state.student_md_files:
    selected_reg = st.selectbox("Select Student Registration Number", list(st.session_state.student_md_files.keys()))
    if selected_reg and st.button("Evaluate Answer"):
        with st.spinner("Evaluating..."):
            student_md = st.session_state.student_md_files[selected_reg]
            evaluation = evaluate_answer(st.session_state.marking_md_content, student_md, selected_reg)
            if evaluation:
                st.session_state.evaluation_results[selected_reg] = evaluation
                st.subheader(f"Evaluation Results (Reg: {selected_reg})")
                st.markdown(evaluation)

# # Section 4: View Previous Evaluations
# st.header("Previous Evaluations")
# if st.session_state.evaluation_results:
#     view_reg = st.selectbox("Select Student to View Evaluation", list(st.session_state.evaluation_results.keys()))
#     if view_reg:
#         st.markdown(st.session_state.evaluation_results[view_reg])