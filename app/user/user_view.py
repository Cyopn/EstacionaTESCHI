from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from app.models import Usuario


class UserView(View):
    def get(self, request):
        usuarios = Usuario.objects.all()
        return render(request, 'user.html', {'usuarios': usuarios})

    def post(self, request):
        matricula = request.POST.get('matricula')
        if not matricula:
            messages.error(request, 'Matrícula no proporcionada.')
            return redirect(request.path)

        usuario = get_object_or_404(Usuario, matricula=matricula)
        usuario.nombre = request.POST.get('nombre', usuario.nombre)
        usuario.apellidos = request.POST.get('apellidos', usuario.apellidos)
        usuario.correo = request.POST.get('correo', usuario.correo)
        contrasena = request.POST.get('contraseña')
        if contrasena:
            usuario.contraseña = contrasena
        usuario.telefono = request.POST.get('telefono', usuario.telefono)
        usuario.save()

        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect(request.path)
