from django.db import models

# Create your models here.


class Area(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    capacidad_total = models.PositiveIntegerField(
        verbose_name="Capacidad total")
    capacidad_disponible = models.PositiveIntegerField(
        verbose_name="Capacidad disponible", default=0)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
