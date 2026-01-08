from django.shortcuts import render
from django.views import View

class EntryView(View):
    def get(self, request):
        return render(request, 'entry.html')