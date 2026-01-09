from django.db import models
from django.contrib.auth.hashers import make_password, identify_hasher

# Create your models here.


class Area(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    capacidad_total = models.PositiveIntegerField(
        verbose_name="Capacidad total")
    capacidad_disponible = models.PositiveIntegerField(
        verbose_name="Capacidad disponible", default=0)

    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación")
    fecha_modificacion = models.DateTimeField(
        auto_now=True, verbose_name="Fecha de modificación")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"


class Empleado(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellidos = models.CharField(max_length=150, verbose_name="Apellidos")
    correo = models.EmailField(unique=True, verbose_name="Correo")
    contraseña = models.CharField(max_length=128, verbose_name="Contraseña")
    telefono = models.CharField(
        max_length=30, blank=True, null=True, verbose_name="Teléfono")
    numero_empleado = models.PositiveIntegerField(
        unique=True, verbose_name="Número de empleado")

    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación")
    fecha_modificacion = models.DateTimeField(
        auto_now=True, verbose_name="Fecha de modificación")

    class Rol(models.TextChoices):
        JEFE_AREA = 'JEFE_AREA', 'Jefe de área'
        GUARDIA = 'GUARDIA', 'Guardia'
        PATRULLA = 'PATRULLA', 'Patrulla'

    class Puesto(models.TextChoices):
        EDIFICIO = 'EDIFICIO', 'Edificio'
        ENTRADA_PEATONAL = 'ENTRADA_PEATONAL', 'Entrada peatonal'
        ENTRADA_VEHICULAR = 'ENTRADA_VEHICULAR', 'Entrada vehicular'
        CAFETERIA = 'CAFETERIA', 'Cafetería'
        ESTACIONAMIENTO = 'ESTACIONAMIENTO', 'Estacionamiento'

    rol = models.CharField(max_length=20, choices=Rol.choices,
                           default=Rol.GUARDIA, verbose_name="Rol")
    puesto = models.CharField(
        max_length=30, choices=Puesto.choices, verbose_name="Puesto")

    def __str__(self):
        return f"{self.nombre} {self.apellidos} ({self.numero_empleado})"

    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"


class Usuario(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellidos = models.CharField(max_length=150, verbose_name="Apellidos")
    matricula = models.CharField(
        max_length=50, unique=True, verbose_name="Matrícula")
    correo = models.EmailField(unique=True, verbose_name="Correo")
    telefono = models.CharField(
        max_length=30, blank=True, null=True, verbose_name="Teléfono")
    contraseña = models.CharField(max_length=128, verbose_name="Contraseña")

    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación")
    fecha_modificacion = models.DateTimeField(
        auto_now=True, verbose_name="Fecha de modificación")

    def __str__(self):
        return f"{self.nombre} {self.apellidos} ({self.matricula})"

    def save(self, *args, **kwargs):
        # Hashear la contraseña si no está ya hasheada
        if self.contraseña:
            try:
                identify_hasher(self.contraseña)
            except (ValueError, TypeError):
                self.contraseña = make_password(self.contraseña)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"


class Vehiculo(models.Model):
    placa = models.CharField(max_length=20, unique=True, verbose_name="Placa")
    marca = models.CharField(max_length=50, verbose_name="Marca")
    modelo = models.CharField(max_length=50, verbose_name="Modelo")
    color = models.CharField(max_length=30, verbose_name="Color")

    class TipoVehiculo(models.TextChoices):
        AUTOMOVIL = 'AUTOMOVIL', 'Automóvil'
        MOTOCICLETA = 'MOTOCICLETA', 'Motocicleta'
        OTRO = 'OTRO', 'Otro'

    tipo_vehiculo = models.CharField(max_length=20, choices=TipoVehiculo.choices,
                                     default=TipoVehiculo.AUTOMOVIL, verbose_name="Tipo de vehículo")

    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación")
    fecha_modificacion = models.DateTimeField(
        auto_now=True, verbose_name="Fecha de modificación")

    def __str__(self):
        return f"{self.placa} - {self.marca} {self.modelo}"

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"
    usuario = models.ForeignKey(
        'Usuario',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='vehiculos',
        verbose_name='Usuario'
    )


class Sancion(models.Model):
    motivo = models.TextField(verbose_name="Motivo")
    fecha = models.DateField(verbose_name="Fecha")

    class Gravedad(models.TextChoices):
        MODERADA = 'MODERADA', 'Moderada'
        GRAVE = 'GRAVE', 'Grave'
        CRITICA = 'CRITICA', 'Crítica'

    gravedad = models.CharField(max_length=10, choices=Gravedad.choices,
                                default=Gravedad.MODERADA, verbose_name="Gravedad")

    vehiculo = models.ForeignKey(
        'Vehiculo',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sanciones',
        verbose_name='Vehículo'
    )

    usuario = models.ForeignKey(
        'Usuario',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sanciones',
        verbose_name='Usuario'
    )

    area = models.ForeignKey(
        'Area',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sanciones',
        verbose_name='Área'
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación")
    fecha_modificacion = models.DateTimeField(
        auto_now=True, verbose_name="Fecha de modificación")

    def __str__(self):
        return f"Sanción {self.id} - {self.get_gravedad_display()} ({self.fecha})"

    class Meta:
        verbose_name = "Sanción"
        verbose_name_plural = "Sanciones"
