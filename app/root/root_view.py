from django.shortcuts import render
from django.views import View

class RootView(View):
    def get(self, request):
        return render(request, 'root.html')