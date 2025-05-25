from django.urls import path
from . import views

urlpatterns = [
    path("", views.url_check_view, name="url_check"),
    path("results/", views.results_view, name="results"),
    path("register/", views.register_view, name="register"),
    path("my-scans/", views.my_scans_view, name="my_scans"),
]
