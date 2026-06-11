from rest_framework import serializers
from .models import Categoria, Herramienta


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ("id", "nombre")


class HerramientaSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = Herramienta
        fields = ("id", "codigo", "nombre", "descripcion", "categoria", "categoria_nombre",
                  "estado", "ubicacion", "imagen", "fecha_registro")
        read_only_fields = ("fecha_registro",)
