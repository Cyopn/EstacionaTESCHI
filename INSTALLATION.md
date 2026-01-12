# Guia de instalacion y ejecucion

## Prerrequisitos
- Python 3.11+ recomendado.
- Pip reciente (`python -m pip install --upgrade pip`).
- Tesseract OCR instalado en el sistema (binario accesible en PATH); si no, define `TESSERACT_CMD` apuntando al ejecutable.
- (Opcional) FFmpeg/GStreamer si usaras streams RTSP/HTTP para deteccion.
- Espacio para modelos: carpeta `models/` ya incluye `yolov10n.pt`, `yolov10s.pt`, `placa.pt`.

## Clonado y entorno
```bash
git clone https://github.com/Cyopn/EstacionaTESCHI.git
cd EstacionaTESCHI
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\\Scripts\\activate
```

## Dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
Dependencias clave:
- Django 6 + DRF
- Vision: ultralytics, opencv-python, Pillow, numpy, pytesseract
- ML local: scikit-learn
- LLM cliente: ollama
- Carga/estrés: locust

## Variables de entorno mas usadas
- `DJANGO_ALLOWED_HOSTS`: lista separada por comas; por defecto `*`.
- `TESSERACT_CMD`: ruta al binario de Tesseract (si no esta en PATH).
- `LLM_MODEL`: modelo de Ollama (defecto `llama3.1:8b`).
- `STRESS_PLATE`: placa existente para evitar 404 en pruebas de log_access (defecto `ABC123`).
- `STRESS_RUN_SECONDS`: duracion de ejecucion en pruebas de carga headless (si se usa modo headless). Por defecto, controla via CLI con `-t`.

## Base de datos
SQLite se usa por defecto. Para entorno limpio:
```bash
python manage.py migrate
```
Si cambias de motor, ajusta `DATABASES` via variables de entorno o edita `setup/settings.py`.

## Archivos estaticos
En desarrollo no necesitas `collectstatic`. Para produccion:
```bash
python manage.py collectstatic
```

## Servidor de desarrollo
```bash
python manage.py runserver 0.0.0.0:8000
```
Endpoints principales:
- Web: `/` (root), `/login/`, `/entry/`, etc. (ver rutas en app/urls.py).
- API disponibilidad: `/api/availability/`, `/api/availability/<area_id>/`.
- Placas: `/plates/lookup/`, `/plates/log_access/`.

## Pruebas unitarias e integracion
```bash
python manage.py test app.tests
```

## Pruebas de estres con Locust
Archivo: `app/tests_stress.py`

Ejecutar UI (seleccionar escenarios en la web):
```bash
locust -f app/tests_stress.py --host http://localhost:8000
```
Ejecutar un solo escenario por tag (headless 25s de ejemplo):
```bash
# Disponibilidad
locust -f app/tests_stress.py --host http://localhost:8000 --tags availability --headless -u 20 -r 5 -t 25s

# Lookup de placas
locust -f app/tests_stress.py --host http://localhost:8000 --tags lookup --headless -u 20 -r 5 -t 25s

# Registro de acceso (define una placa existente)
STRESS_PLATE=ABC123 locust -f app/tests_stress.py --host http://localhost:8000 --tags log_access --headless -u 20 -r 5 -t 25s
```
Notas:
- Usa placas existentes en BD para evitar 404 en `log_access`.
- Ajusta `-u` (usuarios), `-r` (rampa), `-t` (duracion) segun tu carga objetivo.

## Ollama (opcional para chatbot)
Instala Ollama y descarga el modelo configurado (ej. `ollama pull llama3.1:8b`). Ejecuta el daemon de Ollama local antes de usar el chatbot.

## Consideraciones de deteccion (CV)
- Aporta rutas de camara en `Dispositivo.ruta` o via query `ip` para vistas `by_ip`.
- Verifica dependencias del SO para OpenCV (libgl1 en Linux, etc.).

## Solucion de problemas rapida
- 404 en `/plates/log_access/`: verifica que el servidor este corriendo y el host sea correcto (`--host http://localhost:8000`); usa una placa existente (`STRESS_PLATE`).
- Error de Tesseract: fija `TESSERACT_CMD` a la ruta del ejecutable.
- Faltan modelos: confirma que `models/` contiene los pesos `.pt` o coloca los archivos requeridos.
- ImportError de ultralytics/opencv: reinstala requirements y revisa dependencias del SO.
