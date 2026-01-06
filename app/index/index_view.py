from django.shortcuts import render
from django.views import View
import random

from app.models import Area


class IndexView(View):
    def get(self, request):
        areas = list(Area.objects.all())
        # asignar un color hex aleatorio a cada área
        for area in areas:
            area.color = "#{:06x}".format(random.randint(0, 0xFFFFFF))

        espacios = []
        return render(request, 'index.html', {'areas': areas, 'espacios': espacios})
