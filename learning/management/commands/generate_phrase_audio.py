from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Q

from learning.models import Phrase
from learning.tts import get_egyptian_audio_bytes


class Command(BaseCommand):
    help = "Generates and caches TTS audio for all Phrase objects missing an audio file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate audio even if an audio file already exists.",
        )

    def handle(self, *args, **options):
        force = options["force"]

        if force:
            phrases = Phrase.objects.all()
        else:
            phrases = Phrase.objects.filter(Q(audio_file="") | Q(audio_file__isnull=True))

        total_count = phrases.count()
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("All phrases already have audio generated."))
            return

        self.stdout.write(f"Found {total_count} phrase(s) to process.")

        success_count = 0
        error_count = 0

        for idx, phrase in enumerate(phrases, start=1):
            text_to_synthesize = (phrase.arabic_script or "").strip()

            if not text_to_synthesize:
                self.stdout.write(
                    self.style.WARNING(f"[{idx}/{total_count}] Skipping Phrase ID {phrase.id}: empty arabic_script.")
                )
                continue

            self.stdout.write(f"[{idx}/{total_count}] Synthesizing Phrase ID {phrase.id}: '{text_to_synthesize[:30]}...'")

            try:
                audio_bytes = get_egyptian_audio_bytes(text_to_synthesize)
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