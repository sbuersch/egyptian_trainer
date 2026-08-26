import random

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import Level, Lernweg, Phrase
from .models import UserProgress, Attempt
from .services import evaluate_user_input, get_help_info


def path_trainer_view(request):
    lernwege = Lernweg.objects.prefetch_related("levels__phrases__progress").all()

    # Ausgewähltes Level ermitteln
    selected_level_id = request.GET.get(
        "level_id"
    ) or request.POST.get("level_id")
    selected_level = None

    if selected_level_id:
        selected_level = Level.objects.filter(id=selected_level_id).first()

    if not selected_level and lernwege.exists():
        first_lernweg = lernwege.first()
        selected_level = first_lernweg.levels.first()

    # Lernwege-Daten inkl. Median-Berechnung aufbereiten
    paths_data = []
    for path in lernwege:
        levels_data = []
        for lvl in path.levels.all():
            phrases_in_lvl = list(lvl.phrases.all())
            total_count = len(phrases_in_lvl)

            # Zähle Phrasen mit Fortschritt
            reviewed_count = sum(
                1
                for p in phrases_in_lvl
                if hasattr(p, "progress")
                and p.progress.times_reviewed > 0
            )

            levels_data.append(
                {
                    "level": lvl,
                    "median": lvl.calculate_mastery_median(),
                    "total_count": total_count,
                    "reviewed_count": reviewed_count,
                }
            )
        paths_data.append({"path": path, "levels": levels_data})

    # Rechte Seite Logik (Modus 2 auf Level-Ebene)
    context = {
        "paths_data": paths_data,
        "selected_level": selected_level,
    }

    if not selected_level:
        context["no_data"] = True
        context["message"] = "Keine Lernwege vorhanden."
        return render(request, "learning/path_trainer.html", context)

    phrases = selected_level.phrases.all()

    if not phrases.exists():
        context["no_data"] = True
        context[
            "message"
        ] = f"Keine Phrasen im {selected_level.name} vorhanden."
        return render(request, "learning/path_trainer.html", context)

    if request.method == "POST":
        action = request.POST.get("action")
        phrase_id = request.POST.get("phrase_id")
        phrase = get_object_or_404(Phrase, id=phrase_id)
        progress = getattr(phrase, "progress", None)
        median = progress.median_score if progress else None

        if action == "skip":
            other_phrases = phrases.exclude(id=phrase_id)
            selected_phrase = (
                random.choice(list(other_phrases))
                if other_phrases.exists()
                else phrase
            )
            new_progress = getattr(selected_phrase, "progress", None)
            context.update(
                {
                    "phrase": selected_phrase,
                    "median_score": new_progress.median_score
                    if new_progress
                    else None,
                }
            )
            return render(request, "learning/path_trainer.html", context)

        elif action == "simple_help":
            context.update(
                {
                    "phrase": phrase,
                    "median_score": median,
                    "show_simple_help": True,
                }
            )
            return render(request, "learning/path_trainer.html", context)

        elif action == "detailed_help":
            help_info = get_help_info(phrase)
            context.update(
                {
                    "phrase": phrase,
                    "median_score": median,
                    "show_detailed_help": True,
                    "help_info": help_info,
                }
            )
            return render(request, "learning/path_trainer.html", context)

        user_input = request.POST.get("user_input", "")
        result = evaluate_user_input(phrase.german_sentence, user_input)
        score = result.get("score_1_to_10", 0)

        progress, _ = UserProgress.objects.get_or_create(phrase=phrase)
        progress.times_reviewed += 1
        progress.save()

        Attempt.objects.create(
            progress=progress, user_input=user_input, score=score
        )

        context.update(
            {
                "phrase": phrase,
                "user_input": user_input,
                "result": result,
                "score": score,
                "median_score": progress.median_score,
            }
        )
        return render(request, "learning/path_trainer.html", context)

    # Initialer Aufruf GET
    selected_phrase = random.choice(list(phrases))
    progress = getattr(selected_phrase, "progress", None)
    median = progress.median_score if progress else None

    context.update(
        {
            "phrase": selected_phrase,
            "median_score": median,
        }
    )
    return render(request, "learning/path_trainer.html", context)



def phrase_assignment_board_view(request):
    """Zeigt ein Kanban-Board mit allen Lernwegen/Levels sowie unbelegten Phrasen."""
    lernwege = Lernweg.objects.prefetch_related("levels__phrases").all()
    unassigned_phrases = Phrase.objects.filter(level__isnull=True)

    context = {
        "lernwege": lernwege,
        "unassigned_phrases": unassigned_phrases,
    }
    return render(request, "learning/phrase_board.html", context)


@require_POST
def update_phrase_level_ajax(request):
    """AJAX-Endpoint zum Verschieben einer Phrase in ein anderes Level (oder nach unassigned)."""
    phrase_id = request.POST.get("phrase_id")
    target_level_id = request.POST.get("level_id")

    if not phrase_id:
        return JsonResponse(
            {"success": False, "error": "Phrase-ID fehlt."}, status=400
        )

    try:
        phrase = Phrase.objects.get(id=phrase_id)

        if target_level_id == "unassigned" or not target_level_id:
            phrase.level = None
        else:
            target_level = Level.objects.get(id=target_level_id)
            phrase.level = target_level

        phrase.save()
        return JsonResponse({"success": True})
    except (Phrase.DoesNotExist, Level.DoesNotExist) as e:
        return JsonResponse({"success": False, "error": str(e)}, status=404)


@require_POST
def update_phrase_level_view(request):
    phrase_id = request.POST.get("phrase_id")
    target_level_id = request.POST.get("level_id")

    if not phrase_id or not target_level_id:
        return JsonResponse(
            {"success": False, "error": "Fehlende Parameter."}, status=400
        )

    try:
        phrase = Phrase.objects.get(id=phrase_id)
        target_level = Level.objects.get(id=target_level_id)
        phrase.level = target_level
        phrase.save()
        return JsonResponse({"success": True})
    except (Phrase.DoesNotExist, Level.DoesNotExist) as e:
        return JsonResponse({"success": False, "error": str(e)}, status=404)