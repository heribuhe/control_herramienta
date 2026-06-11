from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaViewSet, HerramientaViewSet

router = DefaultRouter()
router.register("categorias", CategoriaViewSet)
router.register("", HerramientaViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
