from django.shortcuts import render, redirect
from django.views import View
from django.db import IntegrityError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib import messages
from app.models import Empleado
from django.contrib.auth.hashers import make_password


class RegisterView(View):
    def get(self, request):
        form_data = request.session.pop('register_form', None)
        context = {}
        if form_data:
            context.update(form_data)
        return render(request, 'register.html', context)

    def post(self, request):
        nombre = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        correo = request.POST.get('correo', '').strip()
        telefono = request.POST.get('telefono', '').strip() or None
        numero_empleado = request.POST.get('numero_empleado', '').strip()
        contraseña = request.POST.get('contrasena', '').strip()
        confirmar = request.POST.get('confirmar', '').strip()

        errors = []

        if not nombre:
            errors.append('Nombre requerido')
        if not apellidos:
            errors.append('Apellidos requeridos')

        if not correo:
            errors.append('Correo requerido')
        else:
            try:
                validate_email(correo)
            except ValidationError:
                errors.append('Correo inválido')
            else:
                if Empleado.objects.filter(correo=correo).exists():
                    errors.append('Correo ya registrado')

        if telefono:
            if len(telefono) < 7:
                errors.append('Teléfono inválido')

        if not numero_empleado:
            errors.append('Número de empleado requerido')
        else:
            try:
                numero_empleado_int = int(numero_empleado)
                if numero_empleado_int <= 0:
                    errors.append('Número de empleado inválido')
                elif Empleado.objects.filter(numero_empleado=numero_empleado_int).exists():
                    errors.append('Número de empleado ya registrado')
            except ValueError:
                errors.append('Número de empleado inválido')

        if not contraseña:
            errors.append('Contraseña requerida')
        else:
            if len(contraseña) < 8:
                errors.append('La contraseña debe tener al menos 8 caracteres')

        if contraseña != confirmar:
            errors.append('Las contraseñas no coinciden')

        if errors:
            request.session['register_form'] = {
                'nombre': nombre,
                'apellidos': apellidos,
                'correo': correo,
                'telefono': telefono or '',
                'numero_empleado': numero_empleado,
            }
            for e in errors:
                messages.error(request, e)
            return redirect(request.path)

        try:
            empleado = Empleado(
                nombre=nombre,
                apellidos=apellidos,
                correo=correo,
                contraseña=make_password(contraseña),
                telefono=telefono,
                numero_empleado=numero_empleado_int,
                rol=Empleado.Rol.GUARDIA,
                puesto=Empleado.Puesto.EDIFICIO,
            )
            empleado.save()
        except IntegrityError:
            errors.append('Error al guardar el empleado (datos duplicados)')
            context = {
                'errors': errors,
                'nombre': nombre,
                'apellidos': apellidos,
                'correo': correo,
                'telefono': telefono or '',
                'numero_empleado': numero_empleado,
            }
            return render(request, 'register.html', context)

        return redirect('login')
