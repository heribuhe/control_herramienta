import io

import barcode
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action

from .models import Categoria, Herramienta
from .serializers import CategoriaSerializer, HerramientaSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class HerramientaViewSet(viewsets.ModelViewSet):
    queryset = Herramienta.objects.select_related("categoria").all()
    serializer_class = HerramientaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    @action(detail=True, methods=["get"])
    def barcode(self, request, pk=None):
        herramienta = self.get_object()

        # --- Código de barras Code128 con el ID de la herramienta ---
        Code128 = barcode.get_barcode_class("code128")
        bc = Code128(str(herramienta.id), writer=ImageWriter())
        bc_buffer = io.BytesIO()
        bc.write(bc_buffer, options={"write_text": False})
        bc_buffer.seek(0)

        # --- PDF ---
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        ancho, alto = A4

        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(ancho / 2, alto - 2 * cm, "Ficha de Artículo")

        c.setLineWidth(0.5)
        c.line(2 * cm, alto - 2.4 * cm, ancho - 2 * cm, alto - 2.4 * cm)

        # Datos del artículo
        c.setFont("Helvetica", 10)
        datos = [
            ("Código", herramienta.codigo),
            ("Nombre", herramienta.nombre),
            ("Categoría", herramienta.categoria.nombre),
            ("Estado", herramienta.get_estado_display()),
            ("Ubicación", herramienta.ubicacion or "—"),
        ]
        if herramienta.descripcion:
            datos.append(("Descripción", herramienta.descripcion))

        y = alto - 3.2 * cm
        for etiqueta, valor in datos:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2 * cm, y, f"{etiqueta}:")
            c.setFont("Helvetica", 10)
            c.drawString(5.5 * cm, y, str(valor))
            y -= 0.7 * cm

        # Código de barras centrado
        img = ImageReader(bc_buffer)
        img_ancho = 10 * cm
        img_alto = 3.5 * cm
        x_img = (ancho - img_ancho) / 2
        y_img = y - img_alto - 0.8 * cm
        c.drawImage(img, x_img, y_img, width=img_ancho, height=img_alto)

        c.save()
        pdf_buffer.seek(0)

        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="articulo_{herramienta.codigo}.pdf"'
        return response

