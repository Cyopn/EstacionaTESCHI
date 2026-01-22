
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
        self.client.get("/api/availability/", name="/api/availability/")


class PlateLookupUser(HttpUser):
    wait_time = between(1, 3)

    @task
    @tag("lookup")
    def lookup_plate(self):
        plate = random.choice(PLATES)
        self.client.get(
            "/plates/lookup/",
            params={"placa": plate},
            name="/plates/lookup/",
        )


class PlateLogAccessUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.plate = DEFAULT_PLATE

    @task
    @tag("log_access")
    def log_access(self):
        payload = {"placa": self.plate, "tipo": "ENTRADA"}
        self.client.post(
            "/plates/log_access/",
            json=payload,
            name="/plates/log_access/",
        )
