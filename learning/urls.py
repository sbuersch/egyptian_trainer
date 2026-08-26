from django.urls import path
from . import views
from .map_views import path_trainer_view, update_phrase_level_view, phrase_assignment_board_view, \
    update_phrase_level_ajax

urlpatterns = [
    # path("", views.index, name="index"),
    path("modus1/", views.mode1_view, name="mode1"),
    path("modus2/", views.mode2_view, name="mode2"),
    path("modus3/", views.mode3_view, name="mode3"),

    path("", path_trainer_view, name="path_trainer"),

    path(
        "api/update-phrase-level/",
        update_phrase_level_view,
        name="update_phrase_level",
    ),
    path("board/", phrase_assignment_board_view, name="phrase_board"),
    path(
        "api/update-phrase-level-ajax/",
        update_phrase_level_ajax,
        name="update_phrase_level_ajax",
    ),

    path("api/tts/", views.tts_audio_view, name="tts_audio"),
]