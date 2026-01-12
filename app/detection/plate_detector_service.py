from app.models import Dispositivo
import django
import os
import sys
import time
import threading
from typing import Optional

import cv2
import numpy as np
import pytesseract

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

django.setup()


try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    print("ADVERTENCIA: ultralytics no instalado. Instalar con: pip install ultralytics")


class PlateDetector:
    VEHICLE_CLASSES = {2, 3, 5, 7}

    def __init__(
        self,
        identifier: str,
        source: str,
        vehicle_model_path: str = 'models/yolov10n.pt',
        plate_model_path: str = 'models/placa.pt',
        conf_vehicle: float = 0.35,
        conf_plate: float = 0.4,
    ) -> None:
        self.identifier = str(identifier)
        self.source = source
        self.vehicle_model_path = vehicle_model_path
        self.plate_model_path = plate_model_path
        self.conf_vehicle = conf_vehicle
        self.conf_plate = conf_plate

        self.running = False
        self.frame = None
        self.frame_lock = threading.Lock()

        self.vehicle_model = None
        self.plate_model = None
        self.cap = None
        self.thread = None

        self.last_plate_text: Optional[str] = None
        self.last_plate_at: Optional[float] = None

        tesseract_cmd = os.getenv('TESSERACT_CMD')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def _load_models(self) -> None:
        if YOLO is None:
            raise RuntimeError("ultralytics no está instalado")

        project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

        vehicle_path = os.path.join(project_root, self.vehicle_model_path)
        plate_path = os.path.join(project_root, self.plate_model_path)

        self.vehicle_model = YOLO(vehicle_path if os.path.exists(
            vehicle_path) else self.vehicle_model_path)
        self.plate_model = YOLO(plate_path if os.path.exists(
            plate_path) else self.plate_model_path)

        print(
            f"Modelos cargados: vehiculos={self.vehicle_model_path}, placas={self.plate_model_path}")

    def _safe_crop(self, image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return np.zeros((0, 0, 3), dtype=image.dtype)
        return image[y1:y2, x1:x2]

    def _extract_plate_text(self, plate_img: np.ndarray) -> Optional[str]:
        if plate_img.size == 0:
            return None

        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        text = pytesseract.image_to_string(
            thresh,
            lang='eng',
            config='--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        )

        cleaned = ''.join(ch for ch in text if ch.isalnum()).upper()
        return cleaned or None

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        annotated = frame.copy()

        results_vehicle = self.vehicle_model(
            annotated, conf=self.conf_vehicle, verbose=False)[0]
        if results_vehicle.boxes is None or len(results_vehicle.boxes) == 0:
            return annotated

        for box in results_vehicle.boxes:
            cls_id = int(box.cls[0])
            if cls_id not in self.VEHICLE_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 255), 2)

            vehicle_crop = self._safe_crop(frame, x1, y1, x2, y2)
            if vehicle_crop.size == 0:
                continue

            results_plate = self.plate_model(
                vehicle_crop, conf=self.conf_plate, agnostic_nms=True, verbose=False
            )[0]
            if results_plate.boxes is None or len(results_plate.boxes) == 0:
                continue

            best_idx = int(np.argmax(results_plate.boxes.conf.cpu().numpy()))
            plate_box = results_plate.boxes[best_idx]
            px1, py1, px2, py2 = map(int, plate_box.xyxy[0])

            gx1, gy1 = x1 + px1, y1 + py1
            gx2, gy2 = x1 + px2, y1 + py2

            cv2.rectangle(annotated, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)

            plate_crop = self._safe_crop(frame, gx1, gy1, gx2, gy2)
            text = self._extract_plate_text(plate_crop)
            if text:
                self.last_plate_text = text
                self.last_plate_at = time.time()
                cv2.putText(
                    annotated,
                    text,
                    (gx1, max(gy1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (255, 255, 255),
                    2,
                )

            break

        return annotated

    def _capture_loop(self) -> None:
        print(
            f"Iniciando captura de {self.source} para detector {self.identifier}")
        self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            print(f"Error: No se pudo abrir la fuente {self.source}")
            self.running = False
            return

        frame_count = 0
        process_every = 2

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("Conexión de cámara perdida, reintentando en 2s...")
                time.sleep(2)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.source)
                continue

            frame_count += 1
            if frame_count % process_every != 0:
                continue

            processed = self._process_frame(frame)
            with self.frame_lock:
                self.frame = processed

        self.cap.release()
        print(f"Captura detenida para detector {self.identifier}")

    def start(self) -> None:
        if self.running:
            return

        self._load_models()
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print(f"Detector de placas iniciado para detector {self.identifier}")

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print(f"Detector de placas detenido para detector {self.identifier}")

    def get_frame_jpeg(self) -> bytes:
        with self.frame_lock:
            if self.frame is None:
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "Iniciando detector...", (120, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                _, jpeg = cv2.imencode('.jpg', placeholder)
                return jpeg.tobytes()

            _, jpeg = cv2.imencode('.jpg', self.frame, [
                                   cv2.IMWRITE_JPEG_QUALITY, 80])
            return jpeg.tobytes()

    def status(self) -> dict:
        return {
            'identifier': self.identifier,
            'running': self.running,
            'last_plate': self.last_plate_text,
            'last_plate_at': self.last_plate_at,
            'stream_url': None,
        }


_plate_detectors = {}
_plate_lock = threading.Lock()


def get_plate_detector(identifier: str) -> Optional[PlateDetector]:
    with _plate_lock:
        return _plate_detectors.get(str(identifier))


def start_plate_detector(device_id: int) -> PlateDetector:
    with _plate_lock:
        identifier = str(device_id)
        if identifier in _plate_detectors:
            _plate_detectors[identifier].stop()

        try:
            device = Dispositivo.objects.get(pk=device_id)
        except Dispositivo.DoesNotExist:
            raise ValueError(f"Dispositivo {device_id} no encontrado")

        detector = PlateDetector(identifier, device.ruta)
        detector.start()
        _plate_detectors[identifier] = detector
        return detector


def start_plate_detector_by_source(source: str) -> PlateDetector:
    with _plate_lock:
        identifier = source
        if identifier in _plate_detectors:
            _plate_detectors[identifier].stop()

        detector = PlateDetector(identifier, source)
        detector.start()
        _plate_detectors[identifier] = detector
        return detector


def stop_plate_detector(identifier: str) -> None:
    with _plate_lock:
        key = str(identifier)
        if key in _plate_detectors:
            _plate_detectors[key].stop()
            del _plate_detectors[key]


def stop_all_plate_detectors() -> None:
    with _plate_lock:
        for det in _plate_detectors.values():
            det.stop()
        _plate_detectors.clear()
