from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Categoria, Herramienta


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Herramienta)
class HerramientaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "estado", "ubicacion", "ver_codigo_barras")
    list_filter = ("estado", "categoria")
    search_fields = ("codigo", "nombre")
    readonly_fields = ("ver_codigo_barras_detalle",)

    def ver_codigo_barras(self, obj):
        url = f"/api/herramientas/{obj.pk}/barcode/"
        return format_html(
            '<a href="{}" target="_blank" style="'
            'background:#417690;color:white;padding:3px 10px;'
            'border-radius:4px;text-decoration:none;font-size:12px;">'
            '🔳 Código de barras</a>',
            url
        )
    ver_codigo_barras.short_description = "Código de barras"

    def ver_codigo_barras_detalle(self, obj):
        if not obj.pk:
            return "Guarda el artículo primero para generar el código de barras."
        url = f"/api/herramientas/{obj.pk}/barcode/"
        return format_html(
            '<a href="{}" target="_blank" style="'
            'background:#417690;color:white;padding:6px 16px;'
            'border-radius:4px;text-decoration:none;font-size:13px;">'
            '🔳 Ver / Imprimir código de barras</a>',
            url
        )
    ver_codigo_barras_detalle.short_description = "Código de barras"

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if "ver_codigo_barras_detalle" not in fields:
            fields = list(fields) + ["ver_codigo_barras_detalle"]
        return fields
