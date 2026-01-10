from django.shortcuts import render
from django.views import View
import random

from app.models import Area, Espacio


class IndexView(View):
    def get(self, request):
        areas = list(Area.objects.all())
        for area in areas:
            area.color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            total = area.espacios.count()
            libres = area.espacios.filter(estado=Espacio.Estado.LIBRE).count()
            area.capacidad_total = total
            area.capacidad_disponible = libres

        return render(request, 'index.html', {'areas': areas})
