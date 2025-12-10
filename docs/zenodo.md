# Integración con Zenodo

## Descripción General

El módulo Zenodo de Track Hub proporciona integración completa con la plataforma Zenodo para publicar datasets y obtener DOIs permanentes. Incluye soporte para desarrollo mediante Fakenodo, un servicio mock que simula la API de Zenodo.

## Ubicación

- **Servicio**: `app/modules/zenodo/services.py`
- **Rutas**: `app/modules/zenodo/routes.py`
- **Repositorio**: `app/modules/zenodo/repositories.py`
- **Formularios**: `app/modules/zenodo/forms.py`
- **Modelos**: `app/modules/zenodo/models.py`
- **Templates**: `app/modules/zenodo/templates/zenodo/`
- **Tests**: `app/modules/fakenodo/tests/test_zenodo_service_unit.py`

## Arquitectura

### ZenodoService

Clase principal que gestiona la comunicación con Zenodo/Fakenodo:

```python
class ZenodoService(BaseService):
    def __init__(self):
        super().__init__(ZenodoRepository())
        self.ZENODO_ACCESS_TOKEN = self.get_zenodo_access_token()
        self.ZENODO_API_URL = self.get_zenodo_url()
        self.headers = {"Content-Type": "application/json"}
```

## Configuración

### Variables de Entorno

```bash
# Desarrollo con Fakenodo
FAKENODO_URL=http://localhost:5001/api/deposit/depositions
FLASK_ENV=development

# Sandbox de Zenodo (testing)
ZENODO_API_URL=https://sandbox.zenodo.org/api/deposit/depositions
ZENODO_ACCESS_TOKEN=tu_token_sandbox

# Producción con Zenodo real
ZENODO_API_URL=https://zenodo.org/api/deposit/depositions
ZENODO_ACCESS_TOKEN=tu_token_produccion
FLASK_ENV=production
```

### Archivo `.env.example`

Ubicación: `app/modules/zenodo/.env.example`

```bash
ZENODO_ACCESS_TOKEN=your_zenodo_access_token_here
FAKENODO_URL=http://localhost:5001/api/deposit/depositions
```

### Lógica de Selección de Backend

El servicio selecciona automáticamente el backend correcto:

```python
def get_zenodo_url(self) -> str:
    # 1) Prioridad: FAKENODO_URL (desarrollo/testing)
    fakenodo = os.getenv("FAKENODO_URL")
    if fakenodo:
        return fakenodo.rstrip("/")

    # 2) Si no hay Fakenodo, usa Zenodo según entorno
    FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()

    # Sandbox por defecto en desarrollo
    default = "https://sandbox.zenodo.org/api/deposit/depositions"

    # Zenodo real en producción
    if FLASK_ENV == "production":
        default = "https://zenodo.org/api/deposit/depositions"

    # Permite override con ZENODO_API_URL
    return os.getenv("ZENODO_API_URL", default).rstrip("/")
```

## Funcionalidades Principales

### 1. Test de Conexión

#### Test Simple
```python
def test_connection(self) -> bool:
    """Verifica conectividad básica con Zenodo/Fakenodo."""
    try:
        response = requests.get(
            self.ZENODO_API_URL,
            params=self._params(),
            headers=self.headers,
            timeout=30
        )
        return response.status_code == 200
    except Exception as exc:
        logger.exception("Zenodo test_connection failed: %s", exc)
        return False
```

#### Test Completo (E2E)
```python
def test_full_connection(self) -> Response:
    """
    Test end-to-end: crea deposición, sube archivo, elimina.
    Devuelve JSON con resultado y mensajes.
    """
```

**Flujo del test completo**:
1. Crea archivo temporal `test_file.txt`
2. Crea nueva deposición
3. Sube el archivo
4. Elimina la deposición
5. Limpia archivo temporal
6. Retorna resultado con `success` y `messages`

**Endpoint**: `GET /zenodo/test`

### 2. Crear Deposición

