# import streamlit as st
# import openai
# from PIL import Image
# import io
# from io import BytesIO
# import base64
# # Define the image_to_base64 function
# def image_to_base64(image):
#     buffered = BytesIO()
#     image.save(buffered, format="JPEG")
#     return base64.b64encode(buffered.getvalue()).decode()

# st.set_page_config(page_title="GPT-4V Handwriting Extractor", layout="centered")
# st.title("🖋️ Handwritten Image to Text with GPT-4V")

# openai.api_key = st.secrets["OPENAI_API_KEY"]

# uploaded_file = st.file_uploader("📷 Upload a handwritten image", type=["jpg", "jpeg", "png"])

# if uploaded_file:
#     image = Image.open(uploaded_file).convert("RGB")
#     st.image(image, caption="Uploaded Image", use_column_width=True)

#     if st.button("Extract Text"):
#         with st.spinner("🧠 Asking GPT-4V..."):
#             # Convert image to byte stream
#             img_bytes = io.BytesIO()
#             image.save(img_bytes, format="JPEG")
#             img_bytes = img_bytes.getvalue()

#             response = openai.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "user", "content": [
#                         {"type": "text", "text": "Please extract all handwritten text from this image as accurately as possible."},
#                         {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_to_base64(image)}}
#                     ]}
#                 ],
#                 max_tokens=1000
#             )

#             text = response.choices[0].message.content
#             st.subheader("📄 Extracted Text:")
#             st.text_area("Text Output", text, height=250)

# # def image_to_base64(image):
# #     import base64
# #     buffered = io.BytesIO()
# #     image.save(buffered, format="JPEG")
# #     return base64.b64encode(buffered.getvalue()).decode("utf-8")


import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os

st.set_page_config(page_title="Gemini Handwriting Extractor", layout="centered")
st.title("🖋️ Handwritten Image to Text with Gemini")

# Configure the Gemini API key.
# It's best practice to use Streamlit secrets for this.
# You need to create a file named `.streamlit/secrets.toml`
# and add your API key like this:
# [gemini]
# API_KEY = "YOUR_GEMINI_API_KEY"
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
    st.image(image, caption="Uploaded Image", use_column_width=True)

    if st.button("Extract Text"):
        with st.spinner("🧠 Asking Gemini..."):
            try:
                # Prepare the image and the prompt for the Gemini API
                img_data = io.BytesIO()
                image.save(img_data, format="JPEG")
                img_data.seek(0)
                
                # The prompt is combined with the image in the request
                prompt = "Please extract all handwritten text from this image as accurately as possible."
                
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
