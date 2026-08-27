from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin
from django.contrib import admin
from django.shortcuts import render

from .models import Level, Lernweg, Phrase, UserProgress, WordPair, Attempt


class WordPairInline(admin.TabularInline):
    model = WordPair
    extra = 0


class LevelInline(admin.TabularInline):
    model = Level
    extra = 0


@admin.register(Lernweg)
class LernwegAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    inlines = [LevelInline]


class PhraseInline(SortableInlineAdminMixin, admin.TabularInline):
    model = Phrase
    fields = ("german_sentence", "arabic_script", "arabizi")
    extra = 1
    show_change_link = True


@admin.register(Level)
class LevelAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ("name", "lernweg", "order", "color")
    list_filter = ("lernweg",)
    inlines = [PhraseInline]


@admin.action(description="Ausgewählte Phrasen einem Level zuweisen")
def assign_to_level(modeladmin, request, queryset):
    if "apply" in request.POST:
        level_id = request.POST.get("level")
        level = Level.objects.get(id=level_id)
        updated_count = queryset.update(level=level)
        modeladmin.message_user(
            request, f"{updated_count} Phrasen erfolgreich zu '{level}' hinzugefügt."
        )
        return None

    levels = Level.objects.select_related("lernweg").all()
    return render(
        request,
        "admin/assign_level_intermediate.html",
        context={"phrases": queryset, "levels": levels},
    )


@admin.register(Phrase)
class PhraseAdmin(admin.ModelAdmin):
    list_display = (
        "german_sentence",
        "level",
        "arabic_script",
        "arabizi",
        "created_at",
    )
    list_filter = ("level__lernweg", "level")
    search_fields = ("german_sentence", "arabic_script", "arabizi")
    inlines = [WordPairInline]
    actions = [assign_to_level]
    list_per_page = 1000


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
        "median_score",
    )

@admin.register(Attempt)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = (
        "progress",
        "user_input",
        "score",
        "created_at",
    )