```python
def create_new_deposition(self, dataset: BaseDataset) -> dict:
    """Crea deposición usando metadatos del DataSet."""

    metadata = {
        "title": dataset.ds_meta_data.title,
        "upload_type": "dataset" if dataset.ds_meta_data.publication_type.value == "none" else "publication",
        "publication_type": dataset.ds_meta_data.publication_type.value,
        "description": dataset.ds_meta_data.description,
        "creators": [
            {
                "name": author.name,
                **({"affiliation": author.affiliation} if author.affiliation else {}),
                **({"orcid": author.orcid} if author.orcid else {}),
            }
            for author in dataset.ds_meta_data.authors
        ],
        "keywords": dataset.ds_meta_data.tags.split(", ") + ["uvlhub"],
        "access_right": "open",
        "license": "CC-BY-4.0",
    }

    data = {"metadata": metadata}
    response = requests.post(
        self.ZENODO_API_URL,
        params=self._params(),
        json=data,
        headers=self.headers,
        timeout=30
    )

    if response.status_code != 201:
        raise Exception(f"Failed to create deposition. Status: {response.status_code}")

    return response.json()
```

### 3. Subir Archivo

```python
def upload_file(self, dataset: BaseDataset, deposition_id: int,
                feature_model: FeatureModel, user=None) -> dict:
    """Sube un archivo a una deposición existente."""

    filename = feature_model.fm_meta_data.filename
    user_id = current_user.id if user is None else user.id
    file_path = os.path.join(
        uploads_folder_name(),
        f"user_{str(user_id)}",
        f"dataset_{dataset.id}/",
        filename
    )

    publish_url = f"{self.ZENODO_API_URL}/{deposition_id}/files"

    with open(file_path, "rb") as fh:
        files = {"file": fh}
        data = {"name": filename}
        response = requests.post(
            publish_url,
            params=self._params(),
            data=data,
            files=files,
            timeout=60
        )

    if response.status_code != 201:
        raise Exception(f"Failed to upload files. Error: {response.json()}")

    return response.json()
```

### 4. Publicar Deposición

```python
def publish_deposition(self, deposition_id: int) -> dict:
    """Publica una deposición y obtiene el DOI."""

    publish_url = f"{self.ZENODO_API_URL}/{deposition_id}/actions/publish"
    response = requests.post(
        publish_url,
        params=self._params(),
        headers=self.headers,
        timeout=30
    )

    if response.status_code != 202:
        raise Exception("Failed to publish deposition")

    return response.json()
```

### 5. Obtener DOI

```python
def get_doi(self, deposition_id: int) -> str:
    """Obtiene el DOI de una deposición publicada."""
    return self.get_deposition(deposition_id).get("doi")
```

### 6. Listar Deposiciones

```python
def get_all_depositions(self) -> dict:
    """Lista todas las deposiciones del usuario."""
    response = requests.get(
        self.ZENODO_API_URL,
        params=self._params(),
        headers=self.headers,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception("Failed to get depositions")

    return response.json()
```

## Endpoints HTTP

### GET /zenodo
Renderiza la página principal del módulo Zenodo.

```python
@zenodo_bp.route("/zenodo", methods=["GET"])
def index():
    return render_template("zenodo/index.html")
```

### GET /zenodo/test
Ejecuta test completo de conexión.

**Respuesta exitosa**:
```json
{
  "success": true,
  "messages": []
}
```

**Respuesta con error**:
```json
{
  "success": false,
  "messages": ["Failed to create test deposition (network error)."]
}
```

### GET /zenodo/demo
Demo visual del flujo completo de Zenodo.

**Respuesta**:
```json
{
  "success": true,
  "steps": [
    {
      "name": "Create Deposition",
      "method": "POST",
      "url": "https://sandbox.zenodo.org/api/deposit/depositions",
      "status": 201,
      "ok": true,
      "payload": { "id": 12345, ... }
    },
    {
      "name": "Upload File",
      "method": "POST",
      "url": "https://sandbox.zenodo.org/api/deposit/depositions/12345/files",
      "status": 201,
      "ok": true
    },
    ...
  ]
}
```

## Despliegue en Render

### Configuración del Servicio Principal

**render.yaml** (ejemplo):
```yaml
services:
  - type: web
    name: track-hub
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: ZENODO_ACCESS_TOKEN
        sync: false
      - key: FAKENODO_URL
        value: https://tu-fakenodo.onrender.com/api/deposit/depositions
      - key: FLASK_ENV
        value: production
```

### Configuración de Fakenodo en Render

1. **Crear nuevo Web Service**:
   - Name: `track-hub-fakenodo`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `cd app/modules/fakenodo && gunicorn -w 2 -b 0.0.0.0:$PORT app:app`

2. **Variables de entorno**:
   ```
   FAKENODO_FILES_DIR=/data
   ```

3. **Disco persistente**:
   - Mount Path: `/data`
   - Size: 1GB (ajustar según necesidad)

4. **Health Check**:
   - Path: `/health`
   - Initial Delay: 30s

