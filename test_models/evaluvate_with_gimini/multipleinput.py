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

# ===== BATCH PROCESSING FUNCTION =====
def image_folder_to_markdown(folder_path):
    """
    Processes all image files in a given folder, extracts text using Gemini API,
    and saves the output to a student answers folder.
    """
    if not os.path.exists(folder_path):
        st.error(f"The specified folder path does not exist: {folder_path}")
        return

    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        st.warning(f"No image files found in the folder: {folder_path}")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, filename in enumerate(image_files):
        image_path = os.path.join(folder_path, filename)
        status_text.text(f"Processing image {i+1}/{len(image_files)}: {filename}")
        
        try:
            image = Image.open(image_path).convert("RGB")
            extracted_md = image_to_markdown(image)

            if extracted_md:
                # Find registration number from extracted text
                match = re.search(r"Reg\s*Number:\s*\$([^\n\r]+)", extracted_md, re.IGNORECASE)
                if match:
                    reg_number_raw = match.group(1)
                    reg_number = reg_number_raw.replace(" ", "")
                    safe_reg_number = reg_number.replace("/", "_").replace("\\", "_")

                    if not os.path.exists(STUDENT_ANSWERS_FOLDER):
                        os.makedirs(STUDENT_ANSWERS_FOLDER)
                    
                    md_path = os.path.join(STUDENT_ANSWERS_FOLDER, f"{safe_reg_number}.md")
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(extracted_md)
                    
                    st.session_state.student_md_files[safe_reg_number] = extracted_md
                    st.success(f"✅ Extracted text from {filename} for Reg. No. {reg_number} and saved.")
                else:
                    st.warning(f"⚠️ Could not find a registration number in {filename}. Skipping save.")
            else:
                st.error(f"❌ Failed to extract text from {filename}.")
        
        except Exception as e:
            st.error(f"An error occurred while processing {filename}: {e}")

        # Update progress bar
        progress = (i + 1) / len(image_files)
        progress_bar.progress(progress)
    
    st.success("🎉 Batch processing complete!")
    progress_bar.empty()
    status_text.empty()
    st.rerun() # Rerun to update the selectbox with new files


# ===== EVALUATION FUNCTION =====
def evaluate_answer(marking_md, student_md, reg_number):
    try:
        prompt = f"""
        You are an academic evaluator. Below are two sections:
        1. **Marking Scheme** – contains expected answer points for an essay, each followed by the mark allocation (e.g., [4 Marks]).
        2. **Student Answer** – the student's response to the same question.

        ---

        ### 🎯 TASK:
        Evaluate the student’s response against **each marking point**, using the mark allocation provided. For each point, identify whether it is:

        - ✅ Fully covered – award **full marks**
        - ⚠️ Partially covered – award **half marks**
        - ❌ Not covered – award **zero marks**

        ---

        ### 📝 Evaluation Format (Strictly follow):

        **Point**: *<Copied from marking scheme>*
        - **Allocated**: [X Marks]
        - **Evaluation**: ✅ / ⚠️ / ❌
        - **Awarded**: X / (X/2) / 0
        - **Comment**: <Why it was awarded that way>

        Do this for every point mentioned in the marking scheme.

        ---

        ### 📊 Final Summary:

        - Total Allocated: XX Marks
        - ✅ Full Marks Awarded: XX
        - ⚠️ Half Marks Awarded: XX
        - ❌ Zero Marks: XX
        - **Total Awarded**: XX Marks

        ---

        ### 📚 Marking Scheme:
        {marking_md}

        ---

        ### ✍️ Student Answer:
        {student_md}
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
st.header("1. Upload Marking Scheme")
marking_pdf = st.file_uploader("Upload Marking Scheme PDF", type="pdf")

if marking_pdf:
    st.session_state.uploaded_marking_pdf = marking_pdf
    st.success("✅ Marking PDF uploaded. Click 'Save Model Answers' to process.")

if st.button("💾 Save Model Answers"):
    if 'uploaded_marking_pdf' in st.session_state:
        with open(MARKING_PDF, "wb") as f:
            f.write(st.session_state.uploaded_marking_pdf.read())
        
        marking_md_content = convert_pdf_to_markdown_html(MARKING_PDF, MARKING_MD)
        split_questions_to_folder(MARKING_MD, QUESTIONS_FOLDER)
        st.session_state.marking_md_content = marking_md_content
        
        st.success("✅ Model answers saved and split into individual question files.")
    else:
        st.warning("⚠️ Please upload a marking scheme PDF first.")

# Section 2: Upload and Process Student Answers
st.header("2. Upload and Process Student Answers")

tab1, tab2 = st.tabs(["Upload Single Image", "Process a Folder of Images"])

with tab1:
    st.subheader("Upload a single image of a student's answer")
    student_image = st.file_uploader("Upload Student Answer Image", type=["jpg", "jpeg", "png"])
    if student_image:
        image = Image.open(student_image).convert("RGB")
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(image, caption="🖼️ Student Answer Image", use_container_width=True)
        
        with col2:
            if st.button("Extract Text from Single Image"):
                with st.spinner("Extracting text..."):
                    extracted_md = image_to_markdown(image)
                    if extracted_md:
                        match = re.search(r"Reg\s*Number:\s*\$([^\n\r]+)", extracted_md, re.IGNORECASE)
                        if match:
                            reg_number_raw = match.group(1)
                            reg_number = reg_number_raw.replace(" ", "")
                            safe_reg_number = reg_number.replace("/", "_").replace("\\", "_")
                            if not os.path.exists(STUDENT_ANSWERS_FOLDER):
                                os.makedirs(STUDENT_ANSWERS_FOLDER)
                            md_path = os.path.join(STUDENT_ANSWERS_FOLDER, f"{safe_reg_number}.md")
                            with open(md_path, "w", encoding="utf-8") as f:
                                f.write(extracted_md)

                            st.session_state.student_md_files[safe_reg_number] = extracted_md
                            st.markdown(f"### 📄 Extracted Text (Reg: {reg_number})")
                            st.markdown(extracted_md)
                        else:
                            st.error("Registration number not found in the extracted text. Make sure it starts with `Reg Number: $...`")
with tab2:
    st.subheader("Process a folder of student answer images")
    image_folder_path = st.text_input("Enter the folder path containing the images:")
    if st.button("🚀 Process All Images in Folder"):
        if image_folder_path:
            image_folder_to_markdown(image_folder_path)
        else:
            st.warning("Please enter a valid folder path.")

# Section 3: Evaluate Student Answer
st.header("3. Evaluate Student Answer")
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
elif not st.session_state.marking_md_content:
    st.warning("⚠️ Please upload and save the marking scheme PDF first (Section 1).")
elif not st.session_state.student_md_files:
    st.warning("⚠️ Please upload or process student answer images first (Section 2).")

# Section 4: View Previous Evaluations
st.header("4. View Previous Evaluations")
if st.session_state.evaluation_results:
    view_reg = st.selectbox("Select Student to View Evaluation", list(st.session_state.evaluation_results.keys()), key="view_evaluation_select")
    if view_reg:
        st.markdown(st.session_state.evaluation_results[view_reg])