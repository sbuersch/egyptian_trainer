import os
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Optional, List
from .models import Phrase

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# --- GRUNDLEGENDE SCHEMAS ---

class ConjugationTense(BaseModel):
    """Konjugation für eine Zeitform"""
    ich: Optional[str] = None
    du: Optional[str] = None
    er_sie_es: Optional[str] = None
    wir: Optional[str] = None
    ihr: Optional[str] = None
    sie: Optional[str] = None


class ImperativeForm(BaseModel):
    """Imperativ-Formen"""
    du: Optional[str] = None
    ihr: Optional[str] = None
    wir: Optional[str] = None
    sie: Optional[str] = None


class ConjugationInfo(BaseModel):
    """Informationen zur Konjugation eines Wortes"""
    # Für Verben
    present_tense: Optional[ConjugationTense] = None
    past_tense: Optional[ConjugationTense] = None
    imperative: Optional[ImperativeForm] = None

    # Für Nomen/Adjektive
    singular: Optional[str] = None
    plural: Optional[str] = None
    feminine: Optional[str] = None
    masculine: Optional[str] = None

    # Allgemein
    notes: Optional[str] = None


class WordPairWithConjugation(BaseModel):
    german_word: str
    arabic_script: str
    arabizi: str
    word_type: str
    root_letters: Optional[str] = None
    conjugation_info: Optional[ConjugationInfo] = None


class GermanSituation(BaseModel):
    german_sentence: str
    arabic_script: str
    arabizi: str


class CorrectPhraseSchema(BaseModel):
    arabic_script: str
    arabizi: str


class EvaluationResult(BaseModel):
    score_1_to_10: int
    pronunciation_notes: str
    grammar_hints: str
    native_alternative: str
    correct_phrase: CorrectPhraseSchema
    words: List[WordPairWithConjugation]


class BatchPhrases(BaseModel):
    phrases: List[GermanSituation]


class WordWithConjugation(BaseModel):
    german_word: str
    arabic_script: str
    arabizi: str
    word_type: str
    conjugation_info: Optional[ConjugationInfo] = None


class HelpInfo(BaseModel):
    full_arabic_script: str
    full_arabizi: str
    word_by_word: List[WordWithConjugation]


# --- SERVICE-FUNKTIONEN ---

def generate_batch_phrases(count=10, category="Alltagssmalltalk"):
    """Generiert einen Stapel neuer Phrasen inkl. Wortzerlegung und Konjugation"""
    prompt = f"""Generiere genau {count} sehr einfache, unterschiedliche, nützliche Alltagssätze auf Deutsch, die man auf Ägyptisch-Arabisch (Masri) lernen sollte.

Fokus-Kategorie für diesen Stapel: {category}

Regeln:
- Nutze reale ÄGYPTISCHE AUSSPRACHE (Masri), kein Hocharabisch (Fusha).
- Variiere die Satzstrukturen und Vokabeln innerhalb des Stapels.
- Gib für jeden Satz die deutsche Variante, die ägyptisch-arabische Schrift, die Arabizi-Transkription an.

WICHTIG: Zerlege JEDEN Satz in seine einzelnen Wortpaare (words) MIT Konjugationsinformationen.

ANTWORTE NUR MIT DEM JSON-SCHEMA! Verwende exakt die vorgegebenen Feldnamen.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BatchPhrases,
            temperature=1.0,
        ),
    )

    result: BatchPhrases = response.parsed
    return [p.model_dump() for p in result.phrases]


def generate_new_situation():
    """Generiert eine neue Alltagssituation inkl. korrekter Übersetzung und Wortkonjugationen"""

    existing_phrases = list(
        Phrase.objects.values_list("german_sentence", flat=True).order_by(
            "-id"
        )[:20]
    )

    prompt = """Generiere genau einen einfachen, nützlichen Alltagssatz auf Deutsch, den man auf Ägyptisch-Arabisch (Masri) lernen sollte, sowie die dazugehörige korrekte ägyptische Übersetzung (in arabischer Schrift und Arabizi).

WICHTIG: Zerlege den Satz in seine einzelnen Wörter und gib für jedes Wort:
- Das deutsche Wort
- Die arabische Schrift
- Die Arabizi-Transkription
- Den Worttyp (verb, noun, adjective, adverb, preposition, pronoun, conjunction)
- Für Verben: Wurzelbuchstaben und Konjugation (Präsens, Vergangenheit, Imperativ)
- Für Nomen/Adjektive: Singular, Plural und ggf. feminin/maskulin

ANTWORTE NUR MIT DEM JSON-SCHEMA! Verwende exakt die vorgegebenen Feldnamen.
"""

    if existing_phrases:
        prompt += f"\n\nGeneriere KEINEN dieser bereits verwendeten Sätze:\n- " + "\n- ".join(
            existing_phrases
        )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GermanSituation,
            temperature=0.95,
        ),
    )

    result: GermanSituation = response.parsed
    return result.model_dump()


def evaluate_user_input(german_sentence, user_input):
    """Evaluiert die Ägyptisch-Eingabe des Nutzers bezüglich Phonetik, Grammatik und Richtigkeit.
    Inkludiert jetzt auch Konjugationsinformationen."""

    prompt = f"""Du bist ein ägyptischer Sprachlehrer für Alltagssprache (Masri).
