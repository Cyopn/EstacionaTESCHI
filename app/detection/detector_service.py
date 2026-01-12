from app.models import Area, Espacio, Dispositivo
import django
import os
import sys
import threading
import time
import cv2
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

django.setup()


try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    print("ADVERTENCIA: ultralytics no instalado. Instalar con: pip install ultralytics")


class ParkingDetector:

    VEHICLE_CLASSES = {2: 'auto', 3: 'moto', 5: 'bus', 7: 'camion'}

    def __init__(self, area_id: int, source: str, model_path: str = 'yolov10s.pt'):
        self.area_id = area_id
        self.source = source
        self.model_path = model_path
        self.running = False
        self.frame = None
        self.frame_lock = threading.Lock()
        self.cap = None
        self.model = None
        self.thread = None

        self.parking_spots = []
        self.spots_initialized = False
        self.calibration_frames = 0
        self.calibration_needed = 30
        self.candidate_spots = []

        self.espacios_map = {}
        self.detection_counts = defaultdict(int)

        self.COLOR_OCCUPIED = (0, 0, 255)
        self.COLOR_FREE = (0, 255, 0)
        self.COLOR_BBOX = (255, 165, 0)
        self.COLOR_SPOT = (255, 255, 0)

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=False)
        self.tracks = {}
        self.next_track_id = 1
        self.stationary_threshold_frames = 15

    def _load_model(self):
        if YOLO is None:
            raise RuntimeError("ultralytics no está instalado")

        project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

        candidates = [
            os.path.join(project_root, self.model_path),
            os.path.join(project_root, 'models',
                         os.path.basename(self.model_path)),
            self.model_path,
        ]

        model_full_path = next(
            (p for p in candidates if os.path.exists(p)), None)

        if model_full_path:
            self.model = YOLO(model_full_path)
        else:
            raise FileNotFoundError(
                f"No se encontró el modelo YOLO en ninguna de las rutas: {candidates}")

        print(f"Modelo cargado: {self.model_path}")

    def _detect_parking_lines(self, frame):
        h, w = frame.shape[:2]

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)

        lower_yellow = np.array([15, 80, 80])
        upper_yellow = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        combined_mask = cv2.bitwise_or(white_mask, yellow_mask)

        kernel = np.ones((3, 3), np.uint8)
        combined_mask = cv2.morphologyEx(
            combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        combined_mask = cv2.morphologyEx(
            combined_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        edges = cv2.Canny(combined_mask, 50, 150, apertureSize=3)

        edges = cv2.dilate(edges, kernel, iterations=1)

        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50,
                                minLineLength=40, maxLineGap=20)

        return lines, combined_mask

    def _find_parking_spots_from_lines(self, lines, frame_shape):

        if lines is None:
            return []

        h, w = frame_shape[:2]

        horizontal_lines = []
        vertical_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi

            if abs(angle) < 30 or abs(angle) > 150:
                horizontal_lines.append((min(y1, y2), x1, x2, y1, y2))
            elif 60 < abs(angle) < 120:
                vertical_lines.append((min(x1, x2), y1, y2, x1, x2))

        horizontal_lines.sort(key=lambda x: x[0])
        h_groups = self._cluster_lines(horizontal_lines, threshold=30, axis=0)

        vertical_lines.sort(key=lambda x: x[0])
        v_groups = self._cluster_lines(vertical_lines, threshold=30, axis=0)

        spots = []

        if len(v_groups) >= 2:
            v_positions = sorted([g[0] for g in v_groups])

            if h_groups:
                y_positions = sorted([g[0] for g in h_groups])
                min_y = int(y_positions[0])
                max_y = int(y_positions[-1])
            else:
                min_y = h
                max_y = 0
                for line in vertical_lines:
                    min_y = min(min_y, line[1], line[2])
                    max_y = max(max_y, line[1], line[2])
                if min_y >= max_y:
                    min_y = int(h * 0.3)
                    max_y = int(h * 0.9)

            for i in range(len(v_positions) - 1):
                x_left = int(v_positions[i])
                x_right = int(v_positions[i + 1])
                width = x_right - x_left
                if width <= 60:
                    continue

                est_spot_width = 110
                n_spots = max(1, int(round(width / est_spot_width)))
                spot_w = width / n_spots

                for s in range(n_spots):
                    sx1 = int(x_left + s * spot_w)
                    sx2 = int(x_left + (s + 1) * spot_w)
                    if sx2 - sx1 < 40:
                        continue
                    spot = {
                        'bbox': (sx1, int(min_y), sx2, int(max_y)),
                        'polygon': [(sx1, int(min_y)), (sx2, int(min_y)),
                                    (sx2, int(max_y)), (sx1, int(max_y))],
                        'center': ((sx1 + sx2) // 2, (int(min_y) + int(max_y)) // 2)
                    }
                    spots.append(spot)

        if len(spots) < 2:
            spots = self._find_spots_by_contours(lines, frame_shape)

        return spots

    def _cluster_lines(self, lines, threshold, axis):
        if not lines:
            return []

        groups = []
        current_group = [lines[0]]

        for line in lines[1:]:
            if line[axis] - current_group[-1][axis] < threshold:
                current_group.append(line)
            else:
                avg_pos = np.mean([l[axis] for l in current_group])
                groups.append((avg_pos, current_group))
                current_group = [line]

        if current_group:
            avg_pos = np.mean([l[axis] for l in current_group])
            groups.append((avg_pos, current_group))

        return groups

    def _find_spots_by_contours(self, lines, frame_shape):

        h, w = frame_shape[:2]
        spots = []

        if lines is None or len(lines) < 4:
            return self._create_adaptive_grid(frame_shape)

        line_image = np.zeros((h, w), dtype=np.uint8)
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(line_image, (x1, y1), (x2, y2), 255, 2)

        kernel = np.ones((5, 5), np.uint8)
        line_image = cv2.morphologyEx(
            line_image, cv2.MORPH_CLOSE, kernel, iterations=3)

        contours, _ = cv2.findContours(
            line_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if 2000 < area < 50000:
                rect = cv2.minAreaRect(contour)
                box = cv2.boxPoints(rect)
                box = np.intp(box)

                x, y, rw, rh = cv2.boundingRect(contour)

                aspect_ratio = max(rw, rh) / (min(rw, rh) + 1)
                if 1.2 < aspect_ratio < 4:
                    spot = {
                        'bbox': (x, y, x + rw, y + rh),
                        'polygon': box.tolist(),
                        'center': (x + rw // 2, y + rh // 2)
                    }
                    spots.append(spot)

        return spots

    def _create_adaptive_grid(self, frame_shape):

        h, w = frame_shape[:2]
        spots = []

        spot_width = max(80, w // 7)
        spot_height = int(spot_width * 2)

        cols = max(1, w // spot_width)
        rows = max(1, h // spot_height)

        margin_x = (w - cols * spot_width) // 2
        margin_y = (h - rows * spot_height) // 2

        for row in range(rows):
            for col in range(cols):
                x1 = margin_x + col * spot_width
                y1 = margin_y + row * spot_height
                x2 = x1 + spot_width
                y2 = y1 + spot_height

                spot = {
                    'bbox': (x1, y1, x2, y2),
                    'polygon': [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
                    'center': ((x1 + x2) // 2, (y1 + y2) // 2)
                }
                spots.append(spot)

        return spots

    def _calibrate_spots(self, frame):

        lines, mask = self._detect_parking_lines(frame)
        spots = self._find_parking_spots_from_lines(lines, frame.shape)

        if spots:
            self.candidate_spots.append(spots)

        self.calibration_frames += 1

        if self.calibration_frames >= self.calibration_needed:
            self._consolidate_spots()
            self.spots_initialized = True
            print(
                f"Calibración completa: {len(self.parking_spots)} cajones detectados")

    def _consolidate_spots(self):

        if not self.candidate_spots:
            self.parking_spots = []
            return

        best_detection = max(self.candidate_spots, key=len)

        all_centers = []
        for detection in self.candidate_spots:
            for spot in detection:
                all_centers.append(spot['center'])

        if all_centers:
            self.parking_spots = best_detection

        if hasattr(self, '_last_frame_shape'):
            self.parking_spots = self._postprocess_spots(
                self.parking_spots, self._last_frame_shape)

        if len(self.parking_spots) < 3:
            print("Pocas líneas detectadas, usando grilla adaptativa")
            if hasattr(self, '_last_frame_shape'):
                self.parking_spots = self._create_adaptive_grid(
                    self._last_frame_shape)

    def _postprocess_spots(self, spots, frame_shape, iou_merge=0.5):

        h, w = frame_shape[:2]
        filtered = []
        for spot in spots:
            x1, y1, x2, y2 = spot['bbox']
            area = max(1, (x2 - x1) * (y2 - y1))
            if area < 800 or area > w * h * 0.4:
                continue
            filtered.append(spot)

        merged = []
        for spot in filtered:
            merged_with_existing = False
            for m in merged:
                iou = self._calculate_iou(spot['bbox'], m['bbox'])
                if iou >= iou_merge:
                    bx1 = min(spot['bbox'][0], m['bbox'][0])
                    by1 = min(spot['bbox'][1], m['bbox'][1])
                    bx2 = max(spot['bbox'][2], m['bbox'][2])
                    by2 = max(spot['bbox'][3], m['bbox'][3])
                    m['bbox'] = (bx1, by1, bx2, by2)
                    m['polygon'] = [(bx1, by1), (bx2, by1),
                                    (bx2, by2), (bx1, by2)]
                    m['center'] = ((bx1 + bx2) // 2, (by1 + by2) // 2)
                    merged_with_existing = True
                    break
            if not merged_with_existing:
                merged.append(spot)

        max_spots = max(4, w // 80)
        merged = merged[:max_spots]
        return merged

    def _match_track(self, center, max_dist=40):
        for tid, t in list(self.tracks.items()):
            tx, ty = t['center']
            dist = (tx - center[0])**2 + (ty - center[1])**2
            if dist <= max_dist**2:
                if abs(tx - center[0]) < 2 and abs(ty - center[1]) < 2:
                    t['frames_static'] += 1
                else:
                    t['frames_static'] = 0
                t['center'] = center
                t['last_seen'] = time.time()
                return tid, t
        tid = self.next_track_id
        self.next_track_id += 1
        self.tracks[tid] = {'center': center,
                            'frames_static': 0, 'last_seen': time.time()}
        return tid, self.tracks[tid]

    def _create_spot_from_vehicle(self, vehicle_bbox):

        x1, y1, x2, y2 = vehicle_bbox
        pad_x = int((x2 - x1) * 0.3) + 10
        pad_y = int((y2 - y1) * 0.2) + 5
        sx1 = max(0, x1 - pad_x)
        sy1 = max(0, y1 - pad_y)
        sx2 = x2 + pad_x
        sy2 = y2 + pad_y

        for spot in self.parking_spots:
            iou = self._calculate_iou(spot['bbox'], (sx1, sy1, sx2, sy2))
            if iou > 0.4:
                return None

        new_spot = {
            'bbox': (sx1, sy1, sx2, sy2),
            'polygon': [(sx1, sy1), (sx2, sy1), (sx2, sy2), (sx1, sy2)],
            'center': ((sx1 + sx2) // 2, (sy1 + sy2) // 2)
        }
        self.parking_spots.append(new_spot)
        if hasattr(self, '_last_frame_shape'):
            self.parking_spots = self._postprocess_spots(
                self.parking_spots, self._last_frame_shape)

        if self.spots_initialized:
            try:
                area = Area.objects.get(pk=self.area_id)
                next_idx = len(self.parking_spots)
                clave = f"A{self.area_id}-E{next_idx:02d}"
                espacio, _ = Espacio.objects.get_or_create(
                    clave=clave,
                    defaults={
                        'area': area,
                        'estado': Espacio.Estado.LIBRE,
                        'discapacitado': False
                    }
                )
                new_spot['espacio_id'] = espacio.id
                self.espacios_map[next_idx - 1] = espacio.id
            except Area.DoesNotExist:
                pass

        print(f"Nuevo cajón inferido desde vehículo en {new_spot['center']}")
        return new_spot

    def _init_espacios_from_spots(self):
        try:
            area = Area.objects.get(pk=self.area_id)
        except Area.DoesNotExist:
            print(f"Error: Área {self.area_id} no encontrada")
            return

        existentes = list(Espacio.objects.filter(area=area).order_by('clave'))

        if len(existentes) > len(self.parking_spots) and self.parking_spots:
            sobrantes = existentes[len(self.parking_spots):]
            ids_borrar = [e.id for e in sobrantes]
            Espacio.objects.filter(id__in=ids_borrar).delete()
            print(
                f"Eliminados {len(ids_borrar)} espacios sin detección para área {self.area_id}")
            existentes = existentes[:len(self.parking_spots)]

        for idx, spot in enumerate(self.parking_spots):
            clave = f"A{self.area_id}-E{idx + 1:02d}"

            if idx < len(existentes):
                espacio = existentes[idx]
                if espacio.clave != clave or espacio.area_id != self.area_id:
                    espacio.clave = clave
                    espacio.area = area
                    espacio.save()
                created = False
            else:
                espacio, created = Espacio.objects.get_or_create(
                    clave=clave,
                    defaults={
                        'area': area,
                        'estado': Espacio.Estado.LIBRE,
                        'discapacitado': False
                    }
                )

            spot['espacio_id'] = espacio.id
            self.espacios_map[idx] = espacio.id

            if created:
                print(f"Espacio creado: {clave}")

        print(
            f"Espacios sincronizados: {len(self.espacios_map)} para área {self.area_id}")

    def _calculate_iou(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)

        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])

        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

    def _point_in_polygon(self, point, polygon):
        x, y = point
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    def _update_espacio_estado(self, espacio_id: int, ocupado: bool):
        try:
            espacio = Espacio.objects.get(pk=espacio_id)
            nuevo_estado = Espacio.Estado.OCUPADO if ocupado else Espacio.Estado.LIBRE

            if espacio.estado != nuevo_estado:
                espacio.estado = nuevo_estado
                espacio.save()
                print(f"Espacio {espacio.clave} -> {nuevo_estado}")
        except Espacio.DoesNotExist:
            pass

    def _draw_spots(self, frame, occupied_spots: set):
        for idx, spot in enumerate(self.parking_spots):
            is_occupied = idx in occupied_spots
            color = self.COLOR_OCCUPIED if is_occupied else self.COLOR_FREE

            polygon = np.array(spot['polygon'], np.int32)

            overlay = frame.copy()
            cv2.fillPoly(overlay, [polygon], color)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

            cv2.polylines(frame, [polygon], True, color, 2)

            espacio_id = spot.get('espacio_id')
            if espacio_id:
                try:
                    espacio = Espacio.objects.get(pk=espacio_id)
                    label = espacio.clave
                    estado_txt = "OCUPADO" if is_occupied else "LIBRE"

                    cx, cy = spot['center']

                    (tw, th), _ = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(frame, (cx - tw//2 - 5, cy - th - 5),
                                  (cx + tw//2 + 5, cy + 5), (0, 0, 0), -1)
                    cv2.putText(frame, label, (cx - tw//2, cy),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                    (tw2, th2), _ = cv2.getTextSize(
                        estado_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                    cv2.rectangle(frame, (cx - tw2//2 - 3, cy + 5),
                                  (cx + tw2//2 + 3, cy + th2 + 12), color, -1)
                    cv2.putText(frame, estado_txt, (cx - tw2//2, cy + th2 + 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                except Espacio.DoesNotExist:
                    pass

        return frame

    def _process_frame(self, frame):
        if frame is None:
            return None

        h, w = frame.shape[:2]
        self._last_frame_shape = (h, w, 3)

        if not self.spots_initialized:
            self._calibrate_spots(frame)

            progress = int((self.calibration_frames /
                           self.calibration_needed) * 100)
            cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 0), -1)
            cv2.putText(frame, f"Calibrando deteccion de cajones... {progress}%",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Detectando lineas de estacionamiento",
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            lines, mask = self._detect_parking_lines(frame)
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    cv2.line(frame, (x1, y1), (x2, y2), self.COLOR_SPOT, 2)

            return frame

        if not self.espacios_map and self.parking_spots:
            self._init_espacios_from_spots()

        results = self.model(frame, verbose=False, conf=0.45)

        fgmask = self.bg_subtractor.apply(frame)
        _, fg = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones(
            (3, 3), np.uint8), iterations=1)

        current_occupied = set()
        vehicle_bboxes = []

        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])

                if cls_id not in self.VEHICLE_CLASSES:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])

                vehicle_bbox = (x1, y1, x2, y2)
                vehicle_center = ((x1 + x2) // 2, (y1 + y2) // 2)
                vehicle_bboxes.append((vehicle_bbox, cls_id, conf))

                cx, cy = vehicle_center
                moving = False
                if 0 <= cy < fg.shape[0] and 0 <= cx < fg.shape[1]:
                    moving = fg[cy, cx] > 0

                tid, track = self._match_track(vehicle_center)

                if not moving:
                    track['frames_static'] += 1
                else:
                    track['frames_static'] = 0

                if track['frames_static'] >= self.stationary_threshold_frames:
                    contained = False
                    for idx, spot in enumerate(self.parking_spots):
                        if self._point_in_polygon(vehicle_center, spot['polygon']):
                            contained = True
                            break
                    if not contained:
                        new_spot = self._create_spot_from_vehicle(vehicle_bbox)

                best_iou = 0
                best_spot_idx = -1
                for idx, spot in enumerate(self.parking_spots):
                    iou = self._calculate_iou(vehicle_bbox, spot['bbox'])
                    center_in_spot = self._point_in_polygon(
                        vehicle_center, spot['polygon'])
                    if iou > best_iou or (center_in_spot and iou > 0.1):
                        best_iou = iou
                        best_spot_idx = idx

                if best_spot_idx >= 0 and best_iou > 0.12:
                    current_occupied.add(best_spot_idx)

        for idx in range(len(self.parking_spots)):
            if idx in current_occupied:
                self.detection_counts[idx] = min(
                    self.detection_counts[idx] + 2, 10)
            else:
                self.detection_counts[idx] = max(
                    self.detection_counts[idx] - 1, 0)

        stable_occupied = {idx for idx,
                           count in self.detection_counts.items() if count >= 3}

        for idx, espacio_id in self.espacios_map.items():
            self._update_espacio_estado(espacio_id, idx in stable_occupied)

        frame = self._draw_spots(frame, stable_occupied)

        try:
            area = Area.objects.get(pk=self.area_id)
            total = len(self.parking_spots)
            ocupados = len(stable_occupied)
            libres = total - ocupados
            info_text = f"Area: {area.nombre} | Cajones: {libres} libres / {ocupados} ocupados"
            cv2.rectangle(frame, (0, 0), (500, 35), (0, 0, 0), -1)
            cv2.putText(frame, info_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        except Area.DoesNotExist:
            pass

        return frame

    def _capture_loop(self):
        print(f"Iniciando captura de {self.source} para área {self.area_id}")

        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            print(f"Error: No se pudo abrir {self.source}")
            self.running = False
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

        frame_count = 0
        process_every = 2

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("Conexión perdida, reintentando...")
                time.sleep(2)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.source)
                continue

            frame_count += 1

            if frame_count % process_every == 0 or not self.spots_initialized:
                processed = self._process_frame(frame)
                if processed is not None:
                    with self.frame_lock:
                        self.frame = processed

            time.sleep(0.033)

        self.cap.release()
        print(f"Captura detenida para área {self.area_id}")

    def start(self):
        if self.running:
            return

        self._load_model()
        self.running = True
        self.spots_initialized = False
        self.calibration_frames = 0
        self.candidate_spots = []
        self.parking_spots = []
        self.espacios_map = {}
        self.detection_counts = defaultdict(int)

        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print(f"Detector iniciado para área {self.area_id}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print(f"Detector detenido para área {self.area_id}")

    def get_frame_jpeg(self) -> bytes:
        with self.frame_lock:
            if self.frame is None:
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "Iniciando detector...", (150, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                _, jpeg = cv2.imencode('.jpg', placeholder)
                return jpeg.tobytes()

            _, jpeg = cv2.imencode('.jpg', self.frame, [
                                   cv2.IMWRITE_JPEG_QUALITY, 80])
            return jpeg.tobytes()


_active_detectors = {}
_detectors_lock = threading.Lock()


def get_detector(area_id: int) -> ParkingDetector:
    with _detectors_lock:
        return _active_detectors.get(area_id)


def start_detector(area_id: int) -> ParkingDetector:
    with _detectors_lock:
        if area_id in _active_detectors:
            _active_detectors[area_id].stop()

        try:
            area = Area.objects.get(pk=area_id)
            device = area.dispositivos.first()
            if not device:
                raise ValueError(
                    f"Área {area_id} no tiene dispositivo configurado")

            source = device.ruta
            detector = ParkingDetector(area_id, source)
            detector.start()
            _active_detectors[area_id] = detector
            return detector
        except Area.DoesNotExist:
            raise ValueError(f"Área {area_id} no encontrada")


def stop_detector(area_id: int):
    with _detectors_lock:
        if area_id in _active_detectors:
            _active_detectors[area_id].stop()
            del _active_detectors[area_id]


def stop_all_detectors():
    with _detectors_lock:
        for detector in _active_detectors.values():
            detector.stop()
        _active_detectors.clear()
