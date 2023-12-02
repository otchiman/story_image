import zipfile
import io
import json
import base64
import os


import streamlit as st
from PIL import Image
from PIL import UnidentifiedImageError
from dotenv import load_dotenv
from openai import OpenAI

import requests



def get_astica_key():
    #return os.getenv("ASTICA_API_KEY")
    return st.secrets["ASTICA_API_KEY"]

def get_openai_key():
    #return os.getenv("OPENAI_API_KEY")
    return st.secrets["OPENAI_API_KEY"]

# Modified function to handle in-memory files
def get_image_base64_encoding(in_memory_file, file_name):
    """
    Function to return the base64 string representation of an image
    """
    image_data = in_memory_file.getvalue()
    image_extension = os.path.splitext(file_name)[1]
    base64_encoded = base64.b64encode(image_data).decode('utf-8')
    return f"data:image/{image_extension[1:]};base64,{base64_encoded}"

def generate_caption(base64_string):

    # API configurations
    asticaAPI_key = os.getenv("ASTICA_API_KEY") # visit https://astica.ai
    asticaAPI_timeout = 1000 # in seconds. "gpt" or "gpt_detailed" require increased timeouts
    asticaAPI_endpoint = 'https://vision.astica.ai/describe'
    asticaAPI_modelVersion = '2.1_full' # '1.0_full', '2.0_full', or '2.1_full'

    asticaAPI_input =  base64_string 
    
    asticaAPI_visionParams = 'gpt, describe_all'  # comma separated, defaults to "all". 

    # Define payload dictionary
    asticaAPI_payload = {
        'tkn': asticaAPI_key,
        'modelVersion': asticaAPI_modelVersion,
        'visionParams': asticaAPI_visionParams,
        'input': asticaAPI_input,
        
    }
    # call API function and store result
    asticaAPI_result = asticaAPI(asticaAPI_endpoint, asticaAPI_payload, asticaAPI_timeout)

    if 'status' in asticaAPI_result:
        # Output Error if exists
        if asticaAPI_result['status'] == 'error':
            return 'Output:\n' + asticaAPI_result['error']
        # Output Success if exists
        if asticaAPI_result['status'] == 'success':
            if ('caption' in asticaAPI_result and asticaAPI_result['caption']['text'] != '') and ('caption_GPTS' in asticaAPI_result and asticaAPI_result['caption_GPTS'] != ''):
               
                return (asticaAPI_result['caption']['text'], asticaAPI_result['caption_GPTS'])
            
            
    else:
        return 'Invalid response'


def asticaAPI(endpoint, payload, timeout):
    response = requests.post(endpoint, data=json.dumps(payload), timeout=timeout, headers={ 'Content-Type': 'application/json', })
    if response.status_code == 200:
        return response.json()
    else:
        return {'status': 'error', 'error': 'Failed to connect to the API.'}

# Updated function to save images from a zip file and get their base64 encodings
def save_images_from_zip(zip_file):
    with zipfile.ZipFile(zip_file, 'r') as z:
        image_data_list = []  # List to store tuples of (Image, Base64 String)
        for filename in z.namelist():
            if any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
                try:
                    file_data = z.read(filename)
                    in_memory_file = io.BytesIO(file_data)
                    image = Image.open(in_memory_file)
                    base64_string = get_image_base64_encoding(in_memory_file, filename)
                    image_data_list.append((image, base64_string))
                except UnidentifiedImageError:
                    print(f"File {filename} is not a valid image and will be skipped.")
                except Exception as e:
                    print(f"An error occurred while processing {filename}: {e}")
        return image_data_list
    

def bundle_narrative_and_images(narrative, images, filename="bundle.zip"):
    with zipfile.ZipFile(filename, 'w') as bundle:
        # Add narrative as a text file
        with open("narrative.txt", "w") as text_file:
            text_file.write(narrative)
        bundle.write("narrative.txt")
        os.remove("narrative.txt")

        # Check if images are UploadedFile objects or tuples (image, base64_string)
        if images and isinstance(images[0], tuple):
            # Handling tuples from zip file upload
            for i, (image, _) in enumerate(images):
                image_filename = f"image_{i}.png"
                image.save(image_filename)
                bundle.write(image_filename)
                os.remove(image_filename)
        else:
            # Handling UploadedFile objects from individual file upload
            for i, file in enumerate(images):
                image_filename = f"image_{i}.png"
                with open(image_filename, "wb") as f:
                    f.write(file.getvalue())
                bundle.write(image_filename)
                os.remove(image_filename)

    return filename

