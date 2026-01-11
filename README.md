# EstacionaTESCHI - Documentacion tecnica

## Vision general
- Plataforma de gestion y monitoreo de estacionamientos desarrollada con Django 6 y Django REST Framework.
- Base de datos SQLite para desarrollo; modelos completos en [app/models.py](app/models.py).
- Frontend con plantillas HTML y assets en [app/templates/](app/templates/) y [app/static/](app/static/).
- Servicios de vision computacional para ocupacion de cajones y lectura de placas usando YOLO (ultralytics), OpenCV y Tesseract OCR.
- Chatbot operativo que mezcla reglas, LLM via Ollama y fallback TF-IDF local.

## Arquitectura y modulos
- Enrutamiento raiz en [setup/urls.py](setup/urls.py), delega a rutas web [app/urls.py](app/urls.py) y API [app/api_urls.py](app/api_urls.py).
- **Catalogos y vistas HTML**: vistas por dominio (empleados, usuarios, vehiculos, sanciones, eventos, accesos, etc.) ubicadas en subdirectorios de [app/](app/).
- **Disponibilidad de cajones (API)**: endpoints REST en [app/api_views/availability_view.py](app/api_views/availability_view.py) respaldados por logica en [app/services/availability.py](app/services/availability.py).
- **Deteccion de ocupacion**: servicio en [app/detection/detector_service.py](app/detection/detector_service.py) con streaming/control expuesto en [app/detection/detection_views.py](app/detection/detection_views.py).
- **Deteccion de placas**: servicio en [app/detection/plate_detector_service.py](app/detection/plate_detector_service.py) con streaming/control y registro de accesos en [app/detection/plate_views.py](app/detection/plate_views.py).
- **Chatbot**: orquestado en [app/chatbot/chat_view.py](app/chatbot/chat_view.py) usando reglas de intencion, consultas de disponibilidad/eventos, LLM via [app/services/llm_client.py](app/services/llm_client.py) y fallback ML en [app/services/ml_chat_model.py](app/services/ml_chat_model.py).
- **Notificaciones en tiempo real**: broker en memoria en [app/notification/notification_broker.py](app/notification/notification_broker.py) y vistas asociadas (API/stream) en el modulo `notification`.

## Modelado de datos principal
- `Area`, `Espacio`, `Dispositivo` para topologia fisica y fuentes de video.
- `Usuario`, `Empleado`, `Vehiculo` (con hashing defensivo en `Usuario.save`).
- `Sancion`, `Evento`, `Acceso`, `Notificacion` para operacion y alertas.
- `ChatConversation`, `ChatMessage` para historial del chatbot.

## Flujos clave
- **Monitoreo de cajones**: cliente inicia detector -> YOLO+OpenCV detecta cajones y vehiculos -> mapea IoU a espacios -> actualiza `Espacio.estado` -> stream MJPEG disponible en `/detection/stream/<area_id>/`.
- **Lectura de placas**: cliente inicia detector -> YOLO vehiculos/placas + Tesseract OCR -> ultimo texto disponible via `/plates/status/...` -> `PlateLogAccessView` registra `Acceso`, sugiere cajon libre por area del usuario y genera `Notificacion` emitida por broker.
- **Chat**: POST a `/api/chat/` -> deteccion de intencion (saludos, lista de areas, disponibilidad, prediccion, eventos) -> consultas a servicios -> respuesta generada con LLM (Ollama) o fallback TF-IDF -> persistencia en BD.

## Heuristicas y decisiones tecnicas
- **Disponibilidad y prediccion**: calculo de libres/ocupados via anotaciones ORM; probabilidad futura basada en proporcion actual con decaimiento temporal (ver [app/services/availability.py](app/services/availability.py)).
- **Deteccion de cajones**: combinacion de deteccion de lineas Hough, agrupamiento y grilla adaptativa cuando no hay marcas; consolidacion de spots en fase de calibracion.
- **Deteccion de placas**: dos modelos YOLO (vehiculo y placa) con recorte seguro y OCR; evita procesar cada frame para eficiencia.
- **Resiliencia de captura**: reintentos si la camara se cae; locks sobre frames para acceso concurrente; hilos por detector.
- **Chat hibrido**: reglas + LLM con contexto limitado; fallback TF-IDF si falla el servicio LLM.
- **Notificaciones**: broker en memoria con filtrado opcional por usuario; disparos en `transaction.on_commit` para coherencia tras escritura.

## Dependencias y modelos de IA
- Requerimientos en [requirements.txt](requirements.txt): Django 6, djangorestframework, ultralytics, opencv-python, numpy, Pillow, pytesseract, scikit-learn, ollama.
- Pesos incluidos en [models/](models/) (`yolov10n.pt`, `yolov10s.pt`, `placa.pt`). `LLM_MODEL` configurable (defecto `llama3.1:8b`). `TESSERACT_CMD` permite fijar binario de Tesseract.

## Configuracion y convenciones
- Ajustes centrales en [setup/settings.py](setup/settings.py): idioma `es`, zona horaria UTC, renderer/parser JSON por defecto para DRF, assets en `app/static` y `STATIC_ROOT` en `staticfiles`.
- Base de datos por defecto SQLite `db.sqlite3` (override via `DATABASES` en entorno si se requiere otro motor).
- Endpoints JSON no requieren autenticacion en los modulos mostrados; agregar permisos segun despliegue.

## Desarrollo rapido (sin pasos de despliegue detallados)
- Instalar dependencias de Python 3.11+ con `pip install -r requirements.txt`.
- Ejecutar migraciones y cargar pesos YOLO en carpeta `models/`.
- Para deteccion, proveer rutas de camara (archivo, RTSP/HTTP) en `Dispositivo.ruta` o via query `ip` para las vistas `by_ip`.
- Para chatbot, iniciar servicio Ollama local con el modelo configurado.

## Riesgos y pendientes
- Falta suite de pruebas automatizadas; flujos de CV y OCR requieren hardware/camaras reales para validar end-to-end.
- Seguridad y autenticacion: vistas de control/stream y API publicas requieren endurecimiento antes de produccion (auth, rate limiting, CORS).
- Escalamiento: broker de notificaciones en memoria no es distribuido; considerar Redis/WS para produccion.
