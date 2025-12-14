
# Fakenodo - Zenodo Mock Service


## General Description

Fakenodo is a Flask microservice that simulates the Zenodo API for development and testing. It provides Zenodo-compatible endpoints to create depositions, upload files, publish, and manage versions, without needing to connect to the real Zenodo service.


## Location

- **Main code**: `app/modules/fakenodo/app.py`
- **Tests**: `app/modules/fakenodo/tests/`
- **Dockerfile**: `docker/images/Dockerfile.fakenodo`


## Main Features

### 1. Deposition Management

- **Create depositions**: Generates unique IDs and concept records for each deposition
- **List depositions**: Returns all created depositions
- **Get deposition**: Retrieves information about a specific deposition
- **Update metadata**: Modifies metadata without affecting versions
- **Delete depositions**: Deletes depositions and their associated files

### 2. File Management

- **File upload**: Stores files with safe names
- **File download**: Allows downloading previously uploaded files
- **Fingerprinting**: Hashing system to detect file changes
- **Security validation**: Protection against path traversal

### 3. Versioning System

Fakenodo implements an intelligent versioning system that replicates Zenodo's behavior:

**First publication**: Assigns version 1 and generates the initial DOI
**Republishing without changes**: Keeps the same version and DOI
**Republishing with changes**: Creates a new version with a new DOI, sharing the same concept DOI


### 4. File Persistence

Files are stored in the directory specified by `FAKENODO_FILES_DIR`:

```bash
export FAKENODO_FILES_DIR=/data
```


## API Endpoints

### Health Check
```http
GET /health
```
Checks the service status.

### Depositions

#### List all depositions
```http
GET /api/deposit/depositions
```

#### Create new deposition
```http
POST /api/deposit/depositions
Content-Type: application/json

{
    "metadata": {
        "title": "My Dataset",
        "upload_type": "dataset",
        "description": "Dataset description"
    }
}
```

#### Get specific deposition
```http
GET /api/deposit/depositions/{dep_id}
```

#### Update metadata
```http
PUT /api/deposit/depositions/{dep_id}
Content-Type: application/json

{
    "metadata": {
        "title": "Updated title"
    }
}
```

#### Delete deposition
```http
DELETE /api/deposit/depositions/{dep_id}
```

### Files

#### Upload file
```http
POST /api/deposit/depositions/{dep_id}/files
Content-Type: multipart/form-data

name: archivo.txt
file: <binary data>
```

#### Download file
```http
GET /api/deposit/depositions/{dep_id}/files/{filename}
```

### Publication

#### Publish deposition
```http
POST /api/deposit/depositions/{dep_id}/actions/publish
```

### Versions

#### List versions of a concept
```http
GET /api/records/{conceptid}/versions
```


## Versioning Logic

The versioning system is based on the fingerprint of files:

```python
def files_fingerprint(files):
    h = hashlib.sha256()
    for f in sorted(files, key=lambda x: x["filename"]):
        h.update(f["filename"].encode())
        h.update(str(f["size"]).encode())
    return h.hexdigest()
```


### Publication Cases

1. **First publication** (no previous DOI):
    - Assigns version 1
    - Generates DOI: `10.9999/fakenodo.{concept}.v1`
    - Status: `done`

2. **Republishing with modified files**:
    - Creates a new deposition with a new ID
    - Increments version
    - Generates new DOI: `10.9999/fakenodo.{concept}.v{version+1}`
    - Keeps the same `conceptdoi`

3. **Republishing without changes**:
    - Keeps the same version and DOI
    - Only updates the `modified` field


## Configuration and Deployment

### Environment Variables

```bash
# Service port (required by Render)
export PORT=5001

# Directory to store files
export FAKENODO_FILES_DIR=/data
```

### Deployment on Render

The service is configured to be deployed on Render using Gunicorn:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/modules/fakenodo/app.py /app/app.py

ENV FAKENODO_FILES_DIR=/data
RUN mkdir -p /data

EXPOSE 8000
CMD gunicorn -w 2 -b 0.0.0.0:$PORT app:app
```


**Steps on Render:**
1. Create a new Web Service
2. Connect the repository
3. Configure:
    - Build Command: `pip install -r requirements.txt`
    - Start Command: `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
    - Environment: `FAKENODO_FILES_DIR=/data`
4. Add a persistent disk mounted at `/data`


### Local Execution

```bash
# Direct development
python app/modules/fakenodo/app.py

# With environment variables
PORT=5001 FAKENODO_FILES_DIR=./_fakenodo_files python app/modules/fakenodo/app.py

# With Gunicorn (production)
gunicorn -w 2 -b 0.0.0.0:5001 app:app
```


## Testing

### Integration Tests

Location: `app/modules/fakenodo/tests/test_fakenodo_integration.py`

The integration tests start the service in a subprocess and validate:

