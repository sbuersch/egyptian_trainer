import random

from django.core.files.base import ContentFile
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, HttpResponseNotFound

from .models import Phrase, UserProgress, WordPair, Attempt
from .services import evaluate_user_input, generate_new_situation, generate_batch_phrases, get_help_info
from .tts import get_egyptian_audio_bytes


def index(request):
    return render(request, "trainer/index.html")


# --- MODUS 1: Neue Phrase lernen ---
def mode1_view(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "discard":
            for key in [
                "current_german",
                "current_solution",
                "last_result",
                "user_input",
            ]:
                request.session.pop(key, None)

            situation_data = generate_new_situation()
            request.session["current_german"] = situation_data["german_sentence"]
            request.session["current_solution"] = situation_data

            return render(
                request,
                "trainer/mode1.html",
                {
                    "german_sentence": situation_data["german_sentence"],
                    "solution": situation_data,
                },
            )
        elif action == "reset":
            for key in ["current_german", "last_result", "user_input"]:
                request.session.pop(key, None)
            return render(request, "trainer/mode1.html")

        elif action == "generate":
            situation_data = generate_new_situation()
            request.session["current_german"] = situation_data["german_sentence"]
            request.session["current_solution"] = situation_data
            request.session.pop("last_result", None)
            request.session.pop("user_input", None)

            return render(
                request,
                "trainer/mode1.html",
                {
                    "german_sentence": situation_data["german_sentence"],
                    "solution": situation_data,
                },
            )

        elif action == "evaluate":
            german_sentence = request.session.get("current_german")
            user_input = request.POST.get("user_input", "")

            result = evaluate_user_input(german_sentence, user_input)

            request.session["last_result"] = result
            request.session["user_input"] = user_input

            score = result.get("score_1_to_10", 0)
            is_acceptable = score >= 8

            return render(
                request,
                "trainer/mode1.html",
                {
                    "german_sentence": german_sentence,
                    "user_input": user_input,
                    "result": result,
                    "evaluated": True,
                    "score": score,
                    "is_acceptable": is_acceptable,
                },
            )

        elif action == "save":
            german_sentence = request.session.get("current_german")
            result = request.session.get("last_result")
            user_input = request.session.get("user_input", "")

            if result and german_sentence:
                phrase = Phrase.objects.create(
                    german_sentence=german_sentence,
                    arabic_script=result["correct_phrase"]["arabic_script"],
                    arabizi=result["correct_phrase"]["arabizi"],
                )

                # Wörter mit Fallbacks speichern
                for w in result.get("words", []):
                    WordPair.objects.create(
                        phrase=phrase,
                        german_word=w.get("german_word", ""),
                        arabic_script=w.get("arabic_script", ""),
                        arabizi=w.get("arabizi", ""),
                        word_type=w.get("word_type", ""),
                        root_letters=w.get("root_letters", ""),  # Fallback auf leerer String
                        conjugation_info=w.get("conjugation_info", None),
                    )

                UserProgress.objects.create(phrase=phrase)

                for key in ["current_german", "last_result", "user_input"]:
                    request.session.pop(key, None)

                return render(
                    request,
                    "trainer/mode1.html",
                    {
                        "german_sentence": german_sentence,
                        "user_input": user_input,
                        "result": result,
                        "saved": True,
                    },
                )

    german_sentence = request.session.get("current_german")
    result = request.session.get("last_result")
    user_input = request.session.get("user_input")

    context = {}
    if german_sentence:
        context["german_sentence"] = german_sentence

    score = result.get("score_1_to_10", 0) if result else 0
    if result:
        context["result"] = result
        context["user_input"] = user_input
        context["evaluated"] = True
        context["score"] = score
        context["is_acceptable"] = score >= 8

    solution = request.session.get("current_solution")
    if solution:
        context["solution"] = solution

    return render(request, "trainer/mode1.html", context)


# --- MODUS 2: Gespeicherte Phrasen üben ---
def mode2_view(request):
    phrases = Phrase.objects.all()

    if not phrases.exists():
        return render(
            request,
            "trainer/mode2.html",
            {
                "no_data": True,
                "message": "Noch keine Phrasen vorhanden. Lerne zuerst neue Phrasen in Modus 1!",
            },
        )

    if request.method == "POST":
        action = request.POST.get("action")
        phrase_id = request.POST.get("phrase_id")
        phrase = Phrase.objects.get(id=phrase_id)
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
            return render(
                request,
                "trainer/mode2.html",
                {
                    "phrase": selected_phrase,
                    "median_score": new_progress.median_score
                    if new_progress
                    else None,
                },
            )

        elif action == "simple_help":
            # Einfache Hilfe: Nur Arabizi anzeigen
            return render(
                request,
                "trainer/mode2.html",
                {
                    "phrase": phrase,
                    "median_score": median,
                    "show_simple_help": True,
                },
            )

        elif action == "detailed_help":
            # Detaillierte Hilfe mit Wort-für-Wort und Konjugationen
            help_info = get_help_info(phrase)
            return render(
                request,
                "trainer/mode2.html",
                {
                    "phrase": phrase,
                    "median_score": median,
                    "show_detailed_help": True,
                    "help_info": help_info,
                },
            )

        user_input = request.POST.get("user_input", "")
        result = evaluate_user_input(phrase.german_sentence, user_input)
        score = result.get("score_1_to_10", 0)

        progress, _ = UserProgress.objects.get_or_create(phrase=phrase)
        progress.times_reviewed += 1
        progress.save()

        Attempt.objects.create(
            progress=progress, user_input=user_input, score=score
        )

        return render(
            request,
            "trainer/mode2.html",
            {
                "phrase": phrase,
                "user_input": user_input,
                "result": result,
                "score": score,
                "median_score": progress.median_score,
            },
        )

    selected_phrase = random.choice(list(phrases))
    progress = getattr(selected_phrase, "progress", None)
    median = progress.median_score if progress else None

    return render(
        request,
        "trainer/mode2.html",
        {"phrase": selected_phrase, "median_score": median},
    )


# --- MODUS 3: Einzelne Wörter üben ---
def mode3_view(request):
    words = WordPair.objects.all()

    if not words.exists():
        return render(
            request,
            "trainer/mode3.html",
            {
                "no_data": True,
                "message": "Noch keine Wörter vorhanden. Lerne zuerst Phrasen in Modus 1!",
            },
        )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "skip":
            current_id = request.POST.get("word_id")
            other_words = words.exclude(id=current_id)
            selected_word = (
                random.choice(list(other_words))
                if other_words.exists()
                else random.choice(list(words))
            )
            return render(request, "trainer/mode3.html", {"word": selected_word})

        elif action == "retry":
            word_id = request.POST.get("word_id")
            word = WordPair.objects.get(id=word_id)
            return render(request, "trainer/mode3.html", {"word": word})

        word_id = request.POST.get("word_id")
        user_input = request.POST.get("user_input", "").strip().lower()
        word = WordPair.objects.get(id=word_id)

        is_correct = (user_input == word.arabizi.lower()) or (
            user_input == word.arabic_script
        )

        return render(
            request,
            "trainer/mode3.html",
            {
                "word": word,
                "user_input": user_input,
                "is_correct": is_correct,
                "checked": True,
            },
        )

    selected_word = random.choice(list(words))
    return render(request, "trainer/mode3.html", {"word": selected_word})


@require_POST
def generate_100_phrases_view(request):
    """Generiert 100 Phrasen in 10er-Batches ohne Riesentext-Prompts."""
    categories = [
        "Einkaufen und Verhandeln auf dem Markt",
        "Im Restaurant oder Café bestellen",
        "Wegbeschreibung, Taxi und öffentliche Verkehrsmittel",
        "Begrüßungen, Höflichkeit und alltäglicher Smalltalk",
        # "Notfälle, Arztbesuch und Apotheke",
        "Wohnung, Mietvertrag und Handwerker",
        "Freunde treffen, Freizeit und Hobbys",
        "Wetter, Zeitangaben und Verabredungen",
        "Erzählung was Freunde machen",
        "Lästern"
    ]

    total_target = 100
    batch_size = 10
    created_count = 0
    skipped_duplicates = 0

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

    return JsonResponse(
        {
            "status": "success",
            "created": created_count,
            "skipped_duplicates": skipped_duplicates,
        }
    )


def tts_audio_view(request):
    phrase_id = request.GET.get("phrase_id")
    text = request.GET.get("text", "").strip()

    # Retrieve phrase by ID or by matching arabic_script text
    phrase = None
    if phrase_id:
        phrase = Phrase.objects.filter(id=phrase_id).first()
    elif text:
        phrase = Phrase.objects.filter(arabic_script=text).first()

    if not phrase:
        return HttpResponseNotFound("Phrase nicht gefunden.")

    # 1. Check if audio is already cached
    if phrase.audio_file:
        try:
            phrase.audio_file.open("rb")
            audio_bytes = phrase.audio_file.read()
            phrase.audio_file.close()
            return HttpResponse(audio_bytes, content_type="audio/wav")
        except Exception:
            # Fallback to re-generation if file on disk was removed
            pass

    # 2. Synthesize audio if not cached
    try:
        synth_text = phrase.arabic_script or text
        audio_bytes = get_egyptian_audio_bytes(synth_text)

        # 3. Save to Model and Disk
        filename = f"phrase_{phrase.id}.wav"
        phrase.audio_file.save(filename, ContentFile(audio_bytes), save=True)

        return HttpResponse(audio_bytes, content_type="audio/wav")
    except Exception as e:
        return HttpResponseBadRequest(f"Audio-Generierung fehlgeschlagen: {e}")