# Fakenodo - Servicio Mock de Zenodo

## Descripción General

Fakenodo es un microservicio Flask que simula la API de Zenodo para desarrollo y testing. Proporciona endpoints compatibles con Zenodo para crear deposiciones, subir archivos, publicar y gestionar versiones, sin necesidad de conectarse al servicio real de Zenodo.

## Ubicación

- **Código principal**: `app/modules/fakenodo/app.py`
- **Tests**: `app/modules/fakenodo/tests/`
- **Dockerfile**: `docker/images/Dockerfile.fakenodo`

## Características Principales

### 1. Gestión de Deposiciones

- **Crear deposiciones**: Genera IDs únicos y concept records para cada deposición
- **Listar deposiciones**: Devuelve todas las deposiciones creadas
- **Obtener deposición**: Recupera información de una deposición específica
- **Actualizar metadatos**: Modifica los metadatos sin afectar versiones
- **Eliminar deposiciones**: Borra deposiciones y sus archivos asociados

### 2. Gestión de Archivos

- **Subida de archivos**: Almacena archivos con nombres seguros
- **Descarga de archivos**: Permite descargar archivos previamente subidos
- **Fingerprinting**: Sistema de hashing para detectar cambios en ficheros
- **Validación de seguridad**: Protección contra path traversal

### 3. Sistema de Versionado

Fakenodo implementa un sistema inteligente de versionado que replica el comportamiento de Zenodo:

- **Primera publicación**: Asigna versión 1 y genera el DOI inicial
- **Republicación sin cambios**: Mantiene la misma versión y DOI
- **Republicación con cambios**: Crea nueva versión con nuevo DOI, compartiendo el mismo concept DOI

### 4. Persistencia de Archivos

Los archivos se almacenan en el directorio especificado por `FAKENODO_FILES_DIR`:

```bash
export FAKENODO_FILES_DIR=/data
```

## Endpoints de la API

### Health Check
```http
GET /health
```
Verifica el estado del servicio.

### Deposiciones

#### Listar todas las deposiciones
```http
GET /api/deposit/depositions
```

#### Crear nueva deposición
```http
POST /api/deposit/depositions
Content-Type: application/json

{
  "metadata": {
    "title": "Mi Dataset",
    "upload_type": "dataset",
    "description": "Descripción del dataset"
  }
}
```

#### Obtener deposición específica
```http
GET /api/deposit/depositions/{dep_id}
```

#### Actualizar metadatos
```http
PUT /api/deposit/depositions/{dep_id}
Content-Type: application/json

{
  "metadata": {
    "title": "Título actualizado"
  }
}
```

#### Eliminar deposición
```http
DELETE /api/deposit/depositions/{dep_id}
```

### Archivos

#### Subir archivo
```http
POST /api/deposit/depositions/{dep_id}/files
Content-Type: multipart/form-data

name: archivo.txt
file: <binary data>
```

#### Descargar archivo
```http
GET /api/deposit/depositions/{dep_id}/files/{filename}
```

### Publicación

#### Publicar deposición
```http
POST /api/deposit/depositions/{dep_id}/actions/publish
```

### Versiones

#### Listar versiones de un concept
```http
GET /api/records/{conceptid}/versions
```

## Lógica de Versionado

El sistema de versionado se basa en el fingerprint de archivos:

```python
def files_fingerprint(files):
    h = hashlib.sha256()
    for f in sorted(files, key=lambda x: x["filename"]):
        h.update(f["filename"].encode())
        h.update(str(f["size"]).encode())
    return h.hexdigest()
```

### Casos de Publicación

1. **Primera publicación** (sin DOI previo):
   - Asigna versión 1
   - Genera DOI: `10.9999/fakenodo.{concept}.v1`
   - Estado: `done`

2. **Republicación con archivos modificados**:
   - Crea nueva deposición con nuevo ID
   - Incrementa versión
   - Genera nuevo DOI: `10.9999/fakenodo.{concept}.v{version+1}`
   - Mantiene el mismo `conceptdoi`

3. **Republicación sin cambios**:
   - Mantiene la misma versión y DOI
   - Actualiza solo el campo `modified`