- ✅ Full cycle: create → upload → publish → delete
- ✅ Version management with file changes
- ✅ Republishing without changes keeps version
- ✅ Listing versions by concept ID

#### Example test:

```python
def test_roundtrip_create_upload_publish_delete(fakenodo_server, tmp_path):
    # 1) Crear deposición
    create = requests.post(
        FAKENODO_DEPOSITIONS,
        json={"metadata": {"title": "Demo pytest", "upload_type": "dataset"}},
        timeout=10,
    )
    assert create.status_code == 201
    dep = create.json()
    dep_id = dep["id"]

    # 2) Subir archivo
    test_file = tmp_path / "file.txt"
    test_file.write_text("hola fakenodo")
    with open(test_file, "rb") as fh:
        up = requests.post(
            f"{FAKENODO_DEPOSITIONS}/{dep_id}/files",
            data={"name": "file.txt"},
            files={"file": fh},
            timeout=15,
        )
    assert up.status_code == 201

    # 3) Publicar
    pub = requests.post(
        f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish",
        timeout=10
    )
    assert pub.status_code == 202
    assert pub.json().get("doi")

    # 4) Borrar
    delete = requests.delete(f"{FAKENODO_DEPOSITIONS}/{dep_id}", timeout=10)
    assert delete.status_code == 204
```


### Running Tests

```bash
# From the project root directory
pytest app/modules/fakenodo/tests/test_fakenodo_integration.py -v

# With coverage
pytest app/modules/fakenodo/tests/test_fakenodo_integration.py --cov=app.modules.fakenodo --cov-report=html
```


### Fakenodo Server Fixture

The tests use a session fixture that:
- Creates a temporary directory for files
- Starts Fakenodo in a subprocess
- Waits for the service to be ready
- Cleans up resources at the end

```python
@pytest.fixture(scope="session")
def fakenodo_server():
    tmpdir = tempfile.mkdtemp(prefix="fakenodo_files_")
    env = os.environ.copy()
    env["PORT"] = str(FAKENODO_PORT)
    env["FAKENODO_FILES_DIR"] = tmpdir

    proc = subprocess.Popen([sys.executable, app_path], env=env)
    ok = _wait_for_healthy(FAKENODO_DEPOSITIONS, timeout=15.0)

    if not ok:
        proc.terminate()
        proc.wait(timeout=3)
        pytest.fail("fakenodo no arrancó a tiempo")

    yield

    proc.terminate()
    shutil.rmtree(tmpdir, ignore_errors=True)
```


## Logging

Fakenodo includes detailed logging of all operations:

```python
logger.info(f"[FAKENODO] Creating deposition - ID: {dep_id}, ConceptID: {conceptrecid}")
logger.info(f"[FAKENODO] File uploaded - Deposition: {dep_id}, File: {filename}")
logger.info(f"[FAKENODO] First publication - DOI assigned: {doi}, Version: {version}")
```


Log levels:
- **INFO**: Successful operations and normal flow
- **WARNING**: Resources not found
- **ERROR**: I/O operation errors


## Advantages of Using Fakenodo

1. **Offline development**: No internet access required
2. **Fast tests**: No network latency
3. **No limits**: Does not consume Zenodo quota
4. **Reproducibility**: Deterministic behavior
5. **Complex versioning**: Simulates Zenodo's versioning system
6. **Easy debugging**: Detailed logs and accessible code


## Differences with Real Zenodo

- Fake DOIs with format `10.9999/fakenodo.*`
- No validation of complex metadata
- No file processing (thumbnails, previews, etc.)
- No community or collection system
- However, **sufficient for testing and development**


## Integration with ZenodoService

The `ZenodoService` automatically detects if it should use Fakenodo:

```python
def get_zenodo_url(self) -> str:
    # 1) Si hay fakenodo configurado, úsalo
    fakenodo = os.getenv("FAKENODO_URL")
    if fakenodo:
        return fakenodo.rstrip("/")

    # 2) Si no, decide Zenodo por entorno
    FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
    default = "https://sandbox.zenodo.org/api/deposit/depositions"
    if FLASK_ENV == "production":
        default = "https://zenodo.org/api/deposit/depositions"
    return os.getenv("ZENODO_API_URL", default).rstrip("/")
```


To use Fakenodo in development:

```bash
export FAKENODO_URL=http://localhost:5001/api/deposit/depositions
export FLASK_ENV=development
```


## Maintenance and Evolution

### Potential future improvements

- Database persistence (currently in-memory)
- Webhooks for publication notifications
- Search and filtering API
- Stricter metadata validation
- Support for more publication types
- User and permission system


## Conclusion

Fakenodo is an essential tool for the development and testing of Track Hub, providing a complete and functional simulation of the Zenodo API without the limitations and complexities of the real service. Its implementation enables an agile and reliable workflow during development.
