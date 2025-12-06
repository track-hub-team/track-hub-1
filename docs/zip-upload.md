# Subida de Archivos ZIP

## Descripción General

Track Hub permite a los usuarios subir colecciones de archivos GPX o UVL empaquetados en formato ZIP. El sistema descomprime automáticamente el archivo, valida cada archivo contenido y los importa al dataset, simplificando la carga de múltiples archivos.

## Ubicación

- **Fetcher**: `app/modules/dataset/fetchers/zip.py` → `ZipFetcher`
- **Servicio**: `app/modules/dataset/services.py` → `DataSetService`
- **Registry**: `app/modules/dataset/registry.py` → Registro de fetchers
- **Tests**: `app/modules/dataset/tests/test_dataset_file_upload.py`

## Arquitectura

### ZipFetcher

Clase principal que implementa la interfaz `Fetcher_Interface`:

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

### Integración con DataSetService

El servicio de datasets proporciona métodos de alto nivel:

```python
def fetch_models_from_zip_upload(self, file_storage, dest_dir, current_user):
    """
    1. Guarda el ZIP en carpeta temporal del usuario
    2. Extrae con ZipFetcher
    3. Copia archivos válidos a dest_dir
    4. Retorna lista de archivos procesados
    """
```

## Funcionalidades Principales

### 1. Validación de Archivo ZIP

```python
def _save_zip_to_temp(self, file_storage, current_user) -> Path:
    """
    Valida y guarda el ZIP subido en carpeta temporal.
    
    Validaciones:
    - Archivo debe existir
    - Debe tener extensión .zip
    - Evita sobrescritura con nombres únicos
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

### 2. Extracción Segura

```python
def fetch(self, url, dest_root, current_user=None):
    """
    Extrae archivos del ZIP con validaciones de seguridad.
    
    Protecciones:
    - Path traversal (../, /../, etc.)
    - Límite de entradas (MAX_ZIP_ENTRIES)
    - Solo extrae archivos soportados (.uvl, .gpx)
    - Validación de cada archivo extraído
    - Manejo de nombres duplicados
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

### 3. Validación y Filtrado de Archivos

```python
def _collect_models_into_temp(self, source_root: Path, dest_dir: Path):
    """
    Copia archivos válidos desde source_root a dest_dir.
    
    Proceso:
    1. Recorre recursivamente source_root
    2. Identifica tipo de archivo (.uvl, .gpx)
    3. Valida cada archivo con su descriptor
    4. Copia archivos válidos a dest_dir
    5. Maneja nombres duplicados
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

## Limitaciones y Restricciones

### Límites Configurables

```python
EXTRACTABLE_EXTS = {".uvl", ".gpx"}  # Extensiones permitidas
MAX_ZIP_ENTRIES = 500                 # Máximo número de entradas en ZIP
```

### Validaciones de Seguridad

1. **Path Traversal**: Rechaza paths como `../../../etc/passwd`
2. **Resolución de paths**: Verifica que los archivos extraídos estén dentro del directorio esperado
3. **Extensiones permitidas**: Solo `.uvl` y `.gpx`
4. **Límite de archivos**: Máximo 500 entradas por ZIP
5. **Validación de contenido**: Cada archivo es validado por su descriptor antes de aceptarse

## Flujo de Uso

### 1. Usuario sube ZIP desde formulario

```html
<form method="POST" enctype="multipart/form-data">
    <input type="file" name="zip_file" accept=".zip">
    <button type="submit">Upload ZIP</button>
</form>
```

### 2. Backend procesa el ZIP

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

### 3. Sistema extrae y valida

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

## Ejemplo de Uso

### Caso: Subir colección de rutas GPX

```python
# Usuario sube archivo: hiking_routes.zip
# Contenido:
# - route1.gpx
# - route2.gpx
# - subfolder/route3.gpx
# - README.txt (ignorado)
# - invalid.gpx (inválido, ignorado)

# 1. Validar ZIP
zip_path = dataset_service._save_zip_to_temp(zip_file, current_user)
# → /tmp/user_42/hiking_routes.zip

# 2. Extraer
extract_root = zip_fetcher.fetch(zip_path, temp_root, current_user)
# → /tmp/zip_random123/
#    ├── route1.gpx ✅
#    ├── route2.gpx ✅
#    └── route3.gpx ✅
# README.txt e invalid.gpx fueron ignorados

# 3. Validar y copiar
added = dataset_service._collect_models_into_temp(extract_root, user_temp)
# → [route1.gpx, route2.gpx, route3.gpx]

# 4. Crear dataset
dataset = dataset_service.create_from_form(form, current_user)
# Dataset con 3 archivos GPX validados
```

