from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from app.models import Evento, Area


class EventsView(View):
    def get(self, request):
        eventos = Evento.objects.all().order_by('-fecha_inicio')
        areas = Area.objects.all().order_by('nombre')
        return render(request, 'events.html', {
            'eventos': eventos,
            'areas': areas,
        })

    def post(self, request):
        action = (request.POST.get('action') or '').lower()
        if action == 'create':
            nombre = (request.POST.get('nombre') or '').strip()
            fecha_inicio = (request.POST.get('fecha_inicio') or '').strip()
            fecha_fin = (request.POST.get('fecha_fin') or '').strip()
            descripcion = (request.POST.get('descripcion') or '').strip()
            prioridad = (request.POST.get('prioridad') or 'MEDIA').strip()
            area_id = request.POST.get('area') or None

            if not nombre or not fecha_inicio or not fecha_fin:
                messages.error(request, 'Nombre y fechas son obligatorios.')
                return redirect('events')
            if not descripcion:
                messages.error(request, 'La descripción es obligatoria.')
                return redirect('events')
            if not area_id:
                messages.error(request, 'Debe seleccionar un área.')
                return redirect('events')
            if fecha_inicio > fecha_fin:
                messages.error(
                    request, 'Fecha inicio no puede ser posterior a fecha fin.')
                return redirect('events')

            try:
                area_obj = Area.objects.get(pk=area_id)
            except (Area.DoesNotExist, TypeError, ValueError):
                messages.error(request, 'Área seleccionada no válida.')
                return redirect('events')

            Evento.objects.create(
                nombre=nombre,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                descripcion=descripcion,
                prioridad=prioridad,
                area=area_obj,
            )
            messages.success(request, 'Evento creado.')
            return redirect('events')

        if action == 'delete':
            evento_id = request.POST.get('evento_id') or ''
            if not evento_id:
                messages.error(
                    request, 'No se proporcionó evento para eliminar.')
                return redirect('events')
            try:
                ev = Evento.objects.get(pk=evento_id)
                ev.delete()
                messages.success(request, 'Evento eliminado.')
            except Evento.DoesNotExist:
                messages.error(request, 'Evento no encontrado.')
            return redirect('events')

        evento_id = request.POST.get('evento_id') or ''
        if not evento_id:
            messages.error(request, 'No se proporcionó evento para modificar.')
            return redirect('events')

        try:
            ev = Evento.objects.get(pk=evento_id)
        except Evento.DoesNotExist:
            messages.error(request, 'Evento no encontrado.')
            return redirect('events')

        nombre = (request.POST.get('nombre') or '').strip()
        fecha_inicio = (request.POST.get('fecha_inicio') or '').strip()
        fecha_fin = (request.POST.get('fecha_fin') or '').strip()
        descripcion = (request.POST.get('descripcion') or '').strip()
        prioridad = (request.POST.get('prioridad') or 'MEDIA').strip()
        area_id = request.POST.get('area') or None

        if not nombre or not fecha_inicio or not fecha_fin:
            messages.error(request, 'Nombre y fechas son obligatorios.')
            return redirect('events')
        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
            return redirect('events')
        if not area_id:
            messages.error(request, 'Debe seleccionar un área.')
            return redirect('events')
        if fecha_inicio > fecha_fin:
            messages.error(
                request, 'Fecha inicio no puede ser posterior a fecha fin.')
            return redirect('events')

        ev.nombre = nombre
        ev.fecha_inicio = fecha_inicio
        ev.fecha_fin = fecha_fin
        ev.descripcion = descripcion
        ev.prioridad = prioridad

        try:
            ev.area = Area.objects.get(pk=area_id)
        except (Area.DoesNotExist, TypeError, ValueError):
            messages.error(request, 'Área seleccionada no válida.')
            return redirect('events')

        ev.save()
        messages.success(request, 'Evento actualizado.')
        return redirect('events')
