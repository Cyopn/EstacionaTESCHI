import json
import time
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseNotAllowed
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import models

from app.models import Notificacion, Usuario
from app.notification.notification_broker import subscribe, unsubscribe, broadcast


def _parse_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def _serialize_notification(n: Notificacion):
    return {
        'id': n.id,
        'usuario_id': n.usuario_id,
        'tipo': n.tipo,
        'cuerpo': n.cuerpo,
        'descripcion': n.descripcion,
        'leido': n.leido,
        'fecha_creacion': n.fecha_creacion.isoformat(),
    }


def _send_sse(payload: str):
    return f"data: {payload}\n\n".encode('utf-8')


@method_decorator(csrf_exempt, name='dispatch')
class NotificationApiView(View):

    def post(self, request):
        data = _parse_body(request)
        if data is None:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        usuario_id = data.get('usuario_id')
        tipo = data.get('tipo') or Notificacion.Tipo.OTRO
        cuerpo = data.get('cuerpo')
        descripcion = data.get('descripcion', '')

        if not cuerpo:
            return JsonResponse({'error': 'cuerpo requerido'}, status=400)

        usuario = None
        if usuario_id:
            usuario = Usuario.objects.filter(id=usuario_id).first()
            if usuario_id and not usuario:
                return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        notif = Notificacion.objects.create(
            usuario=usuario,
            tipo=tipo,
            cuerpo=cuerpo,
            descripcion=descripcion,
            fecha_creacion=timezone.now(),
        )

        payload = _serialize_notification(notif)
        broadcast({'event': 'notificacion', 'data': payload},
                  target_user_id=usuario.id if usuario else None)
        return JsonResponse({'created': True, 'notification': payload}, status=201)

    def get(self, request):
        usuario_id = request.GET.get('usuario_id')
        qs = Notificacion.objects.all().order_by('-fecha_creacion')
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        data = [_serialize_notification(n) for n in qs[:100]]
        return JsonResponse({'notifications': data})

    def dispatch(self, request, *args, **kwargs):
        if request.method not in {'POST', 'GET'}:
            return HttpResponseNotAllowed(['POST', 'GET'])
        return super().dispatch(request, *args, **kwargs)


class NotificationStreamView(View):

    def get(self, request):
        user_id = request.GET.get('usuario_id') or request.GET.get('user_id')
        try:
            uid_int = int(user_id) if user_id else None
        except ValueError:
            uid_int = None

        q = subscribe(uid_int)

        def event_stream():
            try:
                while True:
                    try:
                        msg = q.get(timeout=15)
                        yield _send_sse(msg)
                    except Exception:
                        yield b": keep-alive\n\n"
            finally:
                unsubscribe(q)

        response = StreamingHttpResponse(
            event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
