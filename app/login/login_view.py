from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from app.models import Empleado


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        correo = request.POST.get('correo', '').strip()
        contraseña = request.POST.get('contrasena', '').strip()

        if not correo or not contraseña:
            messages.error(request, 'Correo y contraseña son requeridos')
            return redirect(request.path)

        try:
            empleado = Empleado.objects.get(correo=correo)
        except Empleado.DoesNotExist:
            messages.error(request, 'Correo o contraseña incorrectos')
            return redirect(request.path)

        if not check_password(contraseña, empleado.contraseña):
            messages.error(request, 'Correo o contraseña incorrectos')
            return redirect(request.path)

        request.session['empleado_id'] = empleado.id
        request.session['empleado_nombre'] = f"{empleado.nombre} {empleado.apellidos}"

        return redirect('index')
