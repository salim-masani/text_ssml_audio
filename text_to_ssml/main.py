import functions_framework
from google.cloud import storage
import re

@functions_framework.cloud_event
def txt_to_ssml(cloud_event):
    """Converts a text file to SSML, adds pauses, and uploads it to a bucket.

    Args:
        cloud_event (dict): Event payload.
    """

    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]

    if not file_name.endswith(".txt"):
        print(f"File {file_name} is not a text file. Skipping.")
        return

    storage_client = storage.Client(project="salim-m")

    input_bucket = storage_client.bucket(bucket_name)
    blob = input_bucket.blob(file_name)

    try:
        text_content = blob.download_as_text()

        # Add pauses and format as SSML. Adjust regex and pause length as needed.
        ssml_content = "<speak>"
        sentences = re.split(r'(?<=[.!?])\s+', text_content)  # Split into sentences.

        for sentence in sentences:
            ssml_content += sentence.strip() + '<break time="1s"/>' # Add 1s pause after each sentence.
        ssml_content += "</speak>"

        # Upload SSML file to ssml-files-bucket
        ssml_file_name = file_name.replace(".txt", ".ssml")
        ssml_bucket = storage_client.bucket("ssml-files-bucket")
        ssml_blob = ssml_bucket.blob(ssml_file_name)
        ssml_blob.upload_from_string(ssml_content, content_type="application/ssml+xml")

        print(f"Successfully converted {file_name} to {ssml_file_name}.")

        # Move original text file to text-ssml-completion/text/
        destination_blob_name = f"text/{file_name}"
        destination_bucket = storage_client.bucket("text-ssml-completion")
        input_bucket.copy_blob(blob, destination_bucket, destination_blob_name)
        input_bucket.delete_blob(file_name) #remove original file.

        print(f"Moved {file_name} to text-ssml-completion/text/")

    except Exception as e:
        print(f"Error processing {file_name}: {e}")
