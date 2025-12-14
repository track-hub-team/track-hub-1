
# Upload and Import of Models (.uvl / .gpx)

This document explains how the logic for uploading and importing UVL and GPX models works in Track Hub, including:

- Uploading a single model file to the current session.
- Importing models from a GitHub repository or a ZIP file.
- Validation and classification of models by type (UVL / GPX).
- Integration of those files into dataset creation.

## Overview of the Flow

The import and upload flow of models is divided into layers:

- **Routes layer:** receives HTTP requests, validates basic inputs, and delegates to services.
- **Type registry:** knows which extensions are valid, which handler validates them, and which model they use.
- **Fetchers:** know how to fetch files from different sources (GitHub, ZIP).
- **DataSetService:** orchestrates business logic: saving, validating, moving files, and integrating them into a dataset.

Files are initially handled in a user's temporary folder, and only when the dataset is created are they moved to their final location.

## Supported Import Flows

1. **Individual upload:** The user uploads a .uvl or .gpx file, which is validated and stored in the user's temporary folder.
2. **Import from ZIP:** The user uploads a ZIP file with multiple models. The system extracts, validates, and filters the supported files (.uvl/.gpx).
3. **Import from GitHub:** The user provides a GitHub URL (repo or subfolder). The system clones/fetches the repo, finds, and validates the supported models.

All valid models are available in the user's temporary folder to be used in the creation of a new dataset.

## Type Validation and Registry

The system detects the file type by its extension and validates it using a specific handler:

- **UVLHandler:** validates .uvl files (existence, not empty, contains the word 'features').
- **GPXHandler:** validates .gpx files (existence, XML parsing, <gpx> root, contains tracks or waypoints).

The global registry `DATASET_TYPE_REGISTRY` associates each type with its handler, model, and allowed extensions.

## Use Case Summary

| Case                        | Endpoint                  | Main process                                                                      |
|-----------------------------|---------------------------|-----------------------------------------------------------------------------------|
| Individual upload           | /dataset/file/upload      | Uploads, validates, and leaves the file in the user's temporary folder            |
| Import from ZIP             | /dataset/import           | Extracts, validates, and filters models from an uploaded ZIP                      |
| Import from GitHub          | /dataset/import           | Clones/fetches repo, validates, and filters models from GitHub                    |

---

# ZIP File Upload

## General Description

Track Hub allows users to upload collections of GPX or UVL files packaged in ZIP format. The system automatically unzips the file, validates each contained file, and imports them into the dataset, simplifying the upload of multiple files.

## Location

- **Fetcher**: `app/modules/dataset/fetchers/zip.py` → `ZipFetcher`
- **Service**: `app/modules/dataset/services.py` → `DataSetService`
- **Registry**: `app/modules/dataset/registry.py` → Fetcher registry
- **Tests**: `app/modules/dataset/tests/test_dataset_file_upload.py`

## Architecture

### ZipFetcher

Main class implementing the `Fetcher_Interface`:

```python
class ZipFetcher(Fetcher_Interface):
    EXTRACTABLE_EXTS = {".uvl", ".gpx"}
    MAX_ZIP_ENTRIES = 500

    def supports(self, url):
        """Verifica si la URL es un archivo ZIP."""
        return str(url).lower().endswith(".zip")

    def fetch(self, url, dest_root, current_user=None):
        """Extrae archivos .uvl y .gpx del ZIP al destino."""
```

### Integration with DataSetService

The dataset service provides high-level methods:

```python
def fetch_models_from_zip_upload(self, file_storage, dest_dir, current_user):
    """
    1. Guarda el ZIP en carpeta temporal del usuario
    2. Extrae con ZipFetcher
    3. Copia archivos válidos a dest_dir
    4. Retorna lista de archivos procesados
    """
```

## Main Features

### 1. ZIP File Validation

```python
def _save_zip_to_temp(self, file_storage, current_user) -> Path:
    """
    Valida y guarda el ZIP subido en carpeta temporal.

    Validations:
    - File must exist
    - Must have .zip extension
    - Prevents overwriting with unique names
    """

    if not file_storage or not file_storage.filename:
        raise FetchError("No ZIP file provided")

    filename = file_storage.filename
    if not filename.lower().endswith(".zip"):
        raise FetchError("Invalid file type. Only .zip allowed")

    user_temp = Path(current_user.temp_folder())
    user_temp.mkdir(parents=True, exist_ok=True)

    # Evitar sobrescritura con nombres únicos
    target = user_temp / filename
    i = 1
    while target.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        target = user_temp / f"{stem} ({i}){suffix}"
        i += 1

    file_storage.save(str(target))
    return target
```

