from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Herramienta(models.Model):
    class Estado(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        PRESTADA = "prestada", "Prestada"
        MANTENIMIENTO = "mantenimiento", "En mantenimiento"
        BAJA = "baja", "Dada de baja"

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="herramientas")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.DISPONIBLE)
    ubicacion = models.CharField(max_length=100, blank=True)
    imagen = models.ImageField(upload_to="herramientas/", blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "herramientas"
        ordering = ["nombre"]

    def __str__(self):
        return f"[{self.codigo}] {self.nombre}"
