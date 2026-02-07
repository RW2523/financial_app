import whisper
import os
from typing import Optional

# Load Whisper model (tiny for speed, can use base/small/medium for accuracy)
MODEL = None


def load_whisper_model(model_size: str = "tiny"):
    """Load Whisper model - call this on startup"""
    global MODEL
    if MODEL is None:
        MODEL = whisper.load_model(model_size)
    return MODEL


def transcribe_audio(audio_file_path: str) -> str:
    """Transcribe audio file to text using Whisper"""
    if MODEL is None:
        load_whisper_model()

    try:
        result = MODEL.transcribe(audio_file_path)
        return result["text"].strip()
    except Exception as e:
        raise Exception(f"Whisper transcription error: {str(e)}")
