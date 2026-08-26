from django.contrib import admin
from .models import Phrase, UserProgress, WordPair


# Zeigt die Wortpaare direkt innerhalb der Phrase an
class WordPairInline(admin.TabularInline):
    model = WordPair
    extra = 0


@admin.register(Phrase)
class PhraseAdmin(admin.ModelAdmin):
    list_display = ("german_sentence", "arabic_script", "arabizi", "help_info", "created_at", "audio_file")
    search_fields = ("german_sentence", "arabic_script", "arabizi")
    inlines = [WordPairInline]


@admin.register(WordPair)
class WordPairAdmin(admin.ModelAdmin):
    list_display = ("german_word", "arabic_script", "arabizi", "phrase")
    search_fields = ("german_word", "arabic_script", "arabizi")


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = (
        "phrase",
        "times_reviewed",
        "last_reviewed",
    )