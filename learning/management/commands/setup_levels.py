import matplotlib
import matplotlib.colors as mcolors
from django.core.management.base import BaseCommand
from learning.models import Lernweg, Level


class Command(BaseCommand):
    help = "Erstellt 3 Lernwege mit jeweils 10 leeren Levels und Farbverlauf"

    def handle(self, *args, **options):
        lernwege_names = [
            "Anfänger (A1)",
            "Mittelstufe (A2/B1)",
            "Fortgeschritten (B2+)",
        ]

        # Farbschema über matplotlib.colormaps abrufen
        cmap = matplotlib.colormaps["YlOrRd"]

        for name in lernwege_names:
            lernweg, created = Lernweg.objects.get_or_create(name=name)

            if created or lernweg.levels.count() == 0:
                self.stdout.write(f"Erstelle levels für Lernweg: {name}")

                for i in range(1, 11):
                    intensity = (i - 1) / 9.0
                    rgba = cmap(intensity)
                    hex_color = mcolors.to_hex(rgba)

                    Level.objects.create(
                        lernweg=lernweg,
                        name=f"Level {i}",
                        order=i,
                        color=hex_color,
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"10 Levels für '{name}' erfolgreich erstellt."
                    )
                )
            else:
                self.stdout.write(
                    f"Lernweg '{name}' existiert bereits und hat bereits Levels."
                )