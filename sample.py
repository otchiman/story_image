import json
import base64
import os
from dotenv import load_dotenv

import requests


load_dotenv() # take environment variables from .env.
def get_image_base64_encoding(image_path: str) -> str:
    """
    Function to return the base64 string representation of an image
    """
    with open(image_path, 'rb') as file:
        image_data = file.read()
    image_extension = os.path.splitext(image_path)[1]
    
    base64_encoded = base64.b64encode(image_data).decode('utf-8')
    return f"data:image/{image_extension[1:]};base64,{base64_encoded}"


# API configurations
asticaAPI_key = os.getenv("ASTICA_API_KEY") # visit https://astica.ai
asticaAPI_timeout = 60 # in seconds. "gpt" or "gpt_detailed" require increased timeouts
asticaAPI_endpoint = 'https://vision.astica.ai/describe'
asticaAPI_modelVersion = '2.1_full' # '1.0_full', '2.0_full', or '2.1_full'



asticaAPI_input = get_image_base64_encoding('1 (3).jpeg')  # use base64 image input (slower)


# vision parameters:  https://astica.ai/vision/documentation/#parameters
asticaAPI_visionParams = 'describe_all'  # comma separated, defaults to "all". 


'''    
    '1.0_full' supported visionParams:
        describe
        objects
        categories
        moderate
        tags
        brands
        color
        faces
        celebrities
        landmarks
        gpt               (Slow)
        gpt_detailed      (Slower)

    '2.0_full' supported visionParams:
        describe
        describe_all
        objects
        tags
        describe_all 
        text_read 
        gpt             (Slow)
        gpt_detailed    (Slower)
        
    '2.1_full' supported visionParams:
        Supports all options 
        
'''

# Define payload dictionary
asticaAPI_payload = {
    'tkn': asticaAPI_key,
    'modelVersion': asticaAPI_modelVersion,
    'visionParams': asticaAPI_visionParams,
    'input': asticaAPI_input,
    
}



def asticaAPI(endpoint, payload, timeout):
    response = requests.post(endpoint, data=json.dumps(payload), timeout=timeout, headers={ 'Content-Type': 'application/json', })
    if response.status_code == 200:
        return response.json()
    else:
        return {'status': 'error', 'error': 'Failed to connect to the API.'}



# call API function and store result
asticaAPI_result = asticaAPI(asticaAPI_endpoint, asticaAPI_payload, asticaAPI_timeout)

# print API output
print('\nastica API Output:')
print(json.dumps(asticaAPI_result, indent=4))
print('=================')
print('=================')
# Handle asticaAPI response
if 'status' in asticaAPI_result:
    # Output Error if exists
    if asticaAPI_result['status'] == 'error':
        print('Output:\n', asticaAPI_result['error'])
    # Output Success if exists
    if asticaAPI_result['status'] == 'success':
        if 'caption_GPTS' in asticaAPI_result and asticaAPI_result['caption_GPTS'] != '':
            print('=================')
            print('GPT Caption:', asticaAPI_result['caption_GPTS'])
        if 'caption' in asticaAPI_result and asticaAPI_result['caption']['text'] != '':
            print('=================')
            print('Caption:', asticaAPI_result['caption']['text'])
        if 'CaptionDetailed' in asticaAPI_result and asticaAPI_result['CaptionDetailed']['text'] != '':
            print('=================')
            print('CaptionDetailed:', asticaAPI_result['CaptionDetailed']['text'])
        if 'objects' in asticaAPI_result:
            print('=================')
            print('Objects:', asticaAPI_result['objects'])
else:
    print('Invalid response') 

def bundle_narrative_and_images(narrative, images, filename="bundle.zip"):
    with zipfile.ZipFile(filename, 'w') as bundle:
        # Add narrative as a text file
        with open("narrative.txt", "w") as text_file:
            text_file.write(narrative)
        bundle.write("narrative.txt")
        os.remove("narrative.txt")

        # Add images
        for i, (image, _) in enumerate(images):
            image_filename = f"image_{i}.png"
            image.save(image_filename)
            bundle.write(image_filename)
            os.remove(image_filename)

    return filename


# Main interface
def main():
    st.title("Image Upload Interface")

    st.header("Upload Images")

    caption_list = []

    # Upload images (up to 5)
    uploaded_files = st.file_uploader("Choose images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], help="Upload up to 5 images")
    
    if uploaded_files:
        with st.spinner('Processing images...'):
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
            st.success(f"Processed {len(uploaded_files)} Images Successfully!")
            

    # Upload a zip file
    zip_file = st.file_uploader("Or upload a ZIP file containing images", type='zip')
    if zip_file:
        with st.spinner('Extracting images from ZIP file...'):
            images_from_zip = save_images_from_zip(zip_file)
            for image, base64_string in images_from_zip:
                caption = generate_caption(base64_string)
                try:
                    caption_list.append(caption)
                    #caption_list.append(caption['text'])
                except:
                    #throw error
                    st.error(caption)
            st.success(f"Extracted {len(images_from_zip)} Images from ZIP File!")

    # After processing captions
    narrative = generate_narrative(caption_list)
    st.write("Narrative based on your images:", narrative)

    # Bundle images and narrative
    if uploaded_files:
        bundle_filename = bundle_narrative_and_images(narrative, uploaded_files+images_from_zip)
        st.success("Your images and narrative are bundled into a zip file.")
        with open(bundle_filename, "rb") as file:
            st.download_button(
                label="Download Bundle",
                data=file,
                file_name=bundle_filename,
                mime="application/zip"
            )