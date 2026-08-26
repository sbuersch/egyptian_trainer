
from django.contrib import admin
from django.urls import path, include

from learning.views import generate_100_phrases_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("learning.urls")),
    path(
        "generate-100/",
        generate_100_phrases_view,
        name="generate_100_phrases",
    ),
]