### Configuración para Producción con Zenodo Real

1. Obtener token de Zenodo:
   - Ir a https://zenodo.org/account/settings/applications/tokens/new/
   - Scopes: `deposit:actions`, `deposit:write`

2. Configurar en Render:
   ```bash
   ZENODO_API_URL=https://zenodo.org/api/deposit/depositions
   ZENODO_ACCESS_TOKEN=<tu_token_real>
   FLASK_ENV=production
   ```

3. **NO configurar** `FAKENODO_URL` en producción

### Testing en Sandbox

Para testing intermedio (antes de producción):

```bash
ZENODO_API_URL=https://sandbox.zenodo.org/api/deposit/depositions
ZENODO_ACCESS_TOKEN=<tu_token_sandbox>
FLASK_ENV=development
```

**Ventajas del Sandbox**:
- DOIs reales pero en entorno de prueba
- Sin impacto en registros de producción
- Reseteable cuando sea necesario
- Idéntico a producción en comportamiento

## Testing

### Tests Unitarios

Ubicación: `app/modules/fakenodo/tests/test_zenodo_service_unit.py`

#### Test de Conexión Exitosa

```python
def test_test_full_connection_success(env_ok):
    """Debe devolver success=True con fakenodo corriendo."""
    app = Flask(__name__)
    with app.app_context():
        svc = ZenodoService()
        resp = svc.test_full_connection()
        payload = resp.get_json()

        assert resp.status_code == 200
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert "messages" in payload
```

#### Test de Fallo Graceful

```python
def test_test_full_connection_fails_gracefully(env_fail):
    """Debe fallar de forma controlada si Fakenodo no está disponible."""
    app = Flask(__name__)
    with app.app_context():
        svc = ZenodoService()
        resp = svc.test_full_connection()
        payload = resp.get_json()

        assert resp.status_code == 200
        assert payload.get("success") is False
        assert len(payload.get("messages", [])) > 0
```

### Fixtures de Testing

```python
@pytest.fixture
def env_ok(monkeypatch, fakenodo_server):
    """Configura entorno para usar Fakenodo real."""
    monkeypatch.setenv("FAKENODO_URL", FAKENODO_DEPOSITIONS)
    monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "dummy")
    monkeypatch.setenv("FLASK_ENV", "development")

@pytest.fixture
def env_fail(monkeypatch):
    """Configura endpoint inválido SIN arrancar Fakenodo."""
    monkeypatch.setenv("FAKENODO_URL", "http://localhost:9999/api/deposit/depositions")
    monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "dummy")
    monkeypatch.setenv("FLASK_ENV", "development")
```

### Ejecutar Tests

```bash
# Tests unitarios del servicio Zenodo
pytest app/modules/fakenodo/tests/test_zenodo_service_unit.py -v

# Con cobertura
pytest app/modules/fakenodo/tests/test_zenodo_service_unit.py --cov=app.modules.zenodo --cov-report=html

# Todos los tests de Zenodo y Fakenodo
pytest app/modules/fakenodo/tests/ -v
```

## Logging

El módulo incluye logging detallado:

```python
logger.info("[ZENODO] Dataset sending to Zenodo...")
logger.info("[ZENODO] Publication type: %s", dataset.ds_meta_data.publication_type.value)
logger.info("[ZENODO] Building metadata...")
logger.info(f"[ZENODO] Posting to {self.ZENODO_API_URL}")
logger.info(f"[ZENODO] Response status: {response.status_code}")
logger.info("[ZENODO] Deposition created successfully")
```

**Niveles**:
- `INFO`: Operaciones normales
- `ERROR`: Errores en requests
- `EXCEPTION`: Excepciones con traceback completo

## Flujo Completo de Publicación

### 1. Usuario sube dataset a Track Hub
```
Usuario → Upload form → DatasetService → Database
```

### 2. Usuario solicita publicación en Zenodo
```
Usuario → "Publish to Zenodo" → ZenodoService.create_new_deposition()
```

### 3. Se crea deposición con metadatos
```python
metadata = {
    "title": "GPS Track Collection - Mountain Routes",
    "upload_type": "dataset",
    "description": "Collection of mountain hiking routes...",
    "creators": [{"name": "John Doe", "affiliation": "University"}],
    "keywords": ["GPS", "GPX", "hiking", "uvlhub"],
    "access_right": "open",
    "license": "CC-BY-4.0"
}
```