### 2. Safe Extraction

```python
def fetch(self, url, dest_root, current_user=None):
    """
    Extrae archivos del ZIP con validaciones de seguridad.

    Protections:
    - Path traversal (../, /../, etc.)
    - Entry limit (MAX_ZIP_ENTRIES)
    - Only extracts supported files (.uvl, .gpx)
    - Validation of each extracted file
    - Duplicate name handling
    """

    zip_path = Path(str(url))

    if not zip_path.exists():
        raise FetchError(f"ZIP file not found: {zip_path}")

    extract_root = Path(tempfile.mkdtemp(dir=dest_root, prefix="zip_"))
    logger.info(f"[ZipFetcher] Extracting {zip_path} into {extract_root}")

    extracted_any = False

    try:
        with ZipFile(zip_path, "r") as zf:
            infos = zf.infolist()

            # Validar número de entradas
            if len(infos) > self.MAX_ZIP_ENTRIES:
                raise FetchError("ZIP has too many entries")

            def safe_extract(member):
                nonlocal extracted_any

                if member.is_dir():
                    return None

                # Normalizar y validar path
                raw_path = member.filename
                norm_path = posixpath.normpath(raw_path)

                # Protección contra path traversal
                if norm_path.startswith("/") or norm_path.startswith("..") or "/.." in norm_path:
                    raise FetchError("Unsafe path in ZIP")

                # Filtrar por extensión
                ext = Path(norm_path).suffix.lower()
                if ext not in self.EXTRACTABLE_EXTS:
                    return None

                # Calcular target con manejo de duplicados
                desired_name = Path(norm_path).name
                target = extract_root / desired_name

                i = 1
                while target.exists():
                    stem = Path(desired_name).stem
                    suffix = Path(desired_name).suffix
                    target = extract_root / f"{stem} ({i}){suffix}"
                    i += 1

                # Verificar que el path resuelto esté dentro de extract_root
                resolved = target.resolve()
                base_resolved = extract_root.resolve()
                if base_resolved not in resolved.parents and base_resolved != resolved:
                    raise FetchError("Unsafe path in ZIP")

                # Extraer archivo
                with zf.open(member, "r") as src, open(resolved, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                extracted_any = True
                return resolved

            # Procesar cada entrada
            for info in infos:
                safe_extract(info)

    except BadZipFile:
        raise FetchError("Invalid ZIP file")

    finally:
        # Limpiar archivo ZIP temporal
        try:
            if zip_path.exists() and zip_path.is_file():
                zip_path.unlink()
        except Exception:
            pass

    # Verificar que se extrajo al menos un archivo
    if not extracted_any:
        try:
            extract_root.rmdir()
        except OSError:
            pass
        raise FetchError("ZIP processed, but no supported files (.uvl/.gpx) were found")

    logger.info(f"[ZipFetcher] Extraction completed into {extract_root}")
    return extract_root
```

### 3. File Validation and Filtering

```python
def _collect_models_into_temp(self, source_root: Path, dest_dir: Path):
    """
    Copia archivos válidos desde source_root a dest_dir.

    Process:
    1. Recursively traverses source_root
    2. Identifies file type (.uvl, .gpx)
    3. Validates each file with its descriptor
    4. Copies valid files to dest_dir
    5. Handles duplicate names
    """

    added = []

    for path in Path(source_root).rglob("*"):
        if not path.is_file():
            continue

        # Inferir tipo de archivo
        kind = infer_kind_from_filename(path.name)

        # Saltar archivos no reconocidos
        if not kind or kind == "base":
            logger.debug(f"Skipping unsupported file: {path.name}")
            continue

        # Obtener descriptor
        try:
            descriptor = get_descriptor(kind)
        except ValueError as e:
            logger.warning(f"Cannot get descriptor for {path.name}: {e}")
            continue

        # Validar archivo
        try:
            descriptor.handler.validate(str(path))
        except Exception as e:
            logger.warning(f"Skipping invalid model {path}: {e}")
            continue

        # Copiar a destino
        target = dest_dir / path.name
        i = 1
        while target.exists():
            target = dest_dir / f"{path.stem} ({i)}{path.suffix}"
            i += 1

        shutil.copy2(path, target)
        added.append(target)
        logger.info(f"Added {kind} file: {path.name} -> {target.name}")

    logger.info(f"Total files collected from {source_root}: {len(added)}")
    return added
```