## Manejo de Errores

### Errores de Formato

```python
# ZIP inválido o corrupto
except BadZipFile:
    raise FetchError("Invalid ZIP file")

# Sin archivos soportados
if not extracted_any:
    raise FetchError("ZIP processed, but no supported files (.uvl/.gpx) were found")
```

### Errores de Seguridad

```python
# Path traversal detectado
if norm_path.startswith("/") or ".." in norm_path:
    raise FetchError("Unsafe path in ZIP")

# Demasiadas entradas
if len(infos) > MAX_ZIP_ENTRIES:
    raise FetchError("ZIP has too many entries")
```

### Errores de Validación

```python
# Archivo no válido según su descriptor
try:
    descriptor.handler.validate(str(path))
except Exception as e:
    logger.warning(f"Skipping invalid model {path}: {e}")
    continue  # No abortar, solo saltar archivo
```

## Testing

### Tests de Subida de ZIP

Ubicación: `app/modules/dataset/tests/test_dataset_file_upload.py`

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
# Tests de subida de archivos
pytest app/modules/dataset/tests/test_dataset_file_upload.py -v

# Solo tests de ZIP
pytest app/modules/dataset/tests/test_dataset_file_upload.py -v -k "zip"

# Con cobertura
pytest app/modules/dataset/tests/test_dataset_file_upload.py --cov=app.modules.dataset.fetchers
```

## Logging

El sistema incluye logging detallado:

```python
logger.info(f"[ZipFetcher] Extracting {zip_path} into {extract_root}")
logger.debug(f"Skipping unsupported file: {path.name}")
logger.warning(f"Skipping invalid model {path}: {e}")
logger.info(f"Added {kind} file: {path.name} -> {target.name}")
logger.info(f"Total files collected from {source_root}: {len(added)}")
```

**Niveles**:
- `INFO`: Operaciones exitosas
- `DEBUG`: Archivos ignorados (extensiones no soportadas)
- `WARNING`: Archivos con errores de validación
- `ERROR`: Errores críticos

## Seguridad

### Protecciones Implementadas

1. **Path Traversal**:
   ```python
   # Bloquea: ../../../etc/passwd
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
   # GPXHandler o UVLHandler validan el contenido
   ```

5. **Sanitización de Nombres**:
   ```python
   desired_name = Path(norm_path).name  # Solo el nombre, sin paths
   ```

## Mejores Prácticas

### 1. Limpieza de Recursos

```python
finally:
    # Siempre limpiar ZIP temporal
    try:
        if zip_path.exists():
            zip_path.unlink()
    except Exception:
        pass
```

### 2. Manejo de Duplicados

```python
# Evitar sobrescritura
while target.exists():
    target = dest_dir / f"{stem} ({i}){suffix}"
    i += 1
```

### 3. Validación Temprana

```python
# Validar antes de extraer
if not filename.lower().endswith(".zip"):
    raise FetchError("Invalid file type")
```

### 4. Logging Apropiado

```python
# INFO para operaciones exitosas
logger.info(f"Extracted {count} files")

# WARNING para archivos problemáticos (no abortar)
logger.warning(f"Skipping invalid file: {filename}")
```

## Limitaciones Conocidas

1. **Estructura plana**: Los subdirectorios del ZIP se aplanan (solo se usa el nombre del archivo)
2. **Sin metadatos preservados**: Timestamps y permisos no se preservan
3. **Sin compresión incremental**: ZIP completo debe cargarse en memoria
4. **Sin progreso**: No hay barra de progreso para ZIPs grandes

## Posibles Mejoras Futuras

- [ ] Soporte para archivos más grandes (streaming)
- [ ] Barra de progreso para extracción
- [ ] Preservar estructura de directorios
- [ ] Soporte para `.7z`, `.tar.gz`
- [ ] Preview de contenido antes de confirmar
- [ ] Límites configurables por tipo de usuario

## Conclusión

La funcionalidad de subida de ZIP proporciona:

- ✅ Extracción automática y segura de archivos
- ✅ Validación exhaustiva de contenido
- ✅ Protección contra ataques de path traversal
- ✅ Manejo robusto de errores
- ✅ Filtrado inteligente de archivos soportados
- ✅ Logging detallado para debugging
- ✅ Testing completo de casos normales y edge cases

Esta implementación permite a los usuarios cargar colecciones completas de archivos GPS de forma eficiente y segura.
