
# Zenodo Integration


## General Description

The Zenodo module of Track Hub provides full integration with the Zenodo platform to publish datasets and obtain permanent DOIs. It includes support for development via Fakenodo, a mock service that simulates the Zenodo API.


## Location

- **Service**: `app/modules/zenodo/services.py`
- **Routes**: `app/modules/zenodo/routes.py`
- **Repository**: `app/modules/zenodo/repositories.py`
- **Forms**: `app/modules/zenodo/forms.py`
- **Models**: `app/modules/zenodo/models.py`
- **Templates**: `app/modules/zenodo/templates/zenodo/`
- **Tests**: `app/modules/fakenodo/tests/test_zenodo_service_unit.py`


## Architecture

### ZenodoService

Main class that manages communication with Zenodo/Fakenodo:

```python
class ZenodoService(BaseService):
    def __init__(self):
        super().__init__(ZenodoRepository())
        self.ZENODO_ACCESS_TOKEN = self.get_zenodo_access_token()
        self.ZENODO_API_URL = self.get_zenodo_url()
        self.headers = {"Content-Type": "application/json"}
```


## Configuration

### Environment Variables

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


### `.env.example` file

Location: `app/modules/zenodo/.env.example`

```bash
ZENODO_ACCESS_TOKEN=your_zenodo_access_token_here
FAKENODO_URL=http://localhost:5001/api/deposit/depositions
```


### Backend Selection Logic

The service automatically selects the correct backend:

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


## Main Features

### 1. Connection Test


#### Simple Test
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


#### Full Test (E2E)
```python
def test_full_connection(self) -> Response:
    """
    Test end-to-end: crea deposición, sube archivo, elimina.
    Devuelve JSON con resultado y mensajes.
    """
```


**Full test flow**:
1. Creates temporary file `test_file.txt`
2. Creates new deposition
3. Uploads the file
4. Deletes the deposition
5. Cleans up temporary file
6. Returns result with `success` and `messages`

**Endpoint**: `GET /zenodo/test`


### 2. Create Deposition

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


### 3. Upload File

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


### 4. Publish Deposition

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


### 5. Get DOI

```python
def get_doi(self, deposition_id: int) -> str:
    """Obtiene el DOI de una deposición publicada."""
    return self.get_deposition(deposition_id).get("doi")
```


### 6. List Depositions

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


## HTTP Endpoints

### GET /zenodo
Renders the main page of the Zenodo module.

```python
@zenodo_bp.route("/zenodo", methods=["GET"])
def index():
    return render_template("zenodo/index.html")
```


### GET /zenodo/test
Runs the full connection test.

**Successful response**:
```json
{
  "success": true,
  "messages": []
}
```


**Error response**:
```json
{
  "success": false,
  "messages": ["Failed to create test deposition (network error)."]
}
```


### GET /zenodo/demo
Visual demo of the full Zenodo flow.

**Response**:
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


## Deployment on Render

### Main Service Configuration

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


### Fakenodo Configuration on Render

1. **Crear nuevo Web Service**:
   - Name: `track-hub-fakenodo`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `cd app/modules/fakenodo && gunicorn -w 2 -b 0.0.0.0:$PORT app:app`


2. **Environment variables**:
   ```
   FAKENODO_FILES_DIR=/data
   ```


3. **Persistent disk**:
    - Mount Path: `/data`
    - Size: 1GB (adjust as needed)


4. **Health Check**:
    - Path: `/health`
    - Initial Delay: 30s


### Production Configuration with Real Zenodo


1. Obtain Zenodo token:
    - Go to https://zenodo.org/account/settings/applications/tokens/new/
    - Scopes: `deposit:actions`, `deposit:write`


2. Configure in Render:
   ```bash
   ZENODO_API_URL=https://zenodo.org/api/deposit/depositions
   ZENODO_ACCESS_TOKEN=<tu_token_real>
   FLASK_ENV=production
   ```


3. **DO NOT set** `FAKENODO_URL` in production


### Testing in Sandbox

For intermediate testing (before production):

```bash
ZENODO_API_URL=https://sandbox.zenodo.org/api/deposit/depositions
ZENODO_ACCESS_TOKEN=<tu_token_sandbox>
FLASK_ENV=development
```