## Configuración y Despliegue

### Variables de Entorno

```bash
# Puerto del servicio (requerido por Render)
export PORT=5001

# Directorio para almacenar archivos
export FAKENODO_FILES_DIR=/data
```

### Despliegue en Render

El servicio está configurado para desplegarse en Render usando Gunicorn:

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

**Pasos en Render**:
1. Crear nuevo Web Service
2. Conectar repositorio
3. Configurar:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
   - Environment: `FAKENODO_FILES_DIR=/data`
4. Añadir disco persistente montado en `/data`

### Ejecución Local

```bash
# Desarrollo directo
python app/modules/fakenodo/app.py

# Con variables de entorno
PORT=5001 FAKENODO_FILES_DIR=./_fakenodo_files python app/modules/fakenodo/app.py

# Con Gunicorn (producción)
gunicorn -w 2 -b 0.0.0.0:5001 app:app
```

## Testing

### Tests de Integración

Ubicación: `app/modules/fakenodo/tests/test_fakenodo_integration.py`

Los tests de integración arrancan el servicio en un subproceso y validan:

- ✅ Ciclo completo: crear → subir → publicar → eliminar
- ✅ Gestión de versiones con cambios en archivos
- ✅ Republicación sin cambios mantiene versión
- ✅ Listado de versiones por concept ID

#### Ejemplo de test:

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

### Ejecutar Tests

```bash
# Desde el directorio raíz del proyecto
pytest app/modules/fakenodo/tests/test_fakenodo_integration.py -v

# Con cobertura
pytest app/modules/fakenodo/tests/test_fakenodo_integration.py --cov=app.modules.fakenodo --cov-report=html
```

### Fixture de Fakenodo Server

Los tests utilizan una fixture de sesión que:
- Crea un directorio temporal para archivos
- Arranca Fakenodo en un subproceso
- Espera a que el servicio esté listo
- Limpia recursos al finalizar

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

Fakenodo incluye logging detallado de todas las operaciones:

```python
logger.info(f"[FAKENODO] Creating deposition - ID: {dep_id}, ConceptID: {conceptrecid}")
logger.info(f"[FAKENODO] File uploaded - Deposition: {dep_id}, File: {filename}")
logger.info(f"[FAKENODO] First publication - DOI assigned: {doi}, Version: {version}")
```

Niveles de log:
- **INFO**: Operaciones exitosas y flujo normal
- **WARNING**: Recursos no encontrados
- **ERROR**: Errores en operaciones de I/O

## Ventajas de Usar Fakenodo

1. **Desarrollo sin conexión**: No requiere acceso a internet
2. **Tests rápidos**: Sin latencia de red
3. **Sin límites**: No consume cuota de Zenodo
4. **Reproducibilidad**: Comportamiento determinista
5. **Versionado complejo**: Simula el sistema de versiones de Zenodo
6. **Debugging sencillo**: Logs detallados y código accesible

## Diferencias con Zenodo Real

- DOIs ficticios con formato `10.9999/fakenodo.*`
- Sin validación de metadatos complejos
- Sin procesamiento de archivos (thumbnails, previews, etc.)
- Sin sistema de comunidades o colecciones
- Sin embargo, **suficiente para testing y desarrollo**

## Integración con ZenodoService

El servicio `ZenodoService` detecta automáticamente si debe usar Fakenodo:

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

Para usar Fakenodo en desarrollo:

```bash
export FAKENODO_URL=http://localhost:5001/api/deposit/depositions
export FLASK_ENV=development
```

## Mantenimiento y Evolución

### Futuras mejoras potenciales

- Persistencia en base de datos (actualmente en memoria)
- Webhooks para notificaciones de publicación
- API de búsqueda y filtrado
- Validación más estricta de metadatos
- Soporte para más tipos de publicación
- Sistema de usuarios y permisos

## Conclusión

Fakenodo es una herramienta esencial para el desarrollo y testing de Track Hub, proporcionando una simulación completa y funcional de la API de Zenodo sin las limitaciones y complejidades del servicio real. Su implementación permite un flujo de trabajo ágil y confiable durante el desarrollo.
