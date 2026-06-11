from rest_framework import serializers
from .models import Prestamo


class PrestamoSerializer(serializers.ModelSerializer):
    herramientas_nombres = serializers.SerializerMethodField(read_only=True)
    solicitantes_nombres = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Prestamo
        fields = (
            "id", "herramientas", "herramientas_nombres",
            "solicitantes", "solicitantes_nombres", "responsable",
            "descripcion_uso", "lugar_uso",
            "fecha_prestamo", "fecha_devolucion_esperada",
            "fecha_devolucion_real", "estado", "observaciones",
        )
        read_only_fields = ("fecha_prestamo", "estado")

    def get_herramientas_nombres(self, obj):
        return [str(h) for h in obj.herramientas.all()]

    def get_solicitantes_nombres(self, obj):
        return [s.get_full_name() or s.username for s in obj.solicitantes.all()]
