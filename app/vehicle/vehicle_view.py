from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
import re

from app.models import Vehiculo, Usuario


class VehicleView(View):
    def get(self, request):
        vehiculos = Vehiculo.objects.all()
        usuarios = Usuario.objects.all()
        return render(request, 'vehicle.html', {'vehiculos': vehiculos, 'usuarios': usuarios})

    def post(self, request):
        placa = request.POST.get('placa')
        if not placa:
            messages.error(request, 'Placa no proporcionada.')
            return redirect(request.path)

        placa = placa.strip().upper()
        placa_re = re.compile(r'^[A-Z0-9-]{3,10}$')
        if not placa_re.match(placa):
            messages.error(
                request, 'Formato de placa inválido. Use 3-10 caracteres: letras, números y guion.')
            return redirect(request.path)

        action = request.POST.get('action')
        if action == 'delete':
            try:
                vehiculo = Vehiculo.objects.get(placa=placa)
                vehiculo.delete()
                messages.success(request, 'Vehículo eliminado correctamente.')
            except Vehiculo.DoesNotExist:
                messages.error(request, 'Vehículo no encontrado.')
            return redirect(request.path)
        marca = request.POST.get('marca')
        modelo = request.POST.get('modelo')
        color = request.POST.get('color')
        tipo = request.POST.get('tipo_vehiculo')

        usuario_id = request.POST.get('usuario')
        usuario_obj = None
        if usuario_id:
            try:
                usuario_obj = Usuario.objects.get(pk=usuario_id)
            except Usuario.DoesNotExist:
                usuario_obj = None

        if action == 'create':
            if Vehiculo.objects.filter(placa=placa).exists():
                messages.error(request, 'Ya existe un vehículo con esa placa.')
                return redirect(request.path)
            Vehiculo.objects.create(
                placa=placa,
                marca=marca or '',
                modelo=modelo or '',
                color=color or '',
                tipo_vehiculo=tipo or Vehiculo.TipoVehiculo.AUTOMOVIL,
                usuario=usuario_obj,
            )
            messages.success(request, 'Vehículo creado correctamente.')
            return redirect(request.path)

        try:
            vehiculo = Vehiculo.objects.get(placa=placa)
            vehiculo.marca = marca or vehiculo.marca
            vehiculo.modelo = modelo or vehiculo.modelo
            vehiculo.color = color or vehiculo.color
            if tipo:
                vehiculo.tipo_vehiculo = tipo
            vehiculo.usuario = usuario_obj
            vehiculo.save()
            messages.success(request, 'Vehículo actualizado correctamente.')
        except Vehiculo.DoesNotExist:
            messages.error(request, 'Vehículo no encontrado para actualizar.')
        return redirect(request.path)

        return redirect(request.path)
