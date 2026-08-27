import numpy as np
from django.db import models


class Lernweg(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Level(models.Model):
    lernweg = models.ForeignKey(
        Lernweg, on_delete=models.CASCADE, related_name="levels"
    )
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=1)
    color = models.CharField(
        max_length=20, default="#e2e8f0"
    )  # Hex-Farbcode für die Schwierigkeit

    class Meta:
        ordering = ["order"]

    def calculate_mastery_median(self):
        scores = [
            phrase.progress.median_score
            for phrase in self.phrases.all()
            if hasattr(phrase, "progress")
            and phrase.progress.median_score is not None
        ]
        print("scores: ", scores)

        if not scores:
            return None
        return float(np.median(scores))

    def __str__(self):
        return f"{self.lernweg.name} - {self.name}"


class Phrase(models.Model):
    level = models.ForeignKey(
        Level,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="phrases",
    )
    order = models.PositiveIntegerField(
        default=0, db_index=True
    )
    german_sentence = models.CharField(max_length=500)
    arabic_script = models.CharField(max_length=500)
    arabizi = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    help_info = models.JSONField(null=True, blank=True)
    audio_file = models.FileField(
        upload_to="phrase_audio/", null=True, blank=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.german_sentence


class WordPair(models.Model):
    phrase = models.ForeignKey(
        Phrase, on_delete=models.CASCADE, related_name="words"
    )
    german_word = models.CharField(max_length=100)
    arabic_script = models.CharField(max_length=100)
    arabizi = models.CharField(max_length=100)

    conjugation_info = models.JSONField(null=True, blank=True)
    word_type = models.CharField(max_length=50, null=True, blank=True)
    root_letters = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.german_word} -> {self.arabizi}"


class UserProgress(models.Model):
    phrase = models.OneToOneField(
        Phrase, on_delete=models.CASCADE, related_name="progress"
    )
    times_reviewed = models.IntegerField(default=0)
    last_reviewed = models.DateTimeField(auto_now=True)
    median_score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Progress for {self.phrase.german_sentence[:30]}"


class Attempt(models.Model):
    progress = models.ForeignKey(UserProgress, on_delete=models.CASCADE)
    user_input = models.CharField(max_length=500)
    score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attempt {self.id}: {self.score}/10"