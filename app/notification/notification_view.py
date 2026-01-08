from django.shortcuts import render
from django.views import View

class NotificationView(View):
    def get(self, request):
        return render(request, 'notification.html')