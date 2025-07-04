"""
Tool to transcribe base64-encoded audio using OpenAI Whisper.
"""
import io
import base64
import tempfile
from autogen_core.tools import FunctionTool
import openai

def transcribe_audio(audio_data_uri: str) -> str:
    """Extract and transcribe audio data URI to text."""
    # Separate header and b64 data
    if ',' in audio_data_uri:
        header, b64data = audio_data_uri.split(',', 1)
    else:
        b64data = audio_data_uri
    audio_bytes = base64.b64decode(b64data)
    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        tmp_path = tmp.name
    # Use OpenAI Whisper API
    try:
        transcript = openai.Audio.transcribe("whisper-1", open(tmp_path, 'rb'))
        return transcript.text
    except Exception as e:
        return f"Error during transcription: {e}"

# Wrap in FunctionTool
t = FunctionTool(
    name="transcribe_audio",
    func=transcribe_audio,
    description="Transcribe audio data URI to text using Whisper model."
)