def generate_narrative(captions_list):


    client = OpenAI(
        api_key=get_openai_key(),
    )

    
    primer=f"""
        Memories are cherished by all humans. It is what drives people. 
        In this context you are memorable narrative teller. Given pieces of 
        captions that describe images and narratives that describe them. Here is what to do:

            1. Merge the captions and narratives to create a memorable story using the only the context
        given. 
            2. Your response should only return the narrative, no captioning or headers
        should be returned.
            3. The narrative should capture all elements identified in the images. 
            4. Stories must be complete and coherent.
            5. Narratives should be at most 1000 words long.
    """

    # Combine captions into a single text
    augmented_strings = [
    f"'Caption': {caption} \n------\n 'Narrative': {description}\n---\n"
    for caption, description in captions_list
    ]

    # If you need one big string containing all augmented strings
    
    combined_captions = "\n".join(augmented_strings)
    

    # Generate a narrative
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": primer},
            {"role": "user", "content": combined_captions}, 
        ],
        temperature=0.0,
        max_tokens=2000,
    )
            

    return response.choices[0].message.content if response else "Failed to generate narrative."


    
def main():
    st. set_page_config(layout="wide")
    caption_list = []
    st.title("Tell a Story with Images🌁")
    with st.sidebar:
        st.subheader("🤖 About")
        st.markdown("This is a simple app that helps you make your media more memorable.")
        st.markdown("They say a picture is worth a thousand words. But what if you could make your pictures worth a thousand words?")
        st.markdown("This app uses the power of AI to generate a narrative for your images.")
        st.markdown("© Caleb Otchi. 2023.  All rights reserved.")

    upload_option = st.radio(
        "Choose your upload option:",
        ('Upload Individual Images', 'Upload a ZIP file'))

    if upload_option == 'Upload Individual Images':
        uploaded_files = st.file_uploader("Choose images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], help="Upload up to 5 images")
        if uploaded_files:
            for file in uploaded_files:
                # Convert UploadedFile to BytesIO
                in_memory_file = io.BytesIO(file.getvalue())
                base64_string = get_image_base64_encoding(in_memory_file, file.name)
                caption = generate_caption(base64_string)
                try:
                    caption_list.append(caption)
                except:
                    #throw error
                    st.error(caption)
            st.divider()
            st.success(f"Processed {len(uploaded_files)} Images Successfully!")
            st.divider()
            narrative = generate_narrative(caption_list)
            
            st.subheader("Here is your Story📖:", divider='rainbow')
            narrative = generate_narrative(caption_list)
            
            with st.expander("View"):
                st.markdown(narrative)

            bundle_filename = bundle_narrative_and_images(narrative, uploaded_files)
            with open(bundle_filename, "rb") as file:
                st.download_button("Download Images+Narrative", data=file, file_name=bundle_filename, mime="application/zip", on_click=st.balloons)

    elif upload_option == 'Upload a ZIP file':
        zip_file = st.file_uploader("Upload a ZIP file containing images", type='zip')
        if zip_file:
            images_from_zip = save_images_from_zip(zip_file)
            st.divider()
            st.success(f"Extracted {len(images_from_zip)} Images from ZIP File!")
            st.divider()
            for image, base64_string in images_from_zip:
                caption = generate_caption(base64_string)
                try:
                    caption_list.append(caption)
                    #caption_list.append(caption['text'])
                except:
                    #throw error
                    st.error(caption)
            
            st.divider()

            st.subheader("Here is your Story📖:", divider='rainbow')
            narrative = generate_narrative(caption_list)
            
            with st.expander("View"):
                st.markdown(narrative)
            bundle_filename = bundle_narrative_and_images(narrative, images_from_zip)
            with open(bundle_filename, "rb") as file:
                st.download_button("Download Images+Narrative", data=file, file_name=bundle_filename, mime="application/zip", on_click=st.balloons)


# Run the app
if __name__ == "__main__":
    main()
