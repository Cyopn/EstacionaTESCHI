from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from app.models import Empleado


class EmployeeView(View):
    def get(self, request):
        employees = Empleado.objects.all().order_by('numero_empleado')
        return render(request, 'employee.html', {'employees': employees})

    def post(self, request):
        numero = request.POST.get('numero_empleado')
        if not numero:
            return redirect(request.path)

        empleado = get_object_or_404(Empleado, numero_empleado=numero)
        empleado.nombre = request.POST.get('nombre', empleado.nombre)
        empleado.apellidos = request.POST.get('apellidos', empleado.apellidos)
        empleado.correo = request.POST.get('correo', empleado.correo)
        contrasena = request.POST.get('contraseña')
        if contrasena:
            empleado.contraseña = contrasena
        empleado.telefono = request.POST.get('telefono', empleado.telefono)
        empleado.rol = request.POST.get('rol', empleado.rol)
        empleado.puesto = request.POST.get('puesto', empleado.puesto)
        empleado.save()

        return redirect(request.path)
