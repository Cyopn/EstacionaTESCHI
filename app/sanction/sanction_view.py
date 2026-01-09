from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from app.models import Sancion, Vehiculo, Usuario, Area


class SanctionView(View):
    def get(self, request):
        sanciones = Sancion.objects.select_related(
            'vehiculo', 'usuario', 'area').all()
        vehiculos = Vehiculo.objects.all()
        usuarios = Usuario.objects.all()
        areas = Area.objects.all()
        return render(request, 'sanction.html', {
            'sanciones': sanciones,
            'vehiculos': vehiculos,
            'usuarios': usuarios,
            'areas': areas,
        })

    def post(self, request):
        action = request.POST.get('action')
        sancion_id = request.POST.get('sancion_id')

        if action == 'delete' and sancion_id:
            try:
                sanc = Sancion.objects.get(pk=sancion_id)
                sanc.delete()
                messages.success(request, 'Sanción eliminada correctamente.')
            except Sancion.DoesNotExist:
                messages.error(request, 'Sanción no encontrada.')
            return redirect(request.path)

        motivo = request.POST.get('motivo', '').strip()
        fecha = request.POST.get('fecha')
        gravedad = request.POST.get('gravedad')
        vehiculo_id = request.POST.get('vehiculo')
        usuario_id = request.POST.get('usuario')
        area_id = request.POST.get('area')

        vehiculo_obj = None
        usuario_obj = None
        area_obj = None
        if vehiculo_id:
            try:
                vehiculo_obj = Vehiculo.objects.get(pk=vehiculo_id)
            except Vehiculo.DoesNotExist:
                vehiculo_obj = None
        if usuario_id:
            try:
                usuario_obj = Usuario.objects.get(pk=usuario_id)
            except Usuario.DoesNotExist:
                usuario_obj = None
        if area_id:
            try:
                area_obj = Area.objects.get(pk=area_id)
            except Area.DoesNotExist:
                area_obj = None

        if action == 'create':
            sanc = Sancion.objects.create(
                motivo=motivo,
                fecha=fecha or None,
                gravedad=gravedad or Sancion.Gravedad.MODERADA,
                vehiculo=vehiculo_obj,
                usuario=usuario_obj,
                area=area_obj,
            )
            messages.success(request, 'Sanción creada correctamente.')
            return redirect(request.path)

        # default: update existing sancion
        if sancion_id:
            try:
                sanc = Sancion.objects.get(pk=sancion_id)
                sanc.motivo = motivo or sanc.motivo
                sanc.fecha = fecha or sanc.fecha
                if gravedad:
                    sanc.gravedad = gravedad
                sanc.vehiculo = vehiculo_obj
                sanc.usuario = usuario_obj
                sanc.area = area_obj
                sanc.save()
                messages.success(request, 'Sanción actualizada correctamente.')
            except Sancion.DoesNotExist:
                messages.error(
                    request, 'Sanción no encontrada para actualizar.')
        else:
            messages.error(
                request, 'ID de sanción no proporcionado para actualizar.')

        return redirect(request.path)
