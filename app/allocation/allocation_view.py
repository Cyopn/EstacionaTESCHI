from django.shortcuts import render
from django.views import View

class AllocationView(View):
    def get(self, request):
        return render(request, 'allocation.html')