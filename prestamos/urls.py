from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrestamoViewSet

router = DefaultRouter()
router.register("", PrestamoViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