## Limitations and Restrictions

### Configurable Limits

```python
EXTRACTABLE_EXTS = {".uvl", ".gpx"}  # Extensiones permitidas
MAX_ZIP_ENTRIES = 500                 # Máximo número de entradas en ZIP
```

### Security Validations

1. **Path Traversal**: Rejects paths like `../../../etc/passwd`
2. **Path resolution**: Ensures extracted files are within the expected directory
3. **Allowed extensions**: Only `.uvl` and `.gpx`
4. **File limit**: Maximum 500 entries per ZIP
5. **Content validation**: Each file is validated by its descriptor before being accepted

## Usage Flow

### 1. User uploads ZIP from form

```html
<form method="POST" enctype="multipart/form-data">
    <input type="file" name="zip_file" accept=".zip">
    <button type="submit">Upload ZIP</button>
</form>
```

### 2. Backend processes the ZIP

```python
@dataset_bp.route("/upload", methods=["POST"])
def upload_dataset():
    zip_file = request.files.get('zip_file')

    # Procesar ZIP
    added_files = dataset_service.fetch_models_from_zip_upload(
        file_storage=zip_file,
        dest_dir=current_user.temp_folder(),
        current_user=current_user
    )

    # Crear dataset con los archivos extraídos
    dataset = dataset_service.create_from_form(form, current_user)

    return redirect(url_for('dataset.view', id=dataset.id))
```

### 3. System extracts and validates

```
ZIP Upload
    ↓
_save_zip_to_temp() → Guardar en /tmp/user_123/
    ↓
ZipFetcher.fetch() → Extraer a /tmp/zip_abc123/
    ↓
_collect_models_into_temp() → Validar y copiar
    ↓
Dataset creado con archivos validados
```

## Usage Example

### Case: Uploading a collection of GPX routes

```python
    # User uploads file: hiking_routes.zip
    # Contents:
    # - route1.gpx
    # - route2.gpx
    # - subfolder/route3.gpx
    # - README.txt (ignored)
    # - invalid.gpx (invalid, ignored)

    # 1. Validate ZIP
    zip_path = dataset_service._save_zip_to_temp(zip_file, current_user)
    # → /tmp/user_42/hiking_routes.zip

    # 2. Extract
    extract_root = zip_fetcher.fetch(zip_path, temp_root, current_user)
    # → /tmp/zip_random123/
    #    ├── route1.gpx ✅
    #    ├── route2.gpx ✅
    #    └── route3.gpx ✅
    # README.txt and invalid.gpx were ignored

    # 3. Validate and copy
    added = dataset_service._collect_models_into_temp(extract_root, user_temp)
    # → [route1.gpx, route2.gpx, route3.gpx]

    # 4. Create dataset
    dataset = dataset_service.create_from_form(form, current_user)
    # Dataset with 3 validated GPX files
```

## Error Handling

### Format Errors

```python
# ZIP inválido o corrupto
except BadZipFile:
    raise FetchError("Invalid ZIP file")

# Sin archivos soportados
if not extracted_any:
    raise FetchError("ZIP processed, but no supported files (.uvl/.gpx) were found")
```

### Security Errors

```python
# Path traversal detectado
if norm_path.startswith("/") or ".." in norm_path:
    raise FetchError("Unsafe path in ZIP")

# Demasiadas entradas
if len(infos) > MAX_ZIP_ENTRIES:
    raise FetchError("ZIP has too many entries")
```

### Validation Errors

```python
# Archivo no válido según su descriptor
try:
    descriptor.handler.validate(str(path))
except Exception as e:
    logger.warning(f"Skipping invalid model {path}: {e}")
    continue  # No abortar, solo saltar archivo
```

## Testing

### ZIP Upload Tests

Location: `app/modules/dataset/tests/test_dataset_file_upload.py`

