from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from app.models import Usuario, Area


class UserView(View):
    def get(self, request):
        usuarios = Usuario.objects.select_related('area').all()
        areas = Area.objects.all().order_by('nombre')
        return render(request, 'user.html', {'usuarios': usuarios, 'areas': areas})

    def post(self, request):
        matricula = request.POST.get('matricula')
        if not matricula:
            messages.error(request, 'Matrícula no proporcionada.')
            return redirect(request.path)

        usuario = get_object_or_404(Usuario, matricula=matricula)
        if request.POST.get('delete'):
            usuario.delete()
            messages.success(request, 'Usuario eliminado correctamente.')
            return redirect(request.path)
        usuario.nombre = request.POST.get('nombre', usuario.nombre)
        usuario.apellidos = request.POST.get('apellidos', usuario.apellidos)
        usuario.correo = request.POST.get('correo', usuario.correo)
        contrasena = request.POST.get('contraseña')
        if contrasena:
            usuario.contraseña = contrasena
        usuario.telefono = request.POST.get('telefono', usuario.telefono)

        area_id = request.POST.get('area')
        if area_id:
            try:
                usuario.area = Area.objects.get(id=area_id)
            except Area.DoesNotExist:
                messages.error(request, 'Área seleccionada no es válida.')
                return redirect(request.path)
        else:
            usuario.area = None
        usuario.save()

        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect(request.path)
