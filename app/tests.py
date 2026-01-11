from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from app.models import (
    Area,
    Espacio,
    Usuario,
    Vehiculo,
    Acceso,
    Notificacion,
)
from app.services import availability


class AvailabilityUnitTests(TestCase):
    """Pruebas unitarias sobre heurística de disponibilidad y búsqueda de áreas."""

    def setUp(self):
        self.area_norte = Area.objects.create(nombre="Estacionamiento Norte")
        self.area_sur = Area.objects.create(nombre="Zona Sur")

    def test_find_area_by_name_fragment_matches_partial(self):
        """Debe localizar el área aunque el texto contenga ruido alrededor del nombre."""
        match = availability.find_area_by_name_fragment(
            "hay lugares en estacionamiento norte?")
        self.assertIsNotNone(match)
        self.assertEqual(match.id, self.area_norte.id)

    def test_get_area_status_counts_libres_and_ocupados(self):
        """Cuenta libres/ocupados usando anotaciones ORM en un solo área."""
        Espacio.objects.create(
            clave="A1",
            estado=Espacio.Estado.LIBRE,
            area=self.area_norte,
        )
        Espacio.objects.create(
            clave="A2",
            estado=Espacio.Estado.OCUPADO,
            area=self.area_norte,
        )

        data = availability.get_area_status(area_id=self.area_norte.id)
        self.assertEqual(len(data), 1)
        info = data[0]
        self.assertEqual(info["libres"], 1)
        self.assertEqual(info["ocupados"], 1)
        self.assertEqual(info["total"], 2)

    def test_predict_area_status_applies_decay(self):
        """Aplica decaimiento temporal a la probabilidad base calculada."""
        for idx in range(4):
            Espacio.objects.create(
                clave=f"B{idx}",
                estado=Espacio.Estado.LIBRE if idx < 3 else Espacio.Estado.OCUPADO,
                area=self.area_sur,
            )

        target = timezone.now() + timedelta(hours=1)
        prediction = availability.predict_area_status(
            self.area_sur.id, target_dt=target)

        # Con 3 de 4 libres, prob base 0.75; con decaimiento a 1h, ~0.65
        self.assertAlmostEqual(
            prediction["probabilidad_disponible"], 0.65, places=2)
        self.assertEqual(prediction["total"], 4)
        self.assertEqual(prediction["esperados_libres"], 3)


class ApiIntegrationTests(TestCase):
    """Pruebas de integración sobre endpoints públicos esenciales."""

    def setUp(self):
        self.client = Client()
        self.area = Area.objects.create(nombre="Central")
        self.space = Espacio.objects.create(
            clave="C1", estado=Espacio.Estado.LIBRE, area=self.area
        )
        self.user = Usuario.objects.create(
            nombre="Ana",
            apellidos="Lopez",
            matricula="T001",
            correo="ana@example.com",
            telefono="",
            contraseña="secret123",
            area=self.area,
        )
        self.vehicle = Vehiculo.objects.create(
            placa="ABC123",
            marca="Nissan",
            modelo="Sentra",
            color="Rojo",
            usuario=self.user,
        )

    def test_availability_list_endpoint_returns_area(self):
        """El listado de disponibilidad debe incluir el área creada en setUp."""
        url = reverse("availability_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(item["area"] == "Central" for item in payload))

    def test_plate_lookup_returns_vehicle_and_space(self):
        """El lookup de placas devuelve datos del vehículo y su cajón sugerido."""
        url = reverse("plates_lookup")
        response = self.client.get(url, {"placa": "ABC123"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["placa"], "ABC123")
        self.assertIsNotNone(data["espacio"])
        self.assertEqual(data["espacio"]["id"], self.space.id)

    def test_plate_log_access_creates_access_and_notification(self):
        """Registrar un acceso debe crear Acceso y Notificacion asociada al usuario."""
        url = reverse("plates_log_access")
        response = self.client.post(
            url,
            {"placa": "ABC123", "tipo": "ENTRADA"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Acceso.objects.count(), 1)
        self.assertEqual(Notificacion.objects.count(), 1)

        notif = Notificacion.objects.first()
        self.assertEqual(notif.usuario_id, self.user.id)
        self.assertIn("Acceso autorizado", notif.cuerpo)
