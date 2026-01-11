"""
Vistas para el servicio de detección de placas vehiculares.
Entrega streaming MJPEG y permite controlar el detector.
"""
import json
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from app.detection.plate_detector_service import (
    get_plate_detector,
    start_plate_detector,
    start_plate_detector_by_source,
    stop_plate_detector,
)
from app.models import Vehiculo, Acceso


def _generate_mjpeg(detector):
    while detector.running:
        frame = detector.get_frame_jpeg()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
        )


class PlateStreamView(View):
    """Stream MJPEG con detección de placas."""

    def get(self, request, device_id):
        detector = get_plate_detector(device_id)
        if not detector or not detector.running:
            try:
                detector = start_plate_detector(device_id)
            except ValueError as exc:
                return JsonResponse({'error': str(exc)}, status=400)

        return StreamingHttpResponse(
            _generate_mjpeg(detector),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )


class PlateStreamByIpView(View):
    """Stream MJPEG usando IP/URL de cámara proporcionada por querystring ?ip=..."""

    def get(self, request):
        source = request.GET.get('ip')
        if not source:
            return JsonResponse({'error': 'Parámetro ip requerido'}, status=400)

        detector = get_plate_detector(source)
        if not detector or not detector.running:
            detector = start_plate_detector_by_source(source)

        return StreamingHttpResponse(
            _generate_mjpeg(detector),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )


@method_decorator(csrf_exempt, name='dispatch')
class PlateControlView(View):
    """Inicia o detiene el detector de placas."""

    def post(self, request, device_id):
        body = json.loads(request.body) if request.body else {}
        action = body.get('action', 'start')

        try:
            if action == 'start':
                detector = start_plate_detector(device_id)
                status = detector.status()
                status['stream_url'] = f"/plates/stream/{device_id}/"
                return JsonResponse(status)
            if action == 'stop':
                stop_plate_detector(device_id)
                return JsonResponse({'device_id': device_id, 'running': False})
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        except Exception as exc:  # pragma: no cover
            return JsonResponse({'error': str(exc)}, status=500)

        return JsonResponse({'error': 'Acción inválida'}, status=400)

    def get(self, request, device_id):
        detector = get_plate_detector(device_id)
        if detector:
            status = detector.status()
            status['stream_url'] = f"/plates/stream/{device_id}/"
            return JsonResponse(status)
        return JsonResponse({'device_id': device_id, 'running': False})


@method_decorator(csrf_exempt, name='dispatch')
class PlateControlByIpView(View):
    """Inicia o detiene el detector de placas por IP/URL."""

    def post(self, request):
        source = request.GET.get('ip')
        body = json.loads(request.body) if request.body else {}
        action = body.get('action', 'start')

        if not source:
            return JsonResponse({'error': 'Parámetro ip requerido'}, status=400)

        try:
            if action == 'start':
                detector = start_plate_detector_by_source(source)
                status = detector.status()
                status['stream_url'] = f"/plates/stream_by_ip/?ip={source}"
                return JsonResponse(status)
            if action == 'stop':
                stop_plate_detector(source)
                return JsonResponse({'identifier': source, 'running': False})
        except Exception as exc:  # pragma: no cover
            return JsonResponse({'error': str(exc)}, status=500)

        return JsonResponse({'error': 'Acción inválida'}, status=400)

    def get(self, request):
        source = request.GET.get('ip')
        if not source:
            return JsonResponse({'error': 'Parámetro ip requerido'}, status=400)

        detector = get_plate_detector(source)
        if detector:
            status = detector.status()
            status['stream_url'] = f"/plates/stream_by_ip/?ip={source}"
            return JsonResponse(status)
        return JsonResponse({'identifier': source, 'running': False})


class PlateStatusView(View):
    """Devuelve último texto detectado y estado de ejecución."""

    def get(self, request, device_id):
        detector = get_plate_detector(device_id)
        if detector:
            status = detector.status()
            status['stream_url'] = f"/plates/stream/{device_id}/"
            return JsonResponse(status)
        return JsonResponse({'device_id': device_id, 'running': False})


class PlateStatusByIpView(View):
    """Devuelve estado del detector asociado a una IP/URL."""

    def get(self, request):
        source = request.GET.get('ip')
        if not source:
            return JsonResponse({'error': 'Parámetro ip requerido'}, status=400)

        detector = get_plate_detector(source)
        if detector:
            status = detector.status()
            status['stream_url'] = f"/plates/stream_by_ip/?ip={source}"
            return JsonResponse(status)
        return JsonResponse({'identifier': source, 'running': False})


class PlateLookupView(View):
    """Busca un vehículo por placa exacta (mayúsculas) y retorna datos básicos."""

    def get(self, request):
        placa = request.GET.get('placa', '').strip().upper()
        if not placa:
            return JsonResponse({'error': 'Parámetro placa requerido'}, status=400)

        try:
            veh = Vehiculo.objects.select_related('usuario').get(placa=placa)
            usuario = veh.usuario
            return JsonResponse({
                'found': True,
                'placa': veh.placa,
                'marca': veh.marca,
                'modelo': veh.modelo,
                'color': veh.color,
                'usuario': {
                    'nombre': getattr(usuario, 'nombre', ''),
                    'apellidos': getattr(usuario, 'apellidos', ''),
                    'matricula': getattr(usuario, 'matricula', '')
                } if usuario else None
            })
        except Vehiculo.DoesNotExist:
            return JsonResponse({'found': False, 'placa': placa})


@method_decorator(csrf_exempt, name='dispatch')
class PlateLogAccessView(View):
    """Registra un acceso autorizado en el modelo Acceso."""

    def post(self, request):
        try:
            body = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        placa = body.get('placa', '').strip().upper()
        tipo = body.get('tipo', Acceso.Tipo.ENTRADA)

        if not placa:
            return JsonResponse({'error': 'Parámetro placa requerido'}, status=400)

        if tipo not in Acceso.Tipo.values:
            tipo = Acceso.Tipo.ENTRADA

        try:
            vehiculo = Vehiculo.objects.select_related(
                'usuario').get(placa=placa)
        except Vehiculo.DoesNotExist:
            return JsonResponse({'error': 'Vehículo no encontrado', 'placa': placa}, status=404)

        Acceso.objects.create(
            fecha=timezone.now(),
            tipo=tipo,
            usuario=vehiculo.usuario,
            vehiculo=vehiculo,
        )

        return JsonResponse({
            'logged': True,
            'placa': placa,
            'tipo': tipo
        }, status=201)
