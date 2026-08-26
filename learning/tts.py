import io
import os
import soundfile as sf
import numpy as np
import tempfile
import requests
from gradio_client import Client

# Global client to reuse
_tts_client = None

# Set your token here or load from environment variable
HF_TOKEN = os.getenv("HF_TOKEN")


def _get_tts_client():
    """Initialize and reuse the Gradio client"""
    global _tts_client
    if _tts_client is None:
        print("[TTS] Connecting to VoiceTut-TTS online Space...")
        _tts_client = Client("mohammedaly22/VoiceTut-TTS", token=HF_TOKEN)
        print("[TTS] Connected successfully!")
    return _tts_client


def get_egyptian_audio_bytes(arabic_text: str, speaker: str = "Mohamed") -> bytes:
    """
    Generates WAV bytes for the given Arabic text using the online VoiceTut-TTS Space.

    Args:
        arabic_text: The Arabic text to synthesize
        speaker: The speaker voice to use (default: "Mohamed")

    Returns:
        bytes: WAV audio data as bytes
    """
    try:
        client = _get_tts_client()
        print(f"[TTS] Synthesizing: {arabic_text[:50]}...")

        # Call the synthesis endpoint
        result = client.predict(
            text=arabic_text,
            api_name="/run_b_oneshot"
        )

        # DEBUG: Print what we got
        print(f"[TTS] Result type: {type(result)}")
        print(f"[TTS] Result: {result}")

        # Handle different result types
        audio_bytes = _extract_audio_bytes(result)

        # Validate we got actual audio
        if len(audio_bytes) < 1000:
            print(f"[TTS] ⚠️ Warning: Audio is very small ({len(audio_bytes)} bytes). This might be an error.")

        print(f"[TTS] ✅ Audio generated! Size: {len(audio_bytes)} bytes")
        return audio_bytes

    except Exception as e:
        print(f"[TTS] ❌ Error: {e}")
        raise RuntimeError(f"Failed to synthesize speech: {e}")


def _extract_audio_bytes(result) -> bytes:
    """Extract audio bytes from various result types"""

    # Case 1: Result is a tuple/list with file info
    if isinstance(result, (tuple, list)):
        for item in result:
            try:
                return _extract_audio_bytes(item)
            except:
                continue

    # Case 2: Result is a dict with file info
    if isinstance(result, dict):
        # Check for common keys
        for key in ['file', 'path', 'name', 'url', 'audio', 'data']:
            if key in result:
                try:
                    return _extract_audio_bytes(result[key])
                except:
                    continue

        # Check for 'value' key (common in gradio)
        if 'value' in result:
            return _extract_audio_bytes(result['value'])

    # Case 3: Result has 'read' method (file-like object)
    if hasattr(result, 'read'):
        data = result.read()
        if isinstance(data, bytes):
            return data

    # Case 4: Result has 'name' attribute (file path)
    if hasattr(result, 'name'):
        file_path = result.name
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()

    # Case 5: Result is a string (path or URL)
    if isinstance(result, str):
        # Check if it's a file path
        if os.path.exists(result):
            with open(result, "rb") as f:
                return f.read()

        # Check if it's a URL
        if result.startswith("http"):
            response = requests.get(result)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"Failed to download audio: HTTP {response.status_code}")

        # Check if it's a path from the Space's temp directory
        import glob
        possible_files = glob.glob(result)
        for file_path in possible_files:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    return f.read()

    # Case 6: Result is bytes
    if isinstance(result, bytes):
        return result

    # Case 7: Try to convert to string and check if it's a file path
    try:
        str_result = str(result)
        if os.path.exists(str_result):
            with open(str_result, "rb") as f:
                return f.read()
    except:
        pass

    raise Exception(f"Could not extract audio data from result: {type(result)} - {result}")


# Alternative version using tempfile to handle the result
def get_egyptian_audio_bytes_alternative(arabic_text: str) -> bytes:
    """
    Alternative version that uses the client's submit method to get the file.
    """
    try:
        client = _get_tts_client()
        print(f"[TTS] Synthesizing: {arabic_text[:50]}...")

        # Use submit to get the job
        job = client.submit(
            text=arabic_text,
            api_name="/run_b_oneshot"
        )

        # Wait for the result
        result = job.result()

        # The result should be the audio file
        if hasattr(result, 'value'):
            result = result.value

        # Extract audio bytes
        audio_bytes = _extract_audio_bytes(result)

        # Validate
        if len(audio_bytes) < 1000:
            # Try to get the file path from the result
            if isinstance(result, str) and os.path.exists(result):
                with open(result, "rb") as f:
                    audio_bytes = f.read()
            elif hasattr(result, 'name'):
                with open(result.name, "rb") as f:
                    audio_bytes = f.read()

        print(f"[TTS] ✅ Audio generated! Size: {len(audio_bytes)} bytes")
        return audio_bytes

    except Exception as e:
        print(f"[TTS] ❌ Error: {e}")
        raise