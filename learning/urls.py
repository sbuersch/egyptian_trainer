from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("modus1/", views.mode1_view, name="mode1"),
    path("modus2/", views.mode2_view, name="mode2"),
    path("modus3/", views.mode3_view, name="mode3"),

    path("api/tts/", views.tts_audio_view, name="tts_audio"),
]