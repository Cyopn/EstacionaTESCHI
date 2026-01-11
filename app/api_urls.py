from django.urls import path
from app.chatbot.chat_view import ChatbotView
from app.api_views.availability_view import (
    AvailabilityListView,
    AvailabilityDetailView,
    AvailabilityPredictView,
)

urlpatterns = [
    path('chat/', ChatbotView.as_view(), name='chatbot'),
    path('availability/', AvailabilityListView.as_view(), name='availability_list'),
    path('availability/<int:area_id>/',
         AvailabilityDetailView.as_view(), name='availability_detail'),
    path('availability/<int:area_id>/predict/',
         AvailabilityPredictView.as_view(), name='availability_predict'),
]
