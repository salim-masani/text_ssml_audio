import functions_framework
from google.cloud import storage
from google.cloud import texttospeech
from google.cloud import pubsub_v1

@functions_framework.cloud_event
def ssml_to_audio(cloud_event):
    """Converts SSML to audio using the Text-to-Speech API and uploads it to a bucket."""

    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]

    if not file_name.endswith(".ssml"):
        print(f"File {file_name} is not an SSML file. Skipping.")
        return

    storage_client = storage.Client(project="salim-m")
    input_bucket = storage_client.bucket(bucket_name)
    blob = input_bucket.blob(file_name)

    try:
        ssml_content = blob.download_as_text()

        # Initialize Text-to-Speech client
        client = texttospeech.TextToSpeechClient()

        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_content)

        # Build the voice request, select the language code ("en-US") and the ssml voice gender ("male")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )

        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Perform the text-to-speech request on the text input with the selected voice parameters and audio file type
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Upload audio to audio-files-bucket1
        audio_file_name = file_name.replace(".ssml", ".mp3")
        audio_bucket = storage_client.bucket("audio-files-bucket1")
        audio_blob = audio_bucket.blob(audio_file_name)
        audio_blob.upload_from_string(response.audio_content, content_type="audio/mpeg")

        print(f"Successfully converted {file_name} to {audio_file_name}.")

        # Move original SSML file to text-ssml-completion/ssml/
        destination_blob_name = f"ssml/{file_name}"
        destination_bucket = storage_client.bucket("text-ssml-completion")
        input_bucket.copy_blob(blob, destination_bucket, destination_blob_name)
        input_bucket.delete_blob(file_name)

        print(f"Moved {file_name} to text-ssml-completion/ssml/")

        # Publish message to Pub/Sub topic
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path("salim-m", "eventarc-us-central1-ssml-to-audio-976148-902")
        message = file_name.encode("utf-8")
        future = publisher.publish(topic_path, message)
        future.result()  # Block until published

        print(f"Published message to {topic_path}: {file_name}")

    except Exception as e:
        print(f"Error processing {file_name}: {e}")
