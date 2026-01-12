import re
import time
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Area, ChatConversation, ChatMessage, Usuario, Evento
from app.services.availability import (
    get_area_status,
    predict_area_status,
    find_area_by_name_fragment,
)
from app.services.ml_chat_model import get_ml_chat_model
from app.services.llm_client import generate_llm_reply


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    usuario_id = serializers.IntegerField(required=False, allow_null=True)


class ChatbotView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        usuario_id = serializer.validated_data.get('usuario_id')

        usuario = None
        if usuario_id is not None:
            try:
                usuario = Usuario.objects.get(id=usuario_id)
            except Usuario.DoesNotExist:
                return Response(
                    {"detail": "Usuario no encontrado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        conversation = None
        if conversation_id is not None:
            try:
                conversation = ChatConversation.objects.get(id=conversation_id)
            except ChatConversation.DoesNotExist:
                return Response(
                    {"detail": "Conversación no encontrada"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            titulo = f"Chat de {usuario.nombre}" if usuario else "Chat"
            conversation = ChatConversation.objects.create(
                usuario=usuario, titulo=titulo)

        started = time.perf_counter()
        bot_payload = self._build_reply(message, usuario, conversation)
        duration_ms = max(1, int((time.perf_counter() - started) * 1000))

        message_obj = ChatMessage.objects.create(
            conversation=conversation,
            usuario=usuario,
            mensaje=message,
            respuesta=bot_payload["texto"],
            tiempo_ms=duration_ms,
        )

        bot_payload.update(
            {
                "conversation_id": conversation.id,
                "tiempo_ms": duration_ms,
                "fecha": message_obj.fecha.isoformat(),
            }
        )

        return Response(bot_payload, status=status.HTTP_200_OK)

    def _build_reply(self, message: str, usuario, conversation: ChatConversation | None):
        lower = message.lower()
        area = find_area_by_name_fragment(lower)

        if self._is_prediction_intent(lower):
            target_dt = self._extract_datetime(lower)
            if not area:
                return {
                    "texto": "¿Para qué área quieres la predicción? Menciona el nombre del área.",
                }
            try:
                prediction = predict_area_status(area.id, target_dt)
            except Exception:
                return {"texto": "No encontré esa área para predecir."}
            texto = self._llm_wrap(
                message,
                facts={
                    "area": prediction["area"],
                    "probabilidad": prediction["probabilidad_disponible"],
                    "esperados_libres": prediction["esperados_libres"],
                    "total": prediction["total"],
                    "fecha_objetivo": prediction["fecha_objetivo"],
                },
            )
            return {"texto": texto, "prediction": prediction}

        if self._is_list_areas_intent(lower):
            nombres = list(Area.objects.values_list("nombre", flat=True))
            if not nombres:
                return {"texto": "No hay áreas registradas aún."}
            texto = "Áreas registradas: " + "; ".join(nombres)
            return {"texto": texto, "areas": nombres}

        if self._is_greeting(lower):
            texto = "Hola, soy tu asistente virtual de EstacionTESCHI. Puedo ayudarte a consultar disponibilidad, predicciones y eventos."
            return {"texto": texto}

        if self._is_events_intent(lower):
            qs = Evento.objects.all()
            if area:
                qs = qs.filter(area=area)
            today = timezone.now().date()
            eventos = list(
                qs.filter(fecha_fin__gte=today)
                .order_by("fecha_inicio")
                .values("nombre", "fecha_inicio", "fecha_fin", "area__nombre", "prioridad")[:5]
            )
            if not eventos:
                eventos = list(
                    qs.order_by("-fecha_inicio")
                    .values("nombre", "fecha_inicio", "fecha_fin", "area__nombre", "prioridad")[:5]
                )
            if not eventos:
                return {"texto": "No hay eventos registrados."}
            texto = self._llm_wrap(
                message,
                facts={"eventos": eventos},
            )
            return {"texto": texto, "eventos": eventos}

        if self._is_current_availability_intent(lower):
            if area:
                status_list = get_area_status(area.id)
                if not status_list:
                    return {"texto": "No encontré esa área."}
                info = status_list[0]
                texto = self._llm_wrap(
                    message,
                    facts={
                        "area": info["area"],
                        "libres": info["libres"],
                        "ocupados": info["ocupados"],
                        "total": info["total"],
                    },
                )
                return {"texto": texto, "disponibilidad": info}
            status_list = sorted(
                get_area_status(), key=lambda x: x.get("libres", 0), reverse=True)
            if not status_list:
                return {"texto": "No hay datos de áreas."}
            top = status_list[:3]
            texto = self._llm_wrap(
                message,
                facts={
                    "resumen": [
                        {
                            "area": item["area"],
                            "libres": item["libres"],
                            "total": item["total"],
                        }
                        for item in top
                    ]
                },
            )
            return {"texto": texto, "disponibilidad": top}

        history_lines = self._history_lines(conversation)
        try:
            texto = self._llm_wrap(
                message, facts={"historial": history_lines[-6:]})
        except Exception:
            ml_model = get_ml_chat_model()
            texto = ml_model.respond(message, history_lines)
        return {"texto": texto}

    def _is_prediction_intent(self, text: str) -> bool:
        keywords = ["predec", "predict", "habra",
                    "habrá", "tendra", "tendrá", "futuro", "hora"]
        return any(k in text for k in keywords)

    def _is_current_availability_intent(self, text: str) -> bool:
        keywords = ["disponible", "espacio", "libre", "lugar", "cupo", "hay"]
        return any(k in text for k in keywords)

    def _is_list_areas_intent(self, text: str) -> bool:
        keywords = ["lista", "listar", "muestr", "qué áreas",
                    "que areas", "cuales areas", "qué zonas", "que zonas"]
        return any(k in text for k in keywords)

    def _is_events_intent(self, text: str) -> bool:
        keywords = ["evento", "eventos", "programado",
                    "programados", "agenda", "agenda de eventos"]
        return any(k in text for k in keywords)

    def _is_greeting(self, text: str) -> bool:
        keywords = ["hola", "buenas", "buen dia", "buen día", "hey", "saludos"]
        return any(k in text for k in keywords)

    def _extract_datetime(self, text: str):
        now = timezone.now()
        match = re.search(r"(\d{1,2})(?::(\d{2}))?", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                candidate = now.replace(
                    hour=hour, minute=minute, second=0, microsecond=0)
                if candidate < now:
                    candidate += timedelta(days=1)
                return candidate
        return now + timedelta(hours=1)

    def _history_lines(self, conversation: ChatConversation | None):
        if not conversation:
            return []
        qs = ChatMessage.objects.filter(
            conversation=conversation).order_by("-fecha")[:8]
        lines = []
        for msg in reversed(list(qs)):
            lines.append(msg.mensaje)
            lines.append(msg.respuesta)
        return lines

    def _llm_wrap(self, user_text: str, facts):
        system = (
            "Eres un asistente de estacionamiento. Responde en español, breve (una o dos frases). "
            "No inventes datos: usa solo los datos provistos. Si faltan datos, pide área u hora."
        )
        facts_text = f"Datos: {facts}" if facts else "Sin datos."
        prompt = f"{facts_text}\nPregunta: {user_text}"
        return generate_llm_reply(system, prompt)
