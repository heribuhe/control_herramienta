import io
import barcode
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from herramientas.models import Herramienta
from .models import Prestamo
from .serializers import PrestamoSerializer


def _buscar_herramienta_por_valor(valor):
    """Busca una herramienta por su código."""
    return Herramienta.objects.filter(codigo=valor).first()


class PrestamoViewSet(viewsets.ModelViewSet):
    queryset = Prestamo.objects.select_related("herramienta", "solicitante", "responsable").all()
    serializer_class = PrestamoSerializer

    def destroy(self, request, *args, **kwargs):
        prestamo = self.get_object()
        if prestamo.estado == Prestamo.Estado.ACTIVO:
            return Response(
                {"detail": "No se puede eliminar un préstamo activo. Primero debe registrarse la devolución de la herramienta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        prestamo = serializer.save()
        prestamo.herramientas.all().update(estado=Herramienta.Estado.PRESTADA)

    @action(detail=True, methods=["post"])
    def devolver(self, request, pk=None):
        prestamo = self.get_object()
        if prestamo.estado != Prestamo.Estado.ACTIVO:
            return Response({"detail": "Este préstamo ya fue cerrado."}, status=status.HTTP_400_BAD_REQUEST)

        prestamo.estado = Prestamo.Estado.DEVUELTO
        prestamo.fecha_devolucion_real = timezone.now()
        prestamo.save(update_fields=["estado", "fecha_devolucion_real"])

        prestamo.herramientas.all().update(estado=Herramienta.Estado.DISPONIBLE)

        return Response(PrestamoSerializer(prestamo).data)

    @action(detail=False, methods=["get", "post"], url_path="devolver_por_codigo")
    def devolver_por_codigo(self, request):
        """
        GET  ?codigo=XXX  → Busca el préstamo activo que contiene esa herramienta.
        POST {"codigo": "XXX"} → Marca el préstamo activo como devuelto.
        """
        codigo = request.query_params.get("codigo") if request.method == "GET" else request.data.get("codigo")

        if not codigo:
            return Response({"detail": "Se requiere el campo 'codigo'."}, status=status.HTTP_400_BAD_REQUEST)

        herramienta = _buscar_herramienta_por_valor(codigo)
        if herramienta is None:
            return Response(
                {"detail": "No se encontró ninguna herramienta con ese código."},
                status=status.HTTP_404_NOT_FOUND,
            )

        prestamo = (
            Prestamo.objects
            .filter(herramientas=herramienta, estado=Prestamo.Estado.ACTIVO)
            .first()
        )

        if prestamo is None:
            return Response(
                {"detail": f"La herramienta '{herramienta.nombre}' no tiene un préstamo activo."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == "GET":
            return Response(PrestamoSerializer(prestamo).data)

        # POST: ejecutar devolución
        prestamo.estado = Prestamo.Estado.DEVUELTO
        prestamo.fecha_devolucion_real = timezone.now()
        prestamo.save(update_fields=["estado", "fecha_devolucion_real"])
        prestamo.herramientas.all().update(estado=Herramienta.Estado.DISPONIBLE)

        return Response(PrestamoSerializer(prestamo).data)

    @action(detail=True, methods=["get"])
    def barcode(self, request, pk=None):
        prestamo = self.get_object()

        # --- Generar imagen del código de barras (Code128) ---
        codigo = f"PREST-{prestamo.pk:06d}"
        Code128 = barcode.get_barcode_class("code128")
        bc = Code128(codigo, writer=ImageWriter())
        bc_buffer = io.BytesIO()
        bc.write(bc_buffer, options={"write_text": True, "font_size": 10, "text_distance": 3})
        bc_buffer.seek(0)

        # --- Generar PDF ---
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        ancho, alto = A4

        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(ancho / 2, alto - 2 * cm, "Comprobante de Préstamo")

        # Línea separadora
        c.setLineWidth(0.5)
        c.line(2 * cm, alto - 2.4 * cm, ancho - 2 * cm, alto - 2.4 * cm)

        # Datos del préstamo
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2 * cm, alto - 3.2 * cm, f"Folio: #{prestamo.pk}")

        c.setFont("Helvetica", 10)
        datos = [
            ("Herramienta", prestamo.herramienta.nombre),
            ("Solicitante", prestamo.solicitante.get_full_name() or prestamo.solicitante.username),
            ("Responsable", prestamo.responsable.get_full_name() or prestamo.responsable.username),
            ("Fecha de préstamo", prestamo.fecha_prestamo.strftime("%d/%m/%Y %H:%M")),
            ("Devolución esperada", prestamo.fecha_devolucion_esperada.strftime("%d/%m/%Y")),
            ("Estado", prestamo.get_estado_display()),
        ]
        if prestamo.observaciones:
            datos.append(("Observaciones", prestamo.observaciones))

        y = alto - 4 * cm
        for etiqueta, valor in datos:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2 * cm, y, f"{etiqueta}:")
            c.setFont("Helvetica", 10)
            c.drawString(6.5 * cm, y, str(valor))
            y -= 0.7 * cm

        # Código de barras centrado
        img = ImageReader(bc_buffer)
        img_ancho = 10 * cm
        img_alto = 3.5 * cm
        x_img = (ancho - img_ancho) / 2
        y_img = y - img_alto - 0.8 * cm
        c.drawImage(img, x_img, y_img, width=img_ancho, height=img_alto)

        # Código en texto debajo de la imagen
        c.setFont("Helvetica", 8)
        c.drawCentredString(ancho / 2, y_img - 0.4 * cm, codigo)

        c.save()
        pdf_buffer.seek(0)

        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="prestamo_{prestamo.pk}.pdf"'
        return response

    def _build_barcode_pdf(self, prestamo):
        """Genera el PDF del comprobante de préstamo."""
        codigo = f"PREST-{prestamo.pk:06d}"
        Code128 = barcode.get_barcode_class("code128")
        bc = Code128(codigo, writer=ImageWriter())
        bc_buffer = io.BytesIO()
        bc.write(bc_buffer, options={"write_text": True, "font_size": 10, "text_distance": 3})
        bc_buffer.seek(0)

        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        ancho, alto = A4

        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(ancho / 2, alto - 2 * cm, "Comprobante de Préstamo")
        c.setLineWidth(0.5)
        c.line(2 * cm, alto - 2.4 * cm, ancho - 2 * cm, alto - 2.4 * cm)

        c.setFont("Helvetica-Bold", 11)
        c.drawString(2 * cm, alto - 3.2 * cm, f"Folio: #{prestamo.pk}")

        herramientas = "\n".join(f"• {h}" for h in prestamo.herramientas.all())
        solicitantes = ", ".join(
            s.get_full_name() or s.username for s in prestamo.solicitantes.all()
        )

        c.setFont("Helvetica", 10)
        datos = [
            ("Herramientas", herramientas),
            ("Solicitantes", solicitantes),
            ("Responsable", prestamo.responsable.get_full_name() or prestamo.responsable.username),
            ("Descripción de uso", prestamo.descripcion_uso),
            ("Lugar de uso", prestamo.lugar_uso),
            ("Fecha de préstamo", prestamo.fecha_prestamo.strftime("%d/%m/%Y %H:%M")),
            ("Devolución esperada", prestamo.fecha_devolucion_esperada.strftime("%d/%m/%Y")),
            ("Estado", prestamo.get_estado_display()),
        ]
        if prestamo.observaciones:
            datos.append(("Observaciones", prestamo.observaciones))

        y = alto - 4 * cm
        for etiqueta, valor in datos:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2 * cm, y, f"{etiqueta}:")
            c.setFont("Helvetica", 10)
            # Manejo de texto largo con saltos de línea
            for linea in str(valor).splitlines():
                c.drawString(6.5 * cm, y, linea)
                y -= 0.55 * cm
            y -= 0.15 * cm

        img = ImageReader(bc_buffer)
        img_ancho = 10 * cm
        img_alto = 3.5 * cm
        x_img = (ancho - img_ancho) / 2
        y_img = y - img_alto - 0.8 * cm
        c.drawImage(img, x_img, y_img, width=img_ancho, height=img_alto)
        c.setFont("Helvetica", 8)
        c.drawCentredString(ancho / 2, y_img - 0.4 * cm, codigo)

        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer

