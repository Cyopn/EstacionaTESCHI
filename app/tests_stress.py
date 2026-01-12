"""
Escenarios de carga/estrés sobre endpoints publicos.

Ejecutar con:
    locust -f app/tests_stress.py --host http://localhost:8000

Endpoints cubiertos:
- /api/availability/
- /plates/lookup/
- /plates/log_access/

Nota: para evitar errores 404 en log_access, definir STRESS_PLATE con una placa existente
(en la BD) o ajustar el arreglo PLATES.
"""
import os
import random
from locust import HttpUser, task, between, tag

PLATES = [
    "PEL5217",
    "LZF118C",
    "MWG631C",
]
DEFAULT_PLATE = os.environ.get("STRESS_PLATE", "PEL5217")


class AvailabilityUser(HttpUser):
    wait_time = between(1, 3)

    @task
    @tag("availability")
    def list_availability(self):
        # GET masivo al listado de disponibilidad
        self.client.get("/api/availability/", name="/api/availability/")


class PlateLookupUser(HttpUser):
    wait_time = between(1, 3)

    @task
    @tag("lookup")
    def lookup_plate(self):
        # GET de lookup de placa con pool fijo
        plate = random.choice(PLATES)
        self.client.get(
            "/plates/lookup/",
            params={"placa": plate},
            name="/plates/lookup/",
        )


class PlateLogAccessUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Usa una placa fija para evitar 404 si no existe en BD
        self.plate = DEFAULT_PLATE

    @task
    @tag("log_access")
    def log_access(self):
        # POST que registra acceso y genera notificacion
        payload = {"placa": self.plate, "tipo": "ENTRADA"}
        self.client.post(
            "/plates/log_access/",
            json=payload,
            name="/plates/log_access/",
        )
