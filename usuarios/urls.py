from django.urls import path
from . import views

urlpatterns = [
    path("", views.UsuarioListView.as_view(), name="usuario-list"),
]
