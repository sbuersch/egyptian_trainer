# LOCAL:
import torch
from voicetut_tts import VoiceTutTTS

# Force CPU device execution
tts = VoiceTutTTS.from_pretrained(
    "mohammedaly22/VoiceTut-TTS",
    # device="cpu"
    device="cuda"
)

# Synthesize audio
tts.synthesize(
    text="ازيك عامل ايه النهاردة؟",
    speaker="Mohamed",
    output="out_cpu.wav"
)

# ONLINE:
# from gradio_client import Client
#
# client = Client("mohammedaly22/VoiceTut-TTS")
#
# # Use the one-shot synthesis endpoint
# result = client.predict(
#     text="ازيك عامل ايه النهاردة؟",
#     # speaker="Mohamed",
#     api_name="/run_b_oneshot"  # Endpoint 3
# )
#
# print(f"Audio saved at: {result}")