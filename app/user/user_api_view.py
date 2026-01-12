import json
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import check_password

from app.models import Usuario, Area


def _parse_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def _serialize_user(user: Usuario):
    return {
        'id': user.id,
        'nombre': user.nombre,
        'apellidos': user.apellidos,
        'correo': user.correo,
        'matricula': user.matricula,
        'telefono': user.telefono,
        'area': user.area_id,
    }


@method_decorator(csrf_exempt, name='dispatch')
class UserApiView(View):

    def post(self, request):
        data = _parse_body(request)
        if data is None:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        required = ['nombre', 'apellidos', 'correo', 'matricula', 'contraseña']
        missing = [k for k in required if not data.get(k)]
        if missing:
            return JsonResponse({'error': f'Faltan campos: {", ".join(missing)}'}, status=400)

        area = None
        area_id = data.get('area')
        if area_id:
            area = Area.objects.filter(id=area_id).first()
            if area_id and not area:
                return JsonResponse({'error': 'Área no encontrada'}, status=404)

        if Usuario.objects.filter(matricula=data['matricula']).exists():
            return JsonResponse({'error': 'La matrícula ya existe'}, status=409)

        user = Usuario(
            nombre=data['nombre'],
            apellidos=data['apellidos'],
            correo=data['correo'],
            matricula=data['matricula'],
            telefono=data.get('telefono'),
            contraseña=data['contraseña'],
            area=area,
        )
        user.save()
        return JsonResponse({'created': True, 'user': _serialize_user(user)}, status=201)

    def put(self, request):
        data = _parse_body(request)
        if data is None:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        matricula = data.get('matricula')
        if not matricula:
            return JsonResponse({'error': 'matricula requerida'}, status=400)

        try:
            user = Usuario.objects.get(matricula=matricula)
        except Usuario.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        for field in ['nombre', 'apellidos', 'correo', 'telefono']:
            if field in data and data[field] is not None:
                setattr(user, field, data[field])

        if data.get('contraseña'):
            user.contraseña = data['contraseña']

        if 'area' in data:
            area_id = data.get('area')
            if area_id:
                area = Area.objects.filter(id=area_id).first()
                if not area:
                    return JsonResponse({'error': 'Área no encontrada'}, status=404)
                user.area = area
            else:
                user.area = None

        user.save()
        return JsonResponse({'updated': True, 'user': _serialize_user(user)}, status=200)

    def dispatch(self, request, *args, **kwargs):
        if request.method not in {'POST', 'PUT'}:
            return HttpResponseNotAllowed(['POST', 'PUT'])
        return super().dispatch(request, *args, **kwargs)


class AreaListApiView(View):

    def get(self, request):
        areas = Area.objects.all().order_by('nombre')
        data = [{'id': a.id, 'nombre': a.nombre} for a in areas]
        return JsonResponse({'areas': data})


@method_decorator(csrf_exempt, name='dispatch')
class LoginApiView(View):

    def post(self, request):
        data = _parse_body(request)
        if data is None:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        correo = data.get('correo')
        password = data.get('contraseña')

        if not correo or not password:
            return JsonResponse({'error': 'correo y contraseña requeridos'}, status=400)

        try:
            user = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            return JsonResponse({'error': 'Credenciales inválidas'}, status=401)

        stored = user.contraseña
        ok = False
        try:
            ok = check_password(password, stored)
        except Exception:
            ok = stored == password

        if not ok:
            return JsonResponse({'error': 'Credenciales inválidas'}, status=401)

        return JsonResponse({'authenticated': True, 'user': _serialize_user(user)})

    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        return super().dispatch(request, *args, **kwargs)
