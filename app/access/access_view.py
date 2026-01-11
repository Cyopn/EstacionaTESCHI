from django.shortcuts import render
from django.views import View

from app.models import Acceso


class AccessView(View):
    def get(self, request):
        accesos = (
            Acceso.objects.select_related('usuario', 'vehiculo')
            .order_by('-fecha')
        )
        return render(request, 'access.html', {'accesos': accesos})
