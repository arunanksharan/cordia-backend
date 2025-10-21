import httpx
import logging
from app.core.config import settings
from app.core.twilio import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

logger = logging.getLogger(__name__)

class SpeechToTextService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenAI API key is required for SpeechToTextService")
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/audio/transcriptions"

    async def transcribe_audio_url(self, audio_url: str) -> str | None:
        """
        Downloads an audio file from a URL and transcribes it using OpenAI's Whisper API.
        """
        try:
            # --- Step 1: Download Twilio recording ---
            async with httpx.AsyncClient(auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), follow_redirects=True) as twilio_client:
                response = await twilio_client.get(audio_url)
                response.raise_for_status()
                audio_data = response.content

            # --- Step 2: Send to OpenAI ---
            headers = {"Authorization": f"Bearer {self.api_key}"}
            files = {"file": ("audio.mp3", audio_data, "audio/mpeg")}
            data = {"model": "whisper-1"}

            async with httpx.AsyncClient() as openai_client:
                transcription_response = await openai_client.post(
                    self.api_url, headers=headers, files=files, data=data
                )
                transcription_response.raise_for_status()
                transcription = transcription_response.json()

            if "text" in transcription:
                return transcription["text"]
            else:
                logger.error(f"Transcription failed: 'text' not in response: {transcription}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during transcription: {e.response.text}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An error occurred during transcription: {e}", exc_info=True)
            return None


speech_to_text_service = SpeechToTextService(api_key=settings.OPENAI_API_KEY)
