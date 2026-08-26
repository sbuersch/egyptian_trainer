import os
import tempfile
import torch
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Q
from voicetut_tts import VoiceTutTTS

from learning.models import Phrase


class Command(BaseCommand):
    help = "Generates and caches TTS audio for all Phrase objects missing an audio file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--device",
            type=str,
            default="cuda" if torch.cuda.is_available() else "cpu",
            help="Device to run TTS inference on ('cuda' or 'cpu'). Defaults to CUDA if available.",
        )
        parser.add_argument(
            "--speaker",
            type=str,
            default="Mohamed",
            help="Speaker voice to use for synthesis. Default: 'Mohamed'",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate audio even if an audio file already exists.",
        )

    def handle(self, *args, **options):
        device = options["device"]
        speaker = options["speaker"]
        force = options["force"]

        # Filter phrases needing audio
        if force:
            phrases = Phrase.objects.all()
        else:
            phrases = Phrase.objects.filter(Q(audio_file="") | Q(audio_file__isnull=True))

        total_count = phrases.count()
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("All phrases already have audio generated."))
            return

        self.stdout.write(f"Found {total_count} phrase(s) to process.")
        self.stdout.write(f"Loading VoiceTut-TTS model on device: {device}...")

        # Load model once outside the loop
        try:
            tts = VoiceTutTTS.from_pretrained(
                "mohammedaly22/VoiceTut-TTS",
                device=device,
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to load TTS model: {e}"))
            return

        success_count = 0
        error_count = 0

        # Create a temporary working directory for intermediate .wav files
        with tempfile.TemporaryDirectory() as temp_dir:
            for idx, phrase in enumerate(phrases, start=1):
                text_to_synthesize = phrase.arabic_script.strip()

                if not text_to_synthesize:
                    self.stdout.write(
                        self.style.WARNING(f"[{idx}/{total_count}] Skipping Phrase ID {phrase.id}: empty arabic_script.")
                    )
                    continue

                self.stdout.write(f"[{idx}/{total_count}] Synthesizing Phrase ID {phrase.id}: '{text_to_synthesize[:30]}...'")

                temp_file_path = os.path.join(temp_dir, f"temp_{phrase.id}.wav")

                try:
                    # 1. Synthesize to temporary WAV file
                    tts.synthesize(
                        text=text_to_synthesize,
                        speaker=speaker,
                        output=temp_file_path,
                    )

                    # 2. Read bytes and save into Django FileField
                    with open(temp_file_path, "rb") as f:
                        audio_bytes = f.read()

                    filename = f"phrase_{phrase.id}.wav"
                    phrase.audio_file.save(filename, ContentFile(audio_bytes), save=True)

                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Saved as {filename}"))

                except Exception as e:
                    error_count += 1
                    self.stderr.write(self.style.ERROR(f"  ✗ Failed for Phrase ID {phrase.id}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished processing! Successfully created: {success_count}, Errors: {error_count}."
            )
        )