from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.db.models import Count, Q
from django.utils import timezone

import re
from app.models import Area, Espacio


def _annotated_areas(area_id: Optional[int] = None):
    qs = Area.objects.all()
    if area_id is not None:
        qs = qs.filter(id=area_id)
    return qs.annotate(
        libres=Count('espacios', filter=Q(
            espacios__estado=Espacio.Estado.LIBRE)),
        ocupados=Count('espacios', filter=Q(
            espacios__estado=Espacio.Estado.OCUPADO)),
        total=Count('espacios'),
    )


def get_area_status(area_id: Optional[int] = None) -> List[Dict]:
    areas = _annotated_areas(area_id)
    results = []
    for area in areas:
        libres = area.libres or 0
        total = area.total or 0
        ocupados = area.ocupados or 0
        results.append(
            {
                "area_id": area.id,
                "area": area.nombre,
                "libres": libres,
                "ocupados": ocupados,
                "total": total,
                "fecha": timezone.now().isoformat(),
            }
        )
    return results


def predict_area_status(area_id: int, target_dt: Optional[datetime] = None) -> Dict:
    target = target_dt or timezone.now() + timedelta(hours=1)
    current = get_area_status(area_id=area_id)
    if not current:
        raise Area.DoesNotExist()

    info = current[0]
    total = info.get("total", 0) or 0
    libres = info.get("libres", 0) or 0

    prob = 0.0
    if total > 0:
        prob = libres / total

    delta_hours = max(0.0, (target - timezone.now()).total_seconds() / 3600.0)
    decay = 1 / (1 + 0.25 * delta_hours)
    prob = max(0.05, min(0.95, prob * decay + 0.05))

    esperados_libres = int(round(prob * total)) if total > 0 else 0

    return {
        "area_id": info["area_id"],
        "area": info["area"],
        "probabilidad_disponible": round(prob, 3),
        "esperados_libres": esperados_libres,
        "total": total,
        "fecha_objetivo": target.isoformat(),
        "base_libres_actuales": libres,
    }


def find_area_by_name_fragment(text: str) -> Optional[Area]:
    def normalize(s: str) -> str:
        return re.sub(r"[^a-z0-9\s]", " ", s.lower())

    text_norm = normalize(text)
    text_compact = text_norm.replace(" ", "")

    best_area = None
    for area in Area.objects.all():
        name_norm = normalize(area.nombre)
        name_compact = name_norm.replace(" ", "")

        if name_norm.strip() and (name_norm in text_norm or text_norm in name_norm):
            return area
        if name_compact and (name_compact in text_compact or text_compact in name_compact):
            best_area = best_area or area
            continue

        name_tokens = [t for t in name_norm.split() if t]
        if name_tokens:
            prefix = " ".join(name_tokens[:2]) if len(
                name_tokens) >= 2 else name_tokens[0]
            if prefix in text_norm:
                best_area = best_area or area

    return best_area
