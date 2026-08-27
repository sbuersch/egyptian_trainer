# learning/management/commands/generate_static_site.py

import os
import json
import random
from django.core.management.base import BaseCommand
from django.template import Template, Context
from django.template.defaultfilters import register
from django.utils.safestring import mark_safe
from django.conf import settings
from learning.models import Lernweg, Level, Phrase, WordPair, UserProgress, Attempt


class Command(BaseCommand):
    help = 'Generates a single static index.html with all learning content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='docs/index.html',
            help='Output filename (default: index.html)',
        )

    def handle(self, *args, **options):
        output_file = options['output']

        # Build the static HTML content
        html_content = self.generate_static_html()

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.stdout.write(self.style.SUCCESS(f'✅ Static site generated: {output_file}'))
        self.stdout.write(self.style.SUCCESS(f'📁 File saved to: {os.path.abspath(output_file)}'))

    def generate_static_html(self):
        """Generate the complete static HTML content"""

        # Gather all data from database
        paths_data = self.get_paths_data()
        phrases = list(Phrase.objects.select_related('level', 'progress').all())
        word_pairs = list(WordPair.objects.select_related('phrase').all())

        # Prepare data for JavaScript
        phrases_data = self.prepare_phrases_json(phrases, word_pairs)

        # Build the HTML template
        template_str = self.get_html_template()

        template = Template(template_str)
        context = Context({
            'paths_data': paths_data,
            'phrases_json': mark_safe(json.dumps(phrases_data, ensure_ascii=False)),
            'has_data': len(phrases) > 0,
            'total_phrases': len(phrases),
            'total_words': len(word_pairs),
            'MEDIA_URL': settings.MEDIA_URL if hasattr(settings, 'MEDIA_URL') else '/media/',
        })

        return template.render(context)

    def get_paths_data(self):
        """Get all paths, levels and their progress data"""
        paths_data = []

        for path in Lernweg.objects.all():
            levels_data = []
            for level in path.levels.all().order_by('order'):
                phrases_in_level = level.phrases.all()
                total_count = phrases_in_level.count()
                reviewed_count = UserProgress.objects.filter(
                    phrase__in=phrases_in_level,
                    times_reviewed__gt=0
                ).count()

                # Calculate median score
                median = level.calculate_mastery_median()

                levels_data.append({
                    'level': level,
                    'total_count': total_count,
                    'reviewed_count': reviewed_count,
                    'median': median,
                })

            paths_data.append({
                'path': path,
                'levels': levels_data,
            })

        return paths_data

    def prepare_phrases_json(self, phrases, word_pairs):
        """Prepare phrases data as JSON for JavaScript"""
        phrase_dict = {}

        for phrase in phrases:
            # Get words for this phrase
            words = [w for w in word_pairs if w.phrase_id == phrase.id]
            words_data = []
            for w in words:
                words_data.append({
                    'german_word': w.german_word,
                    'arabic_script': w.arabic_script,
                    'arabizi': w.arabizi,
                    'word_type': w.word_type,
                    'root_letters': w.root_letters,
                    'conjugation_info': w.conjugation_info,
                })

            progress = getattr(phrase, 'progress', None)

            phrase_dict[str(phrase.id)] = {
                'id': phrase.id,
                'german_sentence': phrase.german_sentence,
                'arabic_script': phrase.arabic_script,
                'arabizi': phrase.arabizi,
                'level_id': phrase.level_id,
                'level_name': phrase.level.name if phrase.level else None,
                'words': words_data,
                'progress': {
                    'times_reviewed': progress.times_reviewed if progress else 0,
                    'median_score': progress.median_score if progress else None,
                } if progress else None,
            }

        return phrase_dict

    def get_html_template(self):
        """Return the complete HTML template as a string"""
        return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇪🇬 Ägyptisch Lernen - Static Version</title>
    <style>
        /* ===== RESET & BASE ===== */
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f1f5f9;
            color: #0f172a;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }

        /* ===== HEADER ===== */
        .header {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            color: white;
            padding: 20px 30px;
            border-radius: 12px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .header h1 { font-size: 1.8em; }
        .header .badge {
            background: #2563eb;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85em;
        }
        .header .badge.offline {
            background: #dc2626;
        }

        /* ===== LAYOUT ===== */
        .split-container {
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }
        .left-path-view {
            flex: 1;
            background: #ffffff;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            max-height: 85vh;
            overflow-y: auto;
            min-width: 280px;
        }
        .right-exercise-view {
            flex: 1.5;
        }

        /* ===== PATH VIEW ===== */
        .path-section { margin-bottom: 25px; }
        .path-title {
            font-size: 1.1em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #1e293b;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 5px;
        }
        .level-node-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .level-card {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            border-radius: 6px;
            text-decoration: none;
            color: #0f172a;
            border: 2px solid transparent;
            cursor: pointer;
            transition: all 0.2s ease;
            background: #f8fafc;
        }
        .level-card:hover {
            transform: translateX(4px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .level-card.active {
            border-color: #2563eb;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
            font-weight: bold;
        }
        .level-card.drag-over {
            border: 2px dashed #2563eb !important;
            transform: scale(1.02);
        }
        .level-card .level-name { font-weight: 500; }
        .level-card .level-count {
            font-size: 0.75em;
            color: #475569;
        }
        .badge-score {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            background: rgba(255,255,255,0.9);
        }
        .badge-score.good { background: #dcfce7; color: #16a34a; }
        .badge-score.medium { background: #fef9c3; color: #d97706; }
        .badge-score.bad { background: #fee2e2; color: #dc2626; }
        .badge-score.untrained { background: #e2e8f0; color: #64748b; }

        /* ===== CARDS ===== */
        .card {
            background: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }
        .card h2 { font-size: 1.3em; margin-bottom: 8px; }
        .card h3 { font-size: 1.1em; margin: 10px 0; }
        .card h4 { font-size: 1em; margin: 12px 0 6px 0; color: #475569; }

        .draggable-phrase {
            cursor: grab;
            transition: opacity 0.2s;
        }
        .draggable-phrase:active {
            cursor: grabbing;
            opacity: 0.6;
        }
        .draggable-phrase.dragging {
            opacity: 0.4;
        }

        /* ===== ARABIC ===== */
        .arabic {
            font-family: 'Amiri', 'Traditional Arabic', serif;
            font-size: 1.8em;
            line-height: 1.4;
            direction: rtl;
        }
        .arabic.small { font-size: 1.2em; }

        /* ===== FORMS ===== */
        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 1.1em;
            transition: border-color 0.2s;
        }
        input[type="text"]:focus {
            border-color: #2563eb;
            outline: none;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 0.95em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .btn-primary { background: #2563eb; color: white; }
        .btn-success { background: #16a34a; color: white; }
        .btn-warning { background: #eab308; color: #1e293b; }
        .btn-purple { background: #8b5cf6; color: white; }
        .btn-gray { background: #64748b; color: white; }
        .btn-danger { background: #dc2626; color: white; }

        .btn-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
        }

        /* ===== HELP / RESULT ===== */
        .help-box {
            padding: 15px;
            border-radius: 6px;
            margin: 10px 0;
        }
        .help-box.yellow { background: #fef9c3; border-left: 5px solid #eab308; }
        .help-box.purple { background: #f3e8ff; border-left: 5px solid #8b5cf6; }
        .help-box.green { background: #dcfce7; border-left: 5px solid #16a34a; }
        .help-box.red { background: #fee2e2; border-left: 5px solid #dc2626; }

        .word-detail {
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            margin-bottom: 10px;
            padding: 12px;
            background: #f8fafc;
        }
        .word-detail .word-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
        }
        .word-detail .word-type {
            padding: 2px 8px;
            background: #e2e8f0;
            border-radius: 12px;
            font-size: 0.8em;
        }

        details { margin-top: 8px; }
        details summary {
            cursor: pointer;
            font-weight: bold;
            color: #8b5cf6;
        }
        .conjugation-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin-top: 8px;
        }
        .conjugation-box {
            background: #f1f5f9;
            padding: 8px;
            border-radius: 4px;
        }
        .conjugation-box ul {
            list-style: none;
            padding: 0;
            margin: 5px 0;
        }
        .conjugation-box li {
            display: flex;
            justify-content: space-between;
            padding: 2px 0;
        }

        /* ===== SCORE DISPLAY ===== */
        .score-circle {
            display: inline-block;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            text-align: center;
            line-height: 40px;
            font-weight: bold;
            font-size: 1.1em;
        }
        .score-circle.good { background: #dcfce7; color: #16a34a; }
        .score-circle.medium { background: #fef9c3; color: #d97706; }
        .score-circle.bad { background: #fee2e2; color: #dc2626; }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 900px) {
            .split-container { flex-direction: column; }
            .left-path-view { max-height: none; }
            .conjugation-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 600px) {
            .header { flex-direction: column; text-align: center; }
            .header h1 { font-size: 1.3em; }
            .btn-group { flex-direction: column; }
            .btn-group .btn { width: 100%; text-align: center; }
        }

        /* ===== UTILITY ===== */
        .text-muted { color: #64748b; font-size: 0.85em; }
        .mt-10 { margin-top: 10px; }
        .mt-15 { margin-top: 15px; }
        .mt-20 { margin-top: 20px; }
        .flex-between { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .gap-10 { gap: 10px; }
        .hidden { display: none; }

        /* ===== EMPTY STATE ===== */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            background: #f8fafc;
            border-radius: 12px;
            border: 2px dashed #cbd5e1;
        }
        .empty-state .icon { font-size: 4em; margin-bottom: 15px; }
        .empty-state h2 { color: #1e293b; margin-bottom: 10px; }
        .empty-state p { color: #64748b; max-width: 500px; margin: 0 auto; }

        /* ===== FIXED SIDEBAR SCROLL ===== */
        .left-path-view::-webkit-scrollbar {
            width: 6px;
        }
        .left-path-view::-webkit-scrollbar-track {
            background: #f1f5f9;
            border-radius: 3px;
        }
        .left-path-view::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 3px;
        }
        .left-path-view::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
    </style>
</head>
<body>
<div class="container">

    <!-- ===== HEADER ===== -->
    <header class="header">
        <div>
            <h1>🇪🇬 Ägyptisch lernen</h1>
            <span class="text-muted" style="color: #94a3b8;">Statische Version • Offline-Modus</span>
        </div>
        <div>
            <span class="badge">📚 {{ total_phrases }} Phrasen</span>
            <span class="badge" style="background: #64748b; margin-left: 8px;">📝 {{ total_words }} Wörter</span>
            <span class="badge offline" style="margin-left: 8px;">⚡ Offline</span>
        </div>
    </header>

    <!-- ===== MAIN CONTENT ===== -->
    <div class="split-container">

        <!-- ===== LEFT: PATH VIEW ===== -->
        <div class="left-path-view" id="pathView">
            <h3>🗺️ Lernwege</h3>

            {% if paths_data %}
                {% for item in paths_data %}
                <div class="path-section">
                    <div class="path-title">{{ item.path.name }}</div>
                    <div class="level-node-list">
                        {% for lvl_info in item.levels %}
                            {% if lvl_info.total_count > 0 %}
                            <div class="level-card {% if selected_level_id == lvl_info.level.id %}active{% endif %}"
                                 style="background-color: {{ lvl_info.level.color|default:'#f8fafc' }};"
                                 data-level-id="{{ lvl_info.level.id }}"
                                 onclick="selectLevel({{ lvl_info.level.id }})">
                                <div>
                                    <div class="level-name">{{ lvl_info.level.name }}</div>
                                    <div class="level-count">📊 {{ lvl_info.reviewed_count }}/{{ lvl_info.total_count }} geübt</div>
                                </div>
                                <span class="badge-score {% if lvl_info.median is None %}untrained{% elif lvl_info.median >= 8 %}good{% elif lvl_info.median >= 5 %}medium{% else %}bad{% endif %}">
                                    {% if lvl_info.median is not None %}
                                        {% if lvl_info.median >= 8 %}🟢{% elif lvl_info.median >= 5 %}🟡{% else %}🔴{% endif %}
                                        {{ lvl_info.median|floatformat:1 }}
                                    {% else %}
                                        ⚪ Ungeübt
                                    {% endif %}
                                </span>
                            </div>
                            {% endif %}
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p class="text-muted">Keine Lernwege vorhanden.</p>
            {% endif %}

            <hr style="margin: 20px 0; border-color: #e2e8f0;">
            <div style="font-size: 0.85em; color: #64748b;">
                <p><strong>💡 Bedienung:</strong></p>
                <p>• Klicke auf ein Level, um Phrasen zu üben</p>
                <p>• Ziehe eine Phrase per Drag & Drop auf ein Level, um sie neu zuzuordnen</p>
                <p>• Die Bewertung ist in dieser statischen Version deaktiviert</p>
            </div>
        </div>

        <!-- ===== RIGHT: EXERCISE VIEW ===== -->
        <div class="right-exercise-view" id="exerciseView">

            {% if has_data %}
                <!-- Phrase Card will be rendered by JavaScript -->
                <div id="phraseContainer">
                    <div class="card">
                        <p class="text-muted">Lade Phrasen...</p>
                    </div>
                </div>
            {% else %}
                <div class="empty-state">
                    <div class="icon">📭</div>
                    <h2>Keine Phrasen vorhanden</h2>
                    <p>In dieser statischen Version sind keine Phrasen in der Datenbank vorhanden.<br>
                    Bitte importiere zuerst Daten oder generiere sie mit der Django-Admin-Oberfläche.</p>
                </div>
            {% endif %}

        </div>
    </div>
</div>

<!-- ===== JAVASCRIPT ===== -->
<script>
// ============================================================
// DATA
// ============================================================
const PHRASES_DATA = {{ phrases_json|safe }};
const PHRASE_IDS = Object.keys(PHRASES_DATA).map(Number);

// Sort phrases by level and order (if available)
let allPhrases = PHRASE_IDS.map(id => PHRASES_DATA[id]);
// Sort by level_id, then by id
allPhrases.sort((a, b) => (a.level_id || 0) - (b.level_id || 0) || a.id - b.id);

// ============================================================
// STATE
// ============================================================
let currentLevelId = null;
let currentPhrase = null;
let currentIndex = 0;
let filteredPhrases = [];

// UI state
let showSimpleHelp = false;
let showDetailedHelp = false;
let evaluated = false;
let evaluationResult = null;
let userInput = '';

// ============================================================
// DOM REFS
// ============================================================
const phraseContainer = document.getElementById('phraseContainer');

// ============================================================
// HELPERS
// ============================================================
function shuffleArray(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

function getPhrasesForLevel(levelId) {
    return allPhrases.filter(p => p.level_id === levelId);
}

function getRandomPhrase(levelId) {
    const available = levelId ? getPhrasesForLevel(levelId) : allPhrases;
    if (available.length === 0) return null;
    return available[Math.floor(Math.random() * available.length)];
}

function getMedianScore(phrase) {
    if (phrase && phrase.progress && phrase.progress.median_score !== null) {
        return phrase.progress.median_score;
    }
    return null;
}

function getScoreBadge(score) {
    if (score === null) return { label: '⚪ Ungeübt', cls: 'untrained' };
    if (score >= 8) return { label: `🟢 ${score.toFixed(1)}`, cls: 'good' };
    if (score >= 5) return { label: `🟡 ${score.toFixed(1)}`, cls: 'medium' };
    return { label: `🔴 ${score.toFixed(1)}`, cls: 'bad' };
}

// ============================================================
// RENDER FUNCTIONS
// ============================================================
function renderPhrase(phrase, options = {}) {
    if (!phrase) {
        phraseContainer.innerHTML = `
            <div class="card">
                <p class="text-muted">Keine Phrasen in diesem Level.</p>
                <button class="btn btn-primary" onclick="selectLevel(null)">Alle Phrasen anzeigen</button>
            </div>
        `;
        return;
    }

    currentPhrase = phrase;
    const median = getMedianScore(phrase);
    const badge = getScoreBadge(median);
    const levelName = phrase.level_name || 'Kein Level';

    let helpHtml = '';
    let resultHtml = '';

    // Simple Help
    if (options.showSimpleHelp) {
        helpHtml = `
            <div class="help-box yellow">
                <h3>💡 Hilfe - Übersetzung</h3>
                <div style="display: flex; align-items: center; gap: 10px; margin-top: 10px;">
                    <div style="flex: 1;">
                        <p class="arabic">${escapeHtml(phrase.arabic_script)}</p>
                        <p><strong>Arabizi:</strong> ${escapeHtml(phrase.arabizi)}</p>
                    </div>
                </div>
                <div class="btn-group">
                    <button class="btn btn-success" onclick="renderPhrase(currentPhrase, {})">Zurück zum Üben ➔</button>
                    <button class="btn btn-purple" onclick="renderPhrase(currentPhrase, { showDetailedHelp: true })">Mehr Details 📚</button>
                </div>
            </div>
        `;
    }

    // Detailed Help
    if (options.showDetailedHelp && phrase.words && phrase.words.length > 0) {
        let wordsHtml = '';
        phrase.words.forEach(word => {
            let wordExtraHtml = '';

            // Conjugation info
            if (word.conjugation_info) {
                let detailsHtml = '';
                if (word.word_type === 'verb') {
                    let presentHtml = '', pastHtml = '', imperativeHtml = '';
                    if (word.conjugation_info.present_tense) {
                        presentHtml = `
                            <div class="conjugation-box">
                                <strong style="color: #8b5cf6;">Präsens</strong>
                                <ul>
                                    ${Object.entries(word.conjugation_info.present_tense).map(([person, form]) => 
                                        `<li><span>${person}:</span> <span class="arabic small">${escapeHtml(form)}</span></li>`
                                    ).join('')}
                                </ul>
                            </div>
                        `;
                    }
                    if (word.conjugation_info.past_tense) {
                        pastHtml = `
                            <div class="conjugation-box">
                                <strong style="color: #8b5cf6;">Vergangenheit</strong>
                                <ul>
                                    ${Object.entries(word.conjugation_info.past_tense).map(([person, form]) => 
                                        `<li><span>${person}:</span> <span class="arabic small">${escapeHtml(form)}</span></li>`
                                    ).join('')}
                                </ul>
                            </div>
                        `;
                    }
                    if (word.conjugation_info.imperative) {
                        imperativeHtml = `
                            <div class="conjugation-box">
                                <strong style="color: #8b5cf6;">Imperativ</strong>
                                <ul>
                                    ${Object.entries(word.conjugation_info.imperative).map(([person, form]) => 
                                        `<li><span>${person}:</span> <span class="arabic small">${escapeHtml(form)}</span></li>`
                                    ).join('')}
                                </ul>
                            </div>
                        `;
                    }
                    detailsHtml = `
                        <details>
                            <summary>Konjugation anzeigen 📖</summary>
                            <div class="conjugation-grid">
                                ${presentHtml}
                                ${pastHtml}
                                ${imperativeHtml}
                            </div>
                            ${word.root_letters ? `<div class="text-muted mt-10"><strong>Wurzel:</strong> ${escapeHtml(word.root_letters)}</div>` : ''}
                        </details>
                    `;
                } else if (word.word_type === 'noun' || word.word_type === 'adjective') {
                    let flexHtml = '';
                    if (word.conjugation_info.singular || word.conjugation_info.plural) {
                        flexHtml = `
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px;">
                                ${word.conjugation_info.singular ? `<div class="conjugation-box"><strong>Singular</strong><div class="arabic small">${escapeHtml(word.conjugation_info.singular)}</div></div>` : ''}
                                ${word.conjugation_info.plural ? `<div class="conjugation-box"><strong>Plural</strong><div class="arabic small">${escapeHtml(word.conjugation_info.plural)}</div></div>` : ''}
                                ${word.conjugation_info.masculine ? `<div class="conjugation-box"><strong>Maskulin</strong><div class="arabic small">${escapeHtml(word.conjugation_info.masculine)}</div></div>` : ''}
                                ${word.conjugation_info.feminine ? `<div class="conjugation-box"><strong>Feminin</strong><div class="arabic small">${escapeHtml(word.conjugation_info.feminine)}</div></div>` : ''}
                            </div>
                        `;
                    }
                    detailsHtml = `
                        <details>
                            <summary>Flexion anzeigen 📖</summary>
                            ${flexHtml}
                        </details>
                    `;
                }

                if (word.conjugation_info.notes) {
                    detailsHtml += `<div class="text-muted mt-10">💡 ${escapeHtml(word.conjugation_info.notes)}</div>`;
                }
                wordExtraHtml = detailsHtml;
            }

            wordsHtml += `
                <div class="word-detail">
                    <div class="word-header">
                        <div>
                            <strong style="font-size: 1.1em;">${escapeHtml(word.german_word)}</strong>
                            <span class="word-type">${escapeHtml(word.word_type || 'unbekannt')}</span>
                        </div>
                        <div style="text-align: right;">
                            <div class="arabic small">${escapeHtml(word.arabic_script)}</div>
                            <div class="text-muted">${escapeHtml(word.arabizi)}</div>
                        </div>
                    </div>
                    ${wordExtraHtml}
                </div>
            `;
        });

        helpHtml = `
            <div class="help-box purple">
                <h3>📚 Detaillierte Hilfe - Wort-für-Wort Analyse</h3>
                <div style="display: flex; align-items: center; gap: 10px; margin-top: 10px; padding: 10px; background: #fef9c3; border-radius: 6px;">
                    <div style="flex: 1;">
                        <p class="arabic">${escapeHtml(phrase.arabic_script)}</p>
                        <p><strong>Arabizi:</strong> ${escapeHtml(phrase.arabizi)}</p>
                    </div>
                </div>
                <h4 class="mt-15">Wort-für-Wort Übersetzung:</h4>
                ${wordsHtml}
                <div class="btn-group">
                    <button class="btn btn-success" onclick="renderPhrase(currentPhrase, {})">Zurück zum Üben ➔</button>
                    <button class="btn btn-warning" onclick="renderPhrase(currentPhrase, { showSimpleHelp: true })">Nur Übersetzung 💡</button>
                </div>
            </div>
        `;
    }

    // Evaluation Result (static - just display the correct answer)
    if (options.evaluated) {
        const score = options.score || 0;
        const isGood = score >= 8;
        resultHtml = `
            <div class="help-box ${isGood ? 'green' : 'red'}">
                <div class="flex-between">
                    <h3 style="margin: 0;">Feedback</h3>
                    <span class="score-circle ${isGood ? 'good' : 'bad'}">${score}</span>
                </div>
                ${options.userInput ? `<p><strong>Dein Versuch:</strong> ${escapeHtml(options.userInput)}</p>` : ''}
                <hr>
                <h4>✅ Musterlösung:</h4>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <p class="arabic">${escapeHtml(phrase.arabic_script)}</p>
                </div>
                <p><strong>Arabizi:</strong> ${escapeHtml(phrase.arabizi)}</p>
                <div class="btn-group">
                    <button class="btn btn-success" onclick="nextPhrase()">Nächste Phrase ➔</button>
                </div>
            </div>
        `;
    }

    // Build the full card
    const html = `
        <div class="card draggable-phrase" 
             draggable="true"
             data-phrase-id="${phrase.id}"
             ondragstart="handleDragStart(event)">

            <div style="font-size: 0.8em; color: #64748b; margin-bottom: 8px;">
                ✋ <i>Ziehe diese Karte auf ein Level, um sie neu zuzuordnen</i>
            </div>

            <div class="flex-between">
                <h2>Level: ${escapeHtml(levelName)}</h2>
                <div style="background: #f1f5f9; padding: 6px 14px; border-radius: 20px; font-size: 0.9em; font-weight: bold;">
                    <span class="badge-score ${badge.cls}">${badge.label}</span>
                </div>
            </div>

            <p class="mt-15"><strong>Übersetze ins Ägyptische (Arabisch oder Arabizi):</strong></p>
            <h3>"${escapeHtml(phrase.german_sentence)}"</h3>

            ${!helpHtml && !resultHtml ? `
                <div class="mt-15">
                    <input type="text" id="userInput" 
                           placeholder="z.B. Izayyak oder إزيك" 
                           autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false"
                           onkeydown="if(event.key==='Enter') evaluatePhrase()">
                    <div class="btn-group">
                        <button class="btn btn-primary" onclick="evaluatePhrase()">Prüfen 🔍</button>
                        <button class="btn btn-warning" onclick="renderPhrase(currentPhrase, { showSimpleHelp: true })">Hilfe 💡</button>
                        <button class="btn btn-purple" onclick="renderPhrase(currentPhrase, { showDetailedHelp: true })">Detaillierte Hilfe 📚</button>
                        <button class="btn btn-gray" onclick="nextPhrase()">Überspringen ⏭️</button>
                    </div>
                </div>
            ` : ''}

            ${helpHtml}
            ${resultHtml}
        </div>
    `;

    phraseContainer.innerHTML = html;

    // Focus input if visible
    const input = document.getElementById('userInput');
    if (input) input.focus();
}

// ============================================================
// EVALUATION (Static: no AI, just shows the correct answer)
// ============================================================
function evaluatePhrase() {
    const input = document.getElementById('userInput');
    if (!input || !currentPhrase) return;

    const userText = input.value.trim();
    if (!userText) {
        input.style.borderColor = '#dc2626';
        return;
    }
    input.style.borderColor = '#e2e8f0';

    // Simple check: if input matches arabic_script or arabizi (case insensitive)
    const isCorrect = userText.toLowerCase() === currentPhrase.arabizi.toLowerCase() ||
                      userText === currentPhrase.arabic_script;

    // Generate a mock score (just for display)
    const score = isCorrect ? 10 : Math.floor(Math.random() * 3) + 6; // 6-8 for wrong, 10 for correct

    renderPhrase(currentPhrase, {
        evaluated: true,
        userInput: userText,
        score: score,
    });
}

// ============================================================
// NAVIGATION
// ============================================================
function selectLevel(levelId) {
    currentLevelId = levelId;

    // Update active state in sidebar
    document.querySelectorAll('.level-card').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.levelId) === levelId);
    });

    // Find a phrase for this level
    const phrase = getRandomPhrase(levelId);
    if (phrase) {
        renderPhrase(phrase);
    } else {
        phraseContainer.innerHTML = `
            <div class="card">
                <p class="text-muted">Keine Phrasen in diesem Level.</p>
                <button class="btn btn-primary" onclick="selectLevel(null)">Alle Phrasen anzeigen</button>
            </div>
        `;
    }
}

function nextPhrase() {
    const phrase = getRandomPhrase(currentLevelId);
    if (phrase) {
        renderPhrase(phrase);
    } else {
        selectLevel(null);
    }
}

// ============================================================
// DRAG & DROP (Static - just visual, no server call)
// ============================================================
let draggedPhraseId = null;

function handleDragStart(e) {
    const card = e.currentTarget;
    draggedPhraseId = card.getAttribute('data-phrase-id');
    e.dataTransfer.setData('text/plain', draggedPhraseId);
    e.dataTransfer.effectAllowed = 'move';
    card.classList.add('dragging');
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const target = e.currentTarget.closest('.level-card');
    if (target) target.classList.add('drag-over');
}

function handleDragLeave(e) {
    const target = e.currentTarget.closest('.level-card');
    if (target) target.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    const targetCard = e.currentTarget.closest('.level-card');
    if (targetCard) targetCard.classList.remove('drag-over');

    const targetLevelId = targetCard ? parseInt(targetCard.dataset.levelId) : null;
    const phraseId = parseInt(e.dataTransfer.getData('text/plain'));

    if (!targetLevelId || !phraseId) {
        alert('Bitte ziehe auf ein Level.');
        return;
    }

    // Update in-memory data
    if (PHRASES_DATA[phraseId]) {
        PHRASES_DATA[phraseId].level_id = targetLevelId;
        // Update level name
        const levelCard = targetCard.querySelector('.level-name');
        PHRASES_DATA[phraseId].level_name = levelCard ? levelCard.textContent : 'Level ' + targetLevelId;

        // Update allPhrases
        const idx = allPhrases.findIndex(p => p.id === phraseId);
        if (idx !== -1) {
            allPhrases[idx].level_id = targetLevelId;
            allPhrases[idx].level_name = PHRASES_DATA[phraseId].level_name;
        }

        // Show success message
        alert(`✅ Phrase wurde Level "${PHRASES_DATA[phraseId].level_name}" zugewiesen.`);

        // Re-render current phrase
        if (currentPhrase && currentPhrase.id === phraseId) {
            currentPhrase.level_id = targetLevelId;
            currentPhrase.level_name = PHRASES_DATA[phraseId].level_name;
            renderPhrase(currentPhrase);
        }
    }
}

// Add drag event listeners to level cards
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.level-card').forEach(card => {
        card.addEventListener('dragover', handleDragOver);
        card.addEventListener('dragleave', handleDragLeave);
        card.addEventListener('drop', handleDrop);
    });
});

// ============================================================
// UTILITY
// ============================================================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    // Select first level with phrases or show all
    let firstLevel = null;
    for (const p of allPhrases) {
        if (p.level_id !== null) {
            firstLevel = p.level_id;
            break;
        }
    }

    if (firstLevel !== null) {
        selectLevel(firstLevel);
    } else if (allPhrases.length > 0) {
        renderPhrase(allPhrases[0]);
    } else {
        phraseContainer.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <h2>Keine Phrasen vorhanden</h2>
                <p>In dieser statischen Version sind keine Phrasen in der Datenbank vorhanden.</p>
            </div>
        `;
    }
});

// ============================================================
// GLOBAL EXPOSURE
// ============================================================
window.selectLevel = selectLevel;
window.nextPhrase = nextPhrase;
window.evaluatePhrase = evaluatePhrase;
window.renderPhrase = renderPhrase;
window.handleDragStart = handleDragStart;
window.handleDragOver = handleDragOver;
window.handleDragLeave = handleDragLeave;
window.handleDrop = handleDrop;
window.PHRASES_DATA = PHRASES_DATA;
window.currentPhrase = currentPhrase;

console.log('🇪🇬 Static Learning Site loaded!');
console.log(`📚 ${allPhrases.length} phrases loaded.`);
</script>

</body>
</html>
"""
