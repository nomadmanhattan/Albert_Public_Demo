import os
import uuid
import logging
from google.cloud import texttospeech
from google.cloud import storage

logger = logging.getLogger(__name__)

class TextToSpeechService:
    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Journey-D"  # A pleasant, conversational voice
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        # GCS Configuration
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "albert-audio-assets-mvp")
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)

    def generate_audio(self, text: str) -> str:
        """
        Synthesizes speech from text and uploads it to GCS.
        Returns the public URL to the audio file.
        """
        logger.info("Generating audio via Vertex AI TTS...")
        
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=self.voice,
                audio_config=self.audio_config
            )

            # Generate unique filename
            filename = f"{uuid.uuid4()}.mp3"
            
            # Upload to GCS
            logger.info(f"Uploading audio to GCS bucket: {self.bucket_name}")
            blob = self.bucket.blob(filename)
            blob.upload_from_string(response.audio_content, content_type="audio/mpeg")
            
            # Make public (optional, or use signed URL if private)
            # For this MVP, we'll assume the bucket or object is accessible, 
            # or we can generate a signed URL. Let's use signed URL for security by default.
            
            # Generate Signed URL (valid for 1 hour)
            # Note: For a public podcast, you might want a public bucket.
            # But for a personal assistant, a signed URL is better.
            # However, the user asked for "remote CDN", so let's stick to a simple public URL structure 
            # if the bucket allows, OR just return the signed URL.
            
            # Let's try to make it public-read for simplicity if it's a "podcast"
            # But `upload_from_string` doesn't make it public by default.
            
            # For now, let's use a signed URL which is safer and works without changing bucket IAM.
            url = blob.generate_signed_url(
                version="v4",
                expiration=3600, # 1 hour
                method="GET"
            )
            
            logger.info(f"Audio uploaded successfully: {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to generate/upload audio: {e}")
            raise e
