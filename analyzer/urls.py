from django.urls import path
from . import views

urlpatterns = [
    path("", views.url_check_view, name="url_check"),
    path("results/", views.results_view, name="results"),
    path("register/", views.register_view, name="register"),
]
