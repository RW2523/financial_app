import os
from typing import Optional

# Load Whisper model lazily (tiny for speed) so app starts even if openai-whisper isn't installed
MODEL = None


def load_whisper_model(model_size: str = "tiny"):
    """Load Whisper model on first use."""
    global MODEL
    if MODEL is not None:
        return MODEL
    try:
        import whisper
        MODEL = whisper.load_model(model_size)
        return MODEL
    except ImportError as e:
        raise Exception(
            "Voice input requires openai-whisper. If pip install failed with 'pkg_resources', run: "
            "pip install setuptools==81.0.0 && pip install openai-whisper --no-build-isolation"
        ) from e


def transcribe_audio(audio_file_path: str) -> str:
    """Transcribe audio file to text using Whisper."""
    model = load_whisper_model()
    try:
        result = model.transcribe(audio_file_path)
        return result["text"].strip()
    except Exception as e:
        raise Exception(f"Whisper transcription error: {str(e)}")