Satz auf Deutsch: "{german_sentence}"
Eingabe des Nutzers (Ägyptisch in Arabisch oder Franco-Arabisch/Arabizi): "{user_input}"

Regeln für die Franco-Arabisch / Arabizi Transkription:
- Nutze für die Phonetische Umschrift die reale ÄGYPTISCHE AUSSPRACHE (Masri), nicht das Hocharabische (Fusha).
- Verwende für Fatha-Vokale in der Alltagssprache 'e' statt 'a' wo passend (z. B. 'bikem' statt 'bikam', 'kam' -> 'kem', 'ezayyak' -> 'ezayyek').
- Unterscheide klare Dialektmerkmale (z.B. 'g' statt 'j').

Aufgabe:
1. Bewerte die Genauigkeit/Richtigkeit der Übersetzung auf einer Skala von 1 bis 10 (10 = perfekt/natürlich, 1 = völlig falsch/unverständlich). Beachte dabei, dass im Franco-Arabischen/Arabizi verschiedene Schreibweisen üblich sind!
2. Gib Feedback zu Aussprache, Transkription und Grammatik.
3. Zerlege die richtige Übersetzung in Einzelwörter mit Konjugationsinformationen.

WICHTIG für jedes Wort in der Zerlegung:
- Bestimme den Typ: "verb", "noun", "adjective", "adverb", "preposition", "pronoun", "conjunction"
- Für Verben: Gib die Wurzelbuchstaben (root_letters) und Konjugation für Präsens, Vergangenheit und Imperativ an
- Für Nomen: Gib Singular, Plural und ggf. feminin/maskulin an
- Für Adjektive: Gib Singular, Plural und ggf. feminin/maskulin an

ANTWORTE NUR MIT DEM JSON-SCHEMA! Verwende exakt die vorgegebenen Feldnamen.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EvaluationResult,
        ),
    )

    result: EvaluationResult = response.parsed
    return result.model_dump()


def get_help_info(phrase):
    """
    Hilfe-Informationen für eine Phrase generieren (für Mode 2 und 3).
    Verwendet gecachte Daten aus der Datenbank, wenn verfügbar.
    """

    # 1. Prüfen ob bereits Hilfe-Informationen in der Datenbank existieren
    if phrase.help_info:
        return phrase.help_info

    # 2. Prüfen ob alle Wörter bereits Konjugationsinformationen haben
    #    (dann können wir sie aus den WordPair-Objekten rekonstruieren)
    words_with_conjugation = []
    all_have_conjugation = True

    for word in phrase.words.all():
        if word.conjugation_info:
            words_with_conjugation.append({
                "german_word": word.german_word,
                "arabic_script": word.arabic_script,
                "arabizi": word.arabizi,
                "word_type": word.word_type,
                "conjugation_info": word.conjugation_info,
            })
        else:
            all_have_conjugation = False
            break

    # 3. Wenn alle Wörter Konjugationsinformationen haben, baue HelpInfo daraus
    if all_have_conjugation and words_with_conjugation:
        help_info = {
            "full_arabic_script": phrase.arabic_script,
            "full_arabizi": phrase.arabizi,
            "word_by_word": words_with_conjugation,
        }

        # Cache in der Datenbank speichern für zukünftige Anfragen
        phrase.help_info = help_info
        phrase.save(update_fields=['help_info'])

        return help_info

    # 4. Fallback: Neue Hilfe von Gemini generieren (nur wenn nötig)
    prompt = f"""Analysiere den folgenden ägyptisch-arabischen Satz und gib eine detaillierte Wort-für-Wort-Übersetzung mit Konjugationsinformationen:

Deutscher Satz: "{phrase.german_sentence}"
Ägyptisch-Arabisch (Schrift): "{phrase.arabic_script}"
Ägyptisch-Arabisch (Arabizi): "{phrase.arabizi}"

Für JEDES Wort gib:
- Das deutsche Wort
- Die arabische Schrift
- Die Arabizi-Transkription
- Den Worttyp (verb, noun, adjective, adverb, preposition, pronoun, conjunction)
- Für Verben: Wurzelbuchstaben und Konjugation (Präsens, Vergangenheit, Imperativ)
- Für Nomen/Adjektive: Singular, Plural und ggf. feminin/maskulin

ANTWORTE NUR MIT DEM JSON-SCHEMA! Verwende exakt die vorgegebenen Feldnamen.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=HelpInfo,
            temperature=0.5,
        ),
    )

    result: HelpInfo = response.parsed
    help_info = result.model_dump()

    # Cache in der Datenbank speichern
    phrase.help_info = help_info
    phrase.save(update_fields=['help_info'])

    return help_info