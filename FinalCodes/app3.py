import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os

st.set_page_config(page_title="Gemini Handwriting Extractor", layout="centered")
st.title("🖋️ Automated Essay Grading System")

try:
    gemini_api_key = st.secrets["gemini"]["API_KEY"]
    genai.configure(api_key=gemini_api_key)
except KeyError:
    st.error("Gemini API key not found in secrets. Please add it to `secrets.toml`.")
    st.stop()

# Initialize the generative model
model = genai.GenerativeModel("gemini-2.5-flash")

uploaded_file = st.file_uploader("📷 Upload a handwritten image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Uploaded Image", use_container_width=True)

    if st.button("Extract Text"):
        with st.spinner("🧠 Asking Gemini..."):
            try:
                # Prepare the image and the prompt for the Gemini API
                img_data = io.BytesIO()
                image.save(img_data, format="JPEG")
                img_data.seek(0)
                
                # The prompt is combined with the image in the request
                #prompt = "This answers from students. some words in answers can cut by students and ignore those cut words.Full paragraphs also can be cut by students then also ignore them.Only consider the not cut things by students.Those are handwritten text so that they can be messy unclear and many more corruptions.Extract them as much as perfect way. Extract all handwritten text from this image as accurately as possible and format it as Markdown."
                #prompt = "Extract all handwritten text from the image. The content is a student's answers, and some parts are marked for removal. Strictly ignore any text or code that has a line drawn through it, as this indicates it has been 'cut' or deleted by the student. Also, disregard any text that is covered by shading or heavy scribbles. Focus exclusively on the content that is clearly not marked for removal. Since the text is handwritten, transcribe it as accurately as possible despite any messiness or corruption. Format the final extracted text using Markdown."
                prompt = "Analyze the attached image and extract all handwritten text. Your primary objective is to accurately identify and transcribe only the content that is not marked for deletion. You must follow this strict rule: if any text, code, or paragraph has a visible line drawn through it, you are to completely and utterly ignore that content. Under no circumstances should any crossed-out material be included in your output. Transcribe the remaining, unmarked handwritten text as perfectly as possible, and present the final result using Markdown."
                
                response = model.generate_content(
                    [prompt, Image.open(img_data)],
                    stream=True
                )
                response.resolve()  # Wait for the full response

                # Extract the text from the response
                extracted_text = ""
                for chunk in response:
                    if chunk.text:
                        extracted_text += chunk.text
                
                if extracted_text:
                    st.subheader("📄 Extracted Text:")
                    st.text_area("Text Output", extracted_text, height=250)
                else:
                    st.warning("Could not extract any text. Please try with a clearer image.")

            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.info("Please check your API key and image quality.")