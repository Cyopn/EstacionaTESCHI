
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from app.models import Area, Espacio
from app.detection.detector_service import (
    get_detector, start_detector, stop_detector
)


def generate_mjpeg(detector):
    while detector.running:
        frame = detector.get_frame_jpeg()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
        )


class DetectorStreamView(View):
    def get(self, request, area_id):
        detector = get_detector(area_id)

        if not detector or not detector.running:
            try:
                detector = start_detector(area_id)
            except ValueError as e:
                return JsonResponse({'error': str(e)}, status=400)

        return StreamingHttpResponse(
            generate_mjpeg(detector),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )


@method_decorator(csrf_exempt, name='dispatch')
class DetectorControlView(View):
    def post(self, request, area_id):
        try:
            data = json.loads(request.body) if request.body else {}
            action = data.get('action', 'start')

            if action == 'start':
                detector = start_detector(area_id)
                return JsonResponse({
                    'status': 'started',
                    'area_id': area_id,
                    'stream_url': f'/detection/stream/{area_id}/'
                })
            elif action == 'stop':
                stop_detector(area_id)
                return JsonResponse({
                    'status': 'stopped',
                    'area_id': area_id
                })
            else:
                return JsonResponse({'error': 'Acción inválida'}, status=400)

        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def get(self, request, area_id): 
        detector = get_detector(area_id)
        running = detector is not None and detector.running

        return JsonResponse({
            'area_id': area_id,
            'running': running,
            'stream_url': f'/detection/stream/{area_id}/' if running else None
        })


class EspaciosStatusView(View):

    def get(self, request, area_id):
        try:
            area = Area.objects.get(pk=area_id)
            espacios = Espacio.objects.filter(area=area).order_by('clave')

            espacios_data = [{
                'id': e.id,
                'clave': e.clave,
                'estado': e.estado,
                'estado_display': e.get_estado_display(),
                'discapacitado': e.discapacitado
            } for e in espacios]

            total = len(espacios_data)
            ocupados = sum(
                1 for e in espacios_data if e['estado'] == 'OCUPADO')
            libres = total - ocupados

            return JsonResponse({
                'area_id': area_id,
                'area_nombre': area.nombre,
                'total': total,
                'ocupados': ocupados,
                'libres': libres,
                'espacios': espacios_data
            })

        except Area.DoesNotExist:
            return JsonResponse({'error': 'Área no encontrada'}, status=404)
