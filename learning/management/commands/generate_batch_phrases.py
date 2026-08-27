import random
from django.core.management.base import BaseCommand
from learning.models import Phrase
from learning.services import generate_batch_phrases


class Command(BaseCommand):
    help = "Generates 100 phrases in batches of 10 and saves them to the database."

    def handle(self, *args, **options):
        categories = [
            "Weltpolitik",
            "Weltpolitik",
            "Weltpolitik",
            "Innenpolitik",
            "Innenpolitik",
            "Innenpolitik",
            "Krieg",
            "Verbrechen",
            "Fußball",
            "Drogen",
            "Armut",
        ]

        total_target = 300 - 37
        batch_size = 50
        created_count = 0
        skipped_duplicates = 0

        self.stdout.write(self.style.NOTICE("Starting phrase generation..."))

        while created_count < total_target:
            current_batch_size = min(batch_size, total_target - created_count)
            category = random.choice(categories)

            new_phrases = generate_batch_phrases(
                count=current_batch_size, category=category
            )

            for item in new_phrases:
                german = item.get("german_sentence", "").strip()
                arabic = item.get("arabic_script", "").strip()
                arabizi = item.get("arabizi", "").strip()

                if not german:
                    continue

                exists = Phrase.objects.filter(
                    german_sentence__iexact=german
                ).exists()
                if not exists:
                    Phrase.objects.create(
                        german_sentence=german,
                        arabic_script=arabic,
                        arabizi=arabizi,
                    )
                    created_count += 1
                else:
                    skipped_duplicates += 1

            self.stdout.write(
                f"Progress: {created_count}/{total_target} created..."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created_count}, Skipped duplicates: {skipped_duplicates}"
            )
        )