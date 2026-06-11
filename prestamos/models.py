from django.db import models
from django.conf import settings
from herramientas.models import Herramienta


class Prestamo(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        DEVUELTO = "devuelto", "Devuelto"
        VENCIDO = "vencido", "Vencido"

    herramientas = models.ManyToManyField(Herramienta, related_name="prestamos")
    solicitantes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="prestamos_solicitados",
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="prestamos_autorizados"
    )
    descripcion_uso = models.TextField(verbose_name="¿Para qué se va a usar?", blank=True, default="")
    lugar_uso = models.CharField(max_length=200, verbose_name="Lugar de uso", blank=True, default="")
    fecha_prestamo = models.DateTimeField(auto_now_add=True)
    fecha_devolucion_esperada = models.DateField()
    fecha_devolucion_real = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "préstamos"
        ordering = ["-fecha_prestamo"]

    def __str__(self):
        herrs = ", ".join(h.nombre for h in self.herramientas.all()[:3])
        return f"Préstamo #{self.pk} - {herrs}"