**Sandbox advantages**:
- Real DOIs but in a test environment
- No impact on production records
- Resettable when needed
- Identical to production in behavior


## Testing

### Unit Tests

Location: `app/modules/fakenodo/tests/test_zenodo_service_unit.py`


#### Successful Connection Test

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


#### Graceful Failure Test

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


### Testing Fixtures

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


### Run Tests

```bash
# Zenodo service unit tests
pytest app/modules/fakenodo/tests/test_zenodo_service_unit.py -v

# With coverage
pytest app/modules/fakenodo/tests/test_zenodo_service_unit.py --cov=app.modules.zenodo --cov-report=html

# All Zenodo and Fakenodo tests
pytest app/modules/fakenodo/tests/ -v
```


## Logging

The module includes detailed logging:

```python
logger.info("[ZENODO] Dataset sending to Zenodo...")
logger.info("[ZENODO] Publication type: %s", dataset.ds_meta_data.publication_type.value)
logger.info("[ZENODO] Building metadata...")
logger.info(f"[ZENODO] Posting to {self.ZENODO_API_URL}")
logger.info(f"[ZENODO] Response status: {response.status_code}")
logger.info("[ZENODO] Deposition created successfully")
```


**Levels**:
- `INFO`: Normal operations
- `ERROR`: Request errors
- `EXCEPTION`: Exceptions with full traceback


## Complete Publication Flow

### 1. User uploads dataset to Track Hub
```
Usuario → Upload form → DatasetService → Database
```


### 2. User requests publication to Zenodo
```
Usuario → "Publish to Zenodo" → ZenodoService.create_new_deposition()
```


### 3. Deposition is created with metadata
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


### 4. GPX files are uploaded
```python
for feature_model in dataset.feature_models:
    ZenodoService.upload_file(dataset, deposition_id, feature_model)
```


### 5. It is published and DOI is obtained
```python
result = ZenodoService.publish_deposition(deposition_id)
doi = result["doi"]  # e.g., "10.5281/zenodo.1234567"
```


### 6. DOI is saved in the dataset
```python
dataset.ds_meta_data.doi = doi
db.session.commit()
```


## Error Handling

### Connection Errors
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


### HTTP Errors
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


### File Errors
```python
try:
    with open(file_path, "rb") as fh:
        ...
except FileNotFoundError:
    raise Exception(f"File not found: {file_path}")
except PermissionError:
    raise Exception(f"Cannot read file: {file_path}")
```


## Best Practices

### 1. Local Development
- Always use **Fakenodo** in local development
- Do not waste Zenodo quota unnecessarily
- Fast tests without network latency

### 2. Testing in CI/CD
- Use Fakenodo in GitHub Actions
- Alternatively, use Zenodo Sandbox
- Never use production in automated tests

### 3. Staging
- Use **Zenodo Sandbox** in staging
- Allows testing with real DOIs (but test only)
- Resettable if needed

### 4. Production
- Use **real Zenodo** only in production
- Protect the token as a secret
- Monitor quota and rate limits


## Troubleshooting

### Error: "FAKENODO_URL not set"
**Solution**: Start Fakenodo or set the variable:
```bash
export FAKENODO_URL=http://localhost:5001/api/deposit/depositions
```


### Error: "Invalid access token"
**Solution**: Check token in environment variables:
```bash
echo $ZENODO_ACCESS_TOKEN
```


### Error: "Failed to create deposition"
**Possible causes**:
- Invalid or expired token
- Incomplete or invalid metadata
- Network problems with Zenodo

**Debugging**:
```python
logger.setLevel(logging.DEBUG)
```


### Fakenodo does not start in tests
**Solution**: Check that `app/modules/fakenodo/app.py` exists:
```bash
ls -la app/modules/fakenodo/app.py
```


## Recommended Deployment Architecture

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


## Conclusion

The integration with Zenodo provides a robust solution for publishing datasets with permanent DOIs. The use of Fakenodo enables agile development and reliable testing without external dependencies, while support for Zenodo Sandbox and production ensures a smooth transition between environments.

This flexible architecture ensures:
- ✅ Fast offline development
- ✅ Reliable automated testing
- ✅ Realistic staging with test DOIs
- ✅ Production with official permanent DOIs
