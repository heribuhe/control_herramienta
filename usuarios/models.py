from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = "admin", "Administrador"
        TECNICO = "tecnico", "Técnico"
        ALMACENISTA = "almacenista", "Almacenista"

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.TECNICO)
    telefono = models.CharField(max_length=15, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        nombre = self.get_full_name() or self.username
        return f"{nombre} ({self.get_rol_display()})"
