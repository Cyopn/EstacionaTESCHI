from django.shortcuts import render
from django.views import View

class AccessView(View):
    def get(self, request):
        return render(request, 'access.html')