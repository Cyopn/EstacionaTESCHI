from datetime import datetime

from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.services.availability import get_area_status, predict_area_status


class AvailabilityListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        data = get_area_status()
        return Response(data, status=status.HTTP_200_OK)


class AvailabilityDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, area_id: int):
        data = get_area_status(area_id=area_id)
        if not data:
            return Response({"detail": "Área no encontrada"}, status=status.HTTP_404_NOT_FOUND)
        return Response(data[0], status=status.HTTP_200_OK)


class AvailabilityPredictView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, area_id: int):
        at_str = request.query_params.get("at")
        target_dt = None
        if at_str:
            target_dt = parse_datetime(at_str)
        try:
            result = predict_area_status(area_id=area_id, target_dt=target_dt)
        except Exception:
            return Response({"detail": "Área no encontrada"}, status=status.HTTP_404_NOT_FOUND)
        return Response(result, status=status.HTTP_200_OK)