### 4. Se suben archivos GPX
```python
for feature_model in dataset.feature_models:
    ZenodoService.upload_file(dataset, deposition_id, feature_model)
```

### 5. Se publica y obtiene DOI
```python
result = ZenodoService.publish_deposition(deposition_id)
doi = result["doi"]  # e.g., "10.5281/zenodo.1234567"
```

### 6. DOI se guarda en el dataset
```python
dataset.ds_meta_data.doi = doi
db.session.commit()
```

## Manejo de Errores

### Errores de Conexión
```python
try:
    response = requests.post(url, ...)
except requests.exceptions.ConnectionError:
    logger.error("Cannot connect to Zenodo")
    raise Exception("Connection failed")
except requests.exceptions.Timeout:
    logger.error("Request timeout")
    raise Exception("Request timeout")
```

### Errores HTTP
```python
if response.status_code == 400:
    raise Exception("Invalid metadata")
elif response.status_code == 401:
    raise Exception("Invalid access token")
elif response.status_code == 404:
    raise Exception("Deposition not found")
elif response.status_code >= 500:
    raise Exception("Zenodo server error")
```

### Errores de Archivo
```python
try:
    with open(file_path, "rb") as fh:
        ...
except FileNotFoundError:
    raise Exception(f"File not found: {file_path}")
except PermissionError:
    raise Exception(f"Cannot read file: {file_path}")
```

## Mejores Prácticas

### 1. Desarrollo Local
- Usar **Fakenodo** siempre en desarrollo local
- No gastar cuota de Zenodo innecesariamente
- Tests rápidos sin latencia de red

### 2. Testing en CI/CD
- Usar Fakenodo en GitHub Actions
- Alternativamente, usar Sandbox de Zenodo
- Nunca usar producción en tests automáticos

### 3. Staging
- Usar **Sandbox de Zenodo** en staging
- Permite testing con DOIs reales (pero de prueba)
- Reseteable si es necesario

### 4. Producción
- Usar **Zenodo real** únicamente en producción
- Proteger el token como secreto
- Monitorizar cuota y límites de rate

## Troubleshooting

### Error: "FAKENODO_URL not set"
**Solución**: Arrancar Fakenodo o configurar variable:
```bash
export FAKENODO_URL=http://localhost:5001/api/deposit/depositions
```

### Error: "Invalid access token"
**Solución**: Verificar token en variables de entorno:
```bash
echo $ZENODO_ACCESS_TOKEN
```

### Error: "Failed to create deposition"
**Causas posibles**:
- Token inválido o expirado
- Metadatos incompletos o inválidos
- Problemas de red con Zenodo

**Debugging**:
```python
logger.setLevel(logging.DEBUG)
```

### Fakenodo no arranca en tests
**Solución**: Verificar que existe `app/modules/fakenodo/app.py`:
```bash
ls -la app/modules/fakenodo/app.py
```

## Arquitectura de Despliegue Recomendada

```
┌─────────────────────────────────────────────┐
│           PRODUCCIÓN (Render)               │
├─────────────────────────────────────────────┤
│  Track Hub App                              │
│  ├─ ZENODO_API_URL=zenodo.org              │
│  ├─ ZENODO_ACCESS_TOKEN=<secret>           │
│  └─ FLASK_ENV=production                    │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│            STAGING (Render)                 │
├─────────────────────────────────────────────┤
│  Track Hub App                              │
│  ├─ ZENODO_API_URL=sandbox.zenodo.org      │
│  ├─ ZENODO_ACCESS_TOKEN=<sandbox_token>    │
│  └─ FLASK_ENV=development                   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│          DESARROLLO LOCAL                   │
├─────────────────────────────────────────────┤
│  Track Hub App                              │
│  ├─ FAKENODO_URL=localhost:5001            │
│  └─ FLASK_ENV=development                   │
│                                             │
│  Fakenodo (Puerto 5001)                    │
│  └─ FAKENODO_FILES_DIR=./_fakenodo_files   │
└─────────────────────────────────────────────┘
```

## Conclusión

La integración con Zenodo proporciona una solución robusta para publicación de datasets con DOIs permanentes. El uso de Fakenodo permite un desarrollo ágil y testing confiable sin dependencias externas, mientras que el soporte para Sandbox y producción de Zenodo garantiza una transición suave entre entornos.

Esta arquitectura flexible asegura:
- ✅ Desarrollo rápido sin conexión
- ✅ Testing automatizado confiable
- ✅ Staging realista con DOIs de prueba
- ✅ Producción con DOIs permanentes oficiales