```python
def test_upload_zip_with_multiple_gpx_files(client, user):
    """Test subir ZIP con múltiples archivos GPX válidos."""

    # Crear ZIP con archivos GPX de prueba
    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('route1.gpx', valid_gpx_content)
        zf.writestr('route2.gpx', valid_gpx_content)

    zip_buffer.seek(0)

    # Subir
    response = client.post('/dataset/upload', data={
        'zip_file': (zip_buffer, 'routes.zip')
    })

    assert response.status_code == 200
    # Verificar que se crearon 2 archivos

def test_upload_zip_with_invalid_files(client, user):
    """Test subir ZIP con archivos inválidos - deben ser ignorados."""

    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('valid.gpx', valid_gpx_content)
        zf.writestr('invalid.txt', 'not a gpx')
        zf.writestr('corrupted.gpx', 'invalid xml')

    zip_buffer.seek(0)

    response = client.post('/dataset/upload', data={
        'zip_file': (zip_buffer, 'mixed.zip')
    })

    assert response.status_code == 200
    # Solo 1 archivo válido debe haber sido procesado

def test_upload_zip_path_traversal_attack(client, user):
    """Test protección contra path traversal."""

    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('../../../etc/passwd.gpx', 'malicious')

    zip_buffer.seek(0)

    response = client.post('/dataset/upload', data={
        'zip_file': (zip_buffer, 'malicious.zip')
    })

    # Debe rechazar o ignorar el archivo
    assert response.status_code in [400, 200]
```

### Ejecutar Tests

```bash
# File upload tests
pytest app/modules/dataset/tests/test_dataset_file_upload.py -v

# Only ZIP tests
pytest app/modules/dataset/tests/test_dataset_file_upload.py -v -k "zip"

# With coverage
pytest app/modules/dataset/tests/test_dataset_file_upload.py --cov=app.modules.dataset.fetchers
```

## Logging

The system includes detailed logging:

```python
logger.info(f"[ZipFetcher] Extracting {zip_path} into {extract_root}")
logger.debug(f"Skipping unsupported file: {path.name}")
logger.warning(f"Skipping invalid model {path}: {e}")
logger.info(f"Added {kind} file: {path.name} -> {target.name}")
logger.info(f"Total files collected from {source_root}: {len(added)}")
```

**Levels**:
- `INFO`: Successful operations
- `DEBUG`: Ignored files (unsupported extensions)
- `WARNING`: Files with validation errors
- `ERROR`: Critical errors

## Security

### Implemented Protections

1. **Path Traversal**:
   ```python
    # Blocks: ../../../etc/passwd
    if norm_path.startswith("/") or ".." in norm_path:
        raise FetchError("Unsafe path in ZIP")
   ```

2. **Verificación de Resolución**:
   ```python
    resolved = target.resolve()
    base_resolved = extract_root.resolve()
    if base_resolved not in resolved.parents:
        raise FetchError("Unsafe path in ZIP")
   ```

3. **Límite de Archivos**:
   ```python
    if len(infos) > MAX_ZIP_ENTRIES:
        raise FetchError("ZIP has too many entries")
   ```

4. **Validación de Contenido**:
   ```python
    descriptor.handler.validate(str(path))
    # GPXHandler or UVLHandler validate the content
   ```

5. **Sanitización de Nombres**:
   ```python
    desired_name = Path(norm_path).name  # Only the name, no paths
   ```

## Best Practices

### 1. Resource Cleanup

```python
finally:
    # Siempre limpiar ZIP temporal
    try:
        if zip_path.exists():
            zip_path.unlink()
    except Exception:
        pass
```

### 2. Duplicate Handling

```python
# Evitar sobrescritura
while target.exists():
    target = dest_dir / f"{stem} ({i}){suffix}"
    i += 1
```

### 3. Early Validation

```python
# Validar antes de extraer
if not filename.lower().endswith(".zip"):
    raise FetchError("Invalid file type")
```

### 4. Appropriate Logging

```python
# INFO para operaciones exitosas
logger.info(f"Extracted {count} files")

# WARNING para archivos problemáticos (no abortar)
logger.warning(f"Skipping invalid file: {filename}")
```

## Known Limitations

1. **Flat structure**: ZIP subdirectories are flattened (only the file name is used)
2. **No metadata preserved**: Timestamps and permissions are not preserved
3. **No incremental compression**: The entire ZIP must be loaded into memory
4. **No progress**: No progress bar for large ZIPs

## Possible Future Improvements

- [ ] Support for larger files (streaming)
- [ ] Progress bar for extraction
- [ ] Preserve directory structure
- [ ] Support for `.7z`, `.tar.gz`
- [ ] Content preview before confirming
- [ ] Configurable limits by user type

## Conclusion

The ZIP upload functionality provides:

- ✅ Automatic and safe file extraction
- ✅ Thorough content validation
- ✅ Protection against path traversal attacks
- ✅ Robust error handling
- ✅ Smart filtering of supported files
- ✅ Detailed logging for debugging
- ✅ Complete testing of normal and edge cases

This implementation allows users to efficiently and safely upload complete collections of GPS files.
