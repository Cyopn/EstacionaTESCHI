from django.shortcuts import render, redirect
from django.views import View
from app.models import Area, Dispositivo, Espacio
from django.contrib import messages


class AllocationView(View):
    def get(self, request):
        areas = Area.objects.all().order_by('nombre')
        for area in areas:
            area.capacidad_total = area.espacios.count()
            area.capacidad_disponible = area.espacios.filter(
                estado=Espacio.Estado.LIBRE).count()
            device = area.dispositivos.first()
            if device:
                area.dispositivo_id = device.id
                area.dispositivo_clave = device.clave
                area.dispositivo_ruta = device.ruta
            else:
                area.dispositivo_id = None
                area.dispositivo_clave = ''
                area.dispositivo_ruta = ''
        return render(request, 'allocation.html', {'areas': areas})

    def post(self, request):
        action = request.POST.get('action')

        if action == 'create':
            nombre = request.POST.get('area_nombre')
            dispositivo_clave = request.POST.get('dispositivo_clave')
            dispositivo_ruta = request.POST.get('dispositivo_ruta')
            if nombre and dispositivo_clave and dispositivo_ruta:
                area = Area.objects.create(nombre=nombre)
                Dispositivo.objects.create(
                    clave=dispositivo_clave,
                    ruta=dispositivo_ruta,
                    area=area
                )
                messages.success(request, 'Área creada correctamente.')
                return redirect('allocation')
            error = 'Todos los campos son requeridos.'
            messages.error(request, error)

        elif action == 'update':
            area_id = request.POST.get('area_id')
            nombre = request.POST.get('area_nombre')
            dispositivo_id = request.POST.get('dispositivo_id')
            dispositivo_clave = request.POST.get('dispositivo_clave')
            dispositivo_ruta = request.POST.get('dispositivo_ruta')
            try:
                area = Area.objects.get(pk=area_id)
                if nombre:
                    area.nombre = nombre
                    area.save()
                else:
                    error = 'El nombre es requerido.'
                    messages.error(request, error)
                    raise ValueError('Nombre requerido')

                if dispositivo_id:
                    try:
                        dev = Dispositivo.objects.get(
                            pk=dispositivo_id, area=area)
                        if dispositivo_clave is not None:
                            dev.clave = dispositivo_clave
                        if dispositivo_ruta is not None:
                            dev.ruta = dispositivo_ruta
                        dev.save()
                    except Dispositivo.DoesNotExist:
                        if dispositivo_clave and dispositivo_ruta:
                            Dispositivo.objects.create(
                                clave=dispositivo_clave, ruta=dispositivo_ruta, area=area)
                else:
                    if dispositivo_clave and dispositivo_ruta:
                        Dispositivo.objects.create(
                            clave=dispositivo_clave, ruta=dispositivo_ruta, area=area)

                messages.success(request, 'Área actualizada correctamente.')
                return redirect('allocation')
            except (Area.DoesNotExist, TypeError, ValueError):
                if 'error' not in locals():
                    error = 'Área no encontrada.'
                messages.error(request, error)

        elif action == 'delete':
            area_id = request.POST.get('area_id')
            try:
                area = Area.objects.get(pk=area_id)
                Espacio.objects.filter(area=area).delete()
                Dispositivo.objects.filter(area=area).delete()
                area.delete()
                messages.success(request, 'Área eliminada correctamente.')
                return redirect('allocation')
            except (Area.DoesNotExist, TypeError, ValueError):
                error = 'Área no encontrada.'
                messages.error(request, error)

        else:
            error = 'Acción no válida.'
            messages.error(request, error)

        areas = Area.objects.all().order_by('nombre')
        for area in areas:
            area.capacidad_total = area.espacios.count()
            area.capacidad_disponible = area.espacios.filter(
                estado=Espacio.Estado.LIBRE).count()
        return render(request, 'allocation.html', {'areas': areas, 'error': error})
