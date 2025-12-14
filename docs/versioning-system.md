# Sistema de Versionado de Datasets

## Descripción General

El sistema de versionado de Track Hub proporciona control de versiones completo para datasets, soportando tanto versiones locales de desarrollo como versiones sincronizadas con Zenodo con DOIs. El sistema implementa versionado semántico (MAJOR.MINOR.PATCH) con creación automática de versiones y clara diferenciación entre versiones locales y publicadas.

## Motivación e Implementación

### Problema Original

Cuando se republicaba un dataset con cambios de archivos, Fakenodo/Zenodo creaba una nueva deposición con un nuevo ID y DOI (ejemplo: `.v1` → `.v2`), pero el sistema no capturaba correctamente este nuevo ID, causando que:
- El dataset quedara en v1 indefinidamente
- No se pudiera republicar nuevamente
- No hubiera registro de las versiones de Zenodo en el historial

### Solución Implementada

Se implementó un sistema de versionado completo que sincroniza las versiones locales con Zenodo:

1. **Captura del nuevo deposition_id**: Se modificó `publish_dataset` en `routes.py` para capturar el nuevo ID cuando Fakenodo crea una nueva versión
2. **Campo version_doi**: Se añadió el campo `version_doi` al modelo `DatasetVersion` para almacenar el DOI específico de cada versión de Zenodo
3. **Auto-creación de versiones**: El sistema crea automáticamente versiones `DatasetVersion` cuando se publica/republica, extrayendo el número de versión del DOI
4. **Sincronización de archivos**: Antes de publicar, se suben los archivos locales a Fakenodo para que detecte cambios correctamente
5. **Versionado de metadatos**: Se implementó la capacidad de crear versiones MINOR/PATCH para cambios solo de metadatos en datasets publicados

### Requisito Cumplido

> "Permitir a los usuarios explorar y comprender la evolución de un dataset a través de sus versiones, diferenciando claramente entre ediciones menores (sin nuevo DOI) y ediciones mayores (con nuevo DOI)."

El sistema ahora diferencia claramente:
- **Versiones mayores (MAJOR)**: Cambios de archivos → Nuevo DOI de Zenodo
- **Versiones menores (MINOR/PATCH)**: Cambios de metadatos → Sin DOI, solo seguimiento local
- **Versiones locales**: Pre-publicación → Sin DOI, desarrollo local

## Tipos de Versiones

### 1. Versiones Locales (Pre-Publicación)

**Badge:** 📦 Versión local - Creada antes de publicar en Zenodo

Las versiones locales se crean antes de que un dataset sea publicado en Zenodo. Permiten a los usuarios rastrear cambios durante el desarrollo y preparación del dataset.

**Características:**
- Sin DOI asignado
- Puede usar cualquier número de versión (ej: v0.1.0, v1.0.0, v2.0.0)
- Los números de versión son independientes de las futuras versiones de Zenodo
- Se crean manualmente vía botón "Create New Version" o automáticamente al editar
- El usuario puede elegir el tipo de versión: PATCH, MINOR o MAJOR

**Cuándo se crean:**
- Manualmente haciendo clic en "Create New Version" en Version History
- Automáticamente al editar un dataset no publicado (auto-versionado)

**Comportamiento del número de versión:**
- El usuario tiene control total vía selector de tipo de versión
- Puede incrementar PATCH (X.Y.Z+1), MINOR (X.Y+1.0) o MAJOR (X+1.0.0)

**Implementación:**
```python
# En routes.py - edit_dataset()
if not dataset.ds_meta_data.dataset_doi:
    # Dataset no publicado: crear versión local automáticamente
    version = VersionService.create_version(
        dataset=dataset,
        changelog="Automatic version after edit:\n" + "\n".join(changes),
        user=current_user,
        bump_type="patch",  # Siempre patch para auto-versionado
    )
```

### 2. Versiones Mayores (Publicaciones en Zenodo)

**Badge:** 📌 Versión mayor (X.0.0) - Publicada en Zenodo con DOI

Las versiones mayores se crean cuando un dataset se publica o republica en Zenodo con cambios de archivos. Cada versión mayor tiene su propio DOI único.

**Características:**
- Tiene DOI específico de versión (ej: `10.9999/dataset.v1`, `10.9999/dataset.v2`)
- Almacenado en el campo `DatasetVersion.version_doi`
- Formato de número de versión: X.0.0 (ej: 1.0.0, 2.0.0, 3.0.0)
- Creada automáticamente por el sistema
- Requiere cambios de archivos para disparar nueva versión mayor

**Cuándo se crean:**
- Primera publicación en Zenodo → v1.0.0 con DOI
- Republicación con cambios de archivos → v2.0.0, v3.0.0, etc. con nuevo DOI
- Fakenodo/Zenodo detecta cambios de archivos y crea nueva deposición

**Comportamiento del número de versión:**
- Extraído del DOI de Zenodo (ej: `.v2` → `2.0.0`)
- Incrementado automáticamente por Zenodo cuando los archivos cambian
- No se puede crear manualmente

**Implementación - Parte 1: Sincronización de Archivos**
```python
# En routes.py - publish_dataset()
# Líneas 175-202

# Detectar cambios de archivos
old_fingerprint = dataset.ds_meta_data.files_fingerprint
current_fingerprint = calculate_fingerprint(dataset)

if is_republication and old_fingerprint != current_fingerprint:
    logger.info("[PUBLISH] Re-publication with changes - files modified")

    # Subir archivos nuevos a Fakenodo ANTES de publicar
    logger.info(f"[PUBLISH] Syncing local files with Fakenodo deposition {deposition_id}")

    # Obtener archivos actuales en Fakenodo
    deposition_data = zenodo_service.get_deposition(deposition_id)
    fakenodo_files = {f['filename'] for f in deposition_data.get('files', [])}

    # Subir archivos locales que no estén en Fakenodo
    uploaded_count = 0
    for feature_model in dataset.feature_models:
        for hubfile in feature_model.files:
            if hubfile.name not in fakenodo_files:
                zenodo_service.upload_file(dataset, deposition_id, feature_model, current_user)
                uploaded_count += 1

    if uploaded_count > 0:
        logger.info(f"[PUBLISH] Uploaded {uploaded_count} new file(s) to Fakenodo")
```

**Implementación - Parte 2: Captura del Nuevo ID y DOI**
```python
# En routes.py - publish_dataset()
# Líneas 204-244

# Publicar deposición - Fakenodo puede devolver nueva deposición con nuevo ID
publish_response = zenodo_service.publish_deposition(deposition_id)
new_deposition_id = publish_response.get("id", deposition_id)

# Si Fakenodo creó nueva versión, actualizar el deposition_id
if new_deposition_id != deposition_id:
    logger.info(f"[PUBLISH] New version created - Old: {deposition_id}, New: {new_deposition_id}")
    deposition_id = new_deposition_id
else:
    logger.info(f"[PUBLISH] No new version - Using same deposition: {deposition_id}")

# Obtener DOI de la respuesta de publicación
deposition_doi = publish_response.get("doi")
if not deposition_doi:
    # Fallback: obtenerlo de la API si no está en la respuesta
    deposition_doi = zenodo_service.get_doi(deposition_id)

# Actualizar deposition_id en metadata si cambió
update_data = {"dataset_doi": deposition_doi, "files_fingerprint": current_fingerprint}
if new_deposition_id != dataset.ds_meta_data.deposition_id:
    update_data["deposition_id"] = new_deposition_id
    logger.info(f"[PUBLISH] Updating deposition_id from {dataset.ds_meta_data.deposition_id} to {new_deposition_id}")

dataset_service.update_dsmetadata(dataset.ds_meta_data_id, **update_data)
```

**Implementación - Parte 3: Auto-creación de DatasetVersion**
```python
# En routes.py - publish_dataset()
# Líneas 245-280

# Auto-crear DatasetVersion para rastrear versiones de Zenodo
logger.info(f"[PUBLISH] Checking if version with DOI {deposition_doi} already exists")
version_exists = DatasetVersion.query.filter_by(
    dataset_id=dataset.id,
    version_doi=deposition_doi
).first()

if not version_exists:
    # Determinar número de versión basado en DOI
    # Extraer número de versión del DOI (ej: "10.9999/dataset.v2" -> "2.0.0")
    doi_version = deposition_doi.split('.v')[-1] if '.v' in deposition_doi else '1'
    version_number = f"{doi_version}.0.0"

    logger.info(f"[PUBLISH] Creating new version {version_number} for DOI {deposition_doi}")

    # Generar changelog
    if is_first_publication:
        changelog = "Initial publication to Zenodo"
    else:
        changelog = "Republished to Zenodo with file changes"

    # Crear snapshot de archivos
    files_snapshot = VersionService._create_files_snapshot(dataset)

    # Crear DatasetVersion con DOI
    version = DatasetVersion(
        dataset_id=dataset.id,
        version_number=version_number,
        title=dataset.ds_meta_data.title,
        description=dataset.ds_meta_data.description,
        files_snapshot=files_snapshot,
        changelog=changelog,
        created_by_id=current_user.id,
        version_doi=deposition_doi  # ← CLAVE: Almacenar DOI de Zenodo
    )

    # Calcular métricas si aplica
    if hasattr(version, 'total_features'):
        version.total_features = dataset.calculate_total_features() or 0
        version.total_constraints = dataset.calculate_total_constraints() or 0
        version.model_count = len(dataset.feature_models) or 0

    db.session.add(version)
    db.session.commit()

    logger.info(f"[PUBLISH] Created version {version_number} with DOI {deposition_doi}")
```

### 3. Versiones Menores (Mejoras de Metadatos)

**Badge:** 📝 Versión menor (X.Y.0) - Mejoras de metadatos (sin DOI)

Las versiones menores rastrean mejoras significativas de metadatos después de la publicación sin crear un nuevo DOI.

**Características:**
- Sin DOI (usa el DOI conceptual del dataset padre)
- Formato de número de versión: X.Y.0 (ej: 1.1.0, 1.2.0, 2.1.0)
- Solo para datasets publicados
- Solo para cambios de metadatos
- El usuario elige "Minor" en el selector de tipo de versión

**Cuándo se crean:**
- Al editar metadatos de dataset publicado (título, descripción, tags)
- Usuario selecciona tipo de versión "Minor" en el formulario de edición
- Sin archivos añadidos

**Comportamiento del número de versión:**
- Incrementa Y en X.Y.0 (ej: 1.0.0 → 1.1.0 → 1.2.0)
- Resetea Z a 0

**Implementación:**
```python
# En routes.py - edit_dataset()
# Líneas 865-920

# Dataset publicado
if dataset.ds_meta_data.dataset_doi:
    if metadata_changes and not file_changes:
        # Solo metadatos cambiaron: crear versión minor/patch (sin DOI)
        # Obtener elección del usuario del formulario
        version_bump_type = request.form.get("version_bump_type", "patch")
        if version_bump_type not in ["minor", "patch"]:
            version_bump_type = "patch"

        version_type_label = "Minor" if version_bump_type == "minor" else "Patch"
        changelog = f"{version_type_label} edition (metadata only):\n" + "\n".join(metadata_changes)

        # Obtener última versión para determinar siguiente número
        latest_version = dataset.get_latest_version()
        if latest_version:
            # Parsear versión actual e incrementar según tipo
            parts = latest_version.version_number.split('.')
            if len(parts) == 3:
                major, minor, patch = parts
                if version_bump_type == "minor":
                    new_version_number = f"{major}.{int(minor) + 1}.0"
                else:  # patch
                    new_version_number = f"{major}.{minor}.{int(patch) + 1}"

        # Crear DatasetVersion SIN DOI
        version = DatasetVersion(
            dataset_id=dataset.id,
            version_number=new_version_number,
            title=dataset.ds_meta_data.title,
            description=dataset.ds_meta_data.description,
            files_snapshot=files_snapshot,
            changelog=changelog,
            created_by_id=current_user.id,
            version_doi=None  # ← Versiones menores no obtienen DOI
        )

        db.session.add(version)
        db.session.commit()

        flash(f"Dataset updated successfully! {version_type_label} version: v{version.version_number} (metadata only) 📝", "success")
```

### 4. Versiones de Parche (Correcciones de Metadatos)

**Badge:** 🔧 Versión de parche (X.Y.Z) - Correcciones de metadatos (sin DOI)

Las versiones de parche rastrean correcciones menores de metadatos después de la publicación sin crear un nuevo DOI.

**Características:**
- Sin DOI (usa el DOI conceptual del dataset padre)
- Formato de número de versión: X.Y.Z (ej: 1.0.1, 1.0.2, 1.1.1)
- Solo para datasets publicados
- Solo para cambios de metadatos
- El usuario elige "Patch" en el selector de tipo de versión (por defecto)

**Cuándo se crean:**
- Al editar metadatos de dataset publicado (corregir errores tipográficos, formato)
- Usuario selecciona tipo de versión "Patch" en el formulario de edición (por defecto)
- Sin archivos añadidos

**Comportamiento del número de versión:**
- Incrementa Z en X.Y.Z (ej: 1.0.0 → 1.0.1 → 1.0.2)

**Implementación:**
Ver código de Versiones Menores arriba - usa la misma lógica con `version_bump_type = "patch"`

## Ejemplos de Flujo de Trabajo

### Ejemplo 1: Desarrollo de Nuevo Dataset y Publicación

```
1. Crear dataset → v0.0.1 (local, auto-creada)
2. Editar metadatos → v0.0.2 (local, auto-creada)
3. Crear versión manual → v0.1.0 (local, usuario elige MINOR)
4. Crear versión manual → v1.0.0 (local, usuario elige MAJOR)
5. Publicar en Zenodo → v1.0.0 (mayor, DOI: 10.9999/dataset.v1)
   └─ La v1.0.0 local permanece como versión local
   └─ Se crea nueva v1.0.0 con DOI

Historial de Versiones muestra:
- 📌 v1.0.0 (DOI: 10.9999/dataset.v1) - Publicada en Zenodo
- 📦 v1.0.0 - Versión local
- 📦 v0.1.0 - Versión local
- 📦 v0.0.2 - Versión local
- 📦 v0.0.1 - Versión local
```

### Ejemplo 2: Dataset Publicado con Cambios de Metadatos

```
1. Dataset publicado en v1.0.0 (DOI: 10.9999/dataset.v1)
2. Editar metadatos, elegir PATCH → v1.0.1 (parche, sin DOI)
3. Editar metadatos, elegir PATCH → v1.0.2 (parche, sin DOI)
4. Editar metadatos, elegir MINOR → v1.1.0 (menor, sin DOI)
5. Editar metadatos, elegir PATCH → v1.1.1 (parche, sin DOI)

Historial de Versiones muestra:
- 🔧 v1.1.1 - Versión de parche ✓ Actual
- 📝 v1.1.0 - Versión menor
- 🔧 v1.0.2 - Versión de parche
- 🔧 v1.0.1 - Versión de parche
- 📌 v1.0.0 (DOI: 10.9999/dataset.v1) - Publicada en Zenodo
```

### Ejemplo 3: Dataset Publicado con Cambios de Archivos

```
1. Dataset publicado en v1.0.0 (DOI: 10.9999/dataset.v1)
2. Editar metadatos, elegir MINOR → v1.1.0 (menor, sin DOI)
3. Editar metadatos, elegir PATCH → v1.1.1 (parche, sin DOI)
4. Añadir nuevo archivo, guardar → Archivos guardados localmente, mensaje: "Requiere republicación"
5. Republicar en Zenodo → v2.0.0 (mayor, DOI: 10.9999/dataset.v2)

Historial de Versiones muestra:
- 📌 v2.0.0 (DOI: 10.9999/dataset.v2) - Publicada en Zenodo ✓ Actual
- 🔧 v1.1.1 - Versión de parche
- 📝 v1.1.0 - Versión menor
- 📌 v1.0.0 (DOI: 10.9999/dataset.v1) - Publicada en Zenodo
```

## Implementación Técnica Completa

### Esquema de Base de Datos

**Modelo DatasetVersion:**
```python
# En app/modules/dataset/models.py
class DatasetVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    version_number = db.Column(db.String(20))  # ej: "1.0.0", "1.1.0", "1.0.1"
    version_doi = db.Column(db.String(120))     # DOI de Zenodo solo para versiones mayores
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    changelog = db.Column(db.Text)
    files_snapshot = db.Column(db.Text)         # Snapshot JSON de archivos
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'version_number': self.version_number,
            'version_doi': self.version_doi,  # ← Campo añadido
            'title': self.title,
            'description': self.description,
            'changelog': self.changelog,
            'created_at': self.created_at.isoformat(),
            # ... más campos
        }
```

**Campo clave: `version_doi`**
- `NULL` = Versión Local, Menor o de Parche (sin DOI)
- `NOT NULL` = Versión Mayor (publicada en Zenodo con DOI)

**Migración de Base de Datos:**
```python
# migrations/versions/2ff2c8b0a045_add_version_doi_field.py
def upgrade():
    op.add_column('data_set_version',
        sa.Column('version_doi', sa.String(length=120), nullable=True))

def downgrade():
    op.drop_column('data_set_version', 'version_doi')
```

### Restricciones de Creación Manual de Versiones

**Bloqueo para Datasets Publicados:**
```python
# En routes.py - create_version()
# Líneas 558-590

@dataset_bp.route('/dataset/<int:dataset_id>/versions/create', methods=['POST'])
@login_required
def create_version(dataset_id: int):
    dataset = dataset_service.get_or_404(dataset_id)

    # Verificar que el usuario sea el propietario
    if current_user.id != dataset.user_id:
        return jsonify({"message": "Unauthorized"}), 401

    # BLOQUEAR creación manual de versiones para datasets publicados
    if dataset.ds_meta_data.dataset_doi:
        flash(
            "Cannot create local versions for published datasets. "
            "Use Edit to create minor/patch versions for metadata changes, "
            "or Republish to create a major version with file changes.",
            "error"
        )
        return redirect(url_for('dataset.list_versions', dataset_id=dataset.id))

    # Permitir para datasets no publicados
    changelog = request.form.get("changelog")
    bump_type = request.form.get("bump_type", "patch")

    version = VersionService.create_version(
        dataset=dataset,
        changelog=changelog,
        user=current_user,
        bump_type=bump_type
    )

    flash(f"Version v{version.version_number} created successfully!", "success")
    return redirect(url_for('dataset.list_versions', dataset_id=dataset.id))
```

### Lógica de Visualización de Versiones

**En list_versions.html:**
```jinja2
<!-- Líneas 152-189 -->
{% if version.version_doi %}
    <!-- Versión mayor con DOI -->
    <div class="mb-3 p-2 bg-success bg-opacity-10 rounded border border-success">
        <div class="d-flex align-items-center justify-content-between">
            <div class="flex-grow-1">
                <small class="text-muted d-block mb-1">
                    <i data-feather="link" style="width: 14px; height: 14px;"></i>
                    <strong>📌 Versión mayor (X.0.0)</strong> - Publicada en Zenodo con DOI
                </small>
                <input type="text" class="form-control form-control-sm"
                       id="version_doi_{{ version.id }}"
                       value="{{ version.version_doi }}" readonly>
            </div>
            <button class="btn btn-sm btn-outline-secondary ms-2"
                    type="button"
                    onclick="navigator.clipboard.writeText('{{ version.version_doi }}'); ...">
                <i data-feather="copy"></i>
            </button>
        </div>
    </div>

{% elif dataset.ds_meta_data.dataset_doi and version.version_number.split('.')[0]|int >= 1 %}
    <!-- Versión menor o de parche (post-publicación) -->
    <div class="mb-3 p-2 bg-info bg-opacity-10 rounded border border-info">
        <small class="text-muted">
            <i data-feather="edit-3" style="width: 14px; height: 14px;"></i>
            {% if version.version_number.split('.')[1]|int > 0 %}
                <strong>📝 Versión menor (X.Y.0)</strong> - Mejoras de metadatos (sin DOI)
            {% else %}
                <strong>🔧 Versión de parche (X.Y.Z)</strong> - Correcciones de metadatos (sin DOI)
            {% endif %}
        </small>
    </div>

{% else %}
    <!-- Versión local (pre-publicación) -->
    <div class="mb-3 p-2 bg-warning bg-opacity-10 rounded border border-warning">
        <small class="text-muted">
            <i data-feather="info" style="width: 14px; height: 14px;"></i>
            <strong>📦 Versión local</strong> - Creada antes de publicar en Zenodo
        </small>
    </div>
{% endif %}
```

**Lógica de diferenciación:**
1. Si `version.version_doi` existe → Versión Mayor (con DOI)
2. Si dataset tiene DOI Y versión >= 1.x.x → Versión Menor/Parche (post-publicación)
   - Si segundo número > 0 (X.Y.0 donde Y > 0) → Versión Menor
   - Si no → Versión de Parche
3. Si no → Versión Local (pre-publicación)

### Integración con Zenodo/Fakenodo

**Sincronización de Archivos Antes de Publicar:**
```python
# En routes.py - publish_dataset()
# Obtener archivos actuales en Fakenodo/Zenodo
deposition_data = zenodo_service.get_deposition(deposition_id)
fakenodo_files = {f['filename'] for f in deposition_data.get('files', [])}

# Subir archivos locales que no estén en Zenodo
for feature_model in dataset.feature_models:
    for hubfile in feature_model.files:
        if hubfile.name not in fakenodo_files:
            zenodo_service.upload_file(dataset, deposition_id, feature_model, user)
```

**Detección de Nueva Versión:**
```python
# Publicar en Zenodo
publish_response = zenodo_service.publish_deposition(deposition_id)
new_deposition_id = publish_response.get("id")

# Si Zenodo creó nueva deposición, detectó cambios de archivos
if new_deposition_id != old_deposition_id:
    # Nueva versión mayor creada
    deposition_id = new_deposition_id
```

## Interfaz de Usuario

### Página de Historial de Versiones

**Sección de Cabecera (para datasets publicados):**
```html
<!-- list_versions.html líneas 52-81 -->
<div class="card-body border-bottom bg-light">
    <div class="row">
        <div class="col-md-6">
            <h6>DOI Conceptual (Apunta siempre a la última versión publicada)</h6>
            <input value="{{ dataset.ds_meta_data.dataset_doi }}" readonly>
        </div>
        <div class="col-md-6">
            <h6>Tipos de Versiones</h6>
            <p>
                <strong>Versiones mayores</strong> (con DOI) se publican en Zenodo e incluyen cambios de archivos.
                <strong>Versiones menores/parche</strong> (sin DOI) rastrean mejoras de metadatos localmente.
            </p>
        </div>
    </div>
</div>
```

**Lista de Versiones:**
- Cada versión mostrada en tarjeta con encabezado codificado por color
- Badge de versión (v1.0.0, v1.1.0, etc.) en fuente grande
- Badge "Current" en la última versión
- Badge de tipo (📌 Mayor / 📝 Menor / 🔧 Parche / 📦 Local)
- Campo DOI con botón de copiar (solo versiones mayores)
- Visualización de changelog
- Botones de acción: Comparar, Ver
- Estadísticas (features, constraints, modelos)

**Estilo de Tarjetas de Versión:**
```html
<!-- Versión más reciente: fondo azul -->
<div class="card {% if loop.first %}border-primary bg-primary bg-opacity-10{% endif %}">
    <div class="card-header {% if loop.first %}bg-primary text-white{% else %}bg-light{% endif %}">
        <!-- Badge de versión más grande y visible -->
        <span class="badge {% if loop.first %}bg-primary{% else %}bg-dark{% endif %} fs-5 me-2 px-3 py-2">
            v{{ version.version_number }}
        </span>
        {{ version.title }}

        <!-- Badge "Current" -->
        {% if loop.first %}
        <span class="badge bg-success fs-6 px-3 py-2">Current</span>
        {% endif %}
    </div>
</div>
```

### Página de Editar Dataset

**Para Datasets No Publicados:**
```html
<!-- edit_dataset.html líneas 30-34 -->
<div class="alert alert-info">
    <i data-feather="info"></i>
    <strong>Auto-versionado habilitado:</strong> Los cambios crearán una nueva versión local automáticamente.
</div>
```

**Para Datasets Publicados:**
```html
<!-- edit_dataset.html líneas 26-29 -->
<div class="alert alert-warning">
    <i data-feather="alert-triangle"></i>
    <strong>Advertencia:</strong> Este dataset está sincronizado con Zenodo.
    Los cambios NO se reflejarán en Zenodo automáticamente.
</div>

<!-- edit_dataset.html líneas 107-122 -->
<div class="mb-3" id="versionTypeSelector">
    <label for="version_bump_type" class="form-label">
        <i data-feather="git-branch"></i>
        Tipo de Versión (para cambios de metadatos)
    </label>
    <select class="form-select" id="version_bump_type" name="version_bump_type">
        <option value="patch" selected>🔧 Patch (X.Y.Z+1) - Correcciones menores, errores tipográficos</option>
        <option value="minor">✨ Minor (X.Y+1.0) - Mejoras significativas de metadatos</option>
    </select>
    <small class="text-muted">
        Esto aplica solo si cambias metadatos. Añadir archivos requiere republicar para una versión mayor.
    </small>
</div>

<!-- Advertencia cuando se seleccionan archivos -->
<div class="alert alert-warning d-none" id="filesAddedWarning">
    <i data-feather="alert-triangle"></i>
    <strong>Archivos seleccionados:</strong> Añadir archivos requerirá republicar en Zenodo
    para crear una nueva versión mayor (X+1.0.0). El selector de tipo de versión será ignorado.
</div>
```

**JavaScript para Monitoreo de Archivos:**
```javascript
// edit_dataset.html líneas 154-169
const filesInput = document.getElementById('files');
const versionTypeSelector = document.getElementById('versionTypeSelector');
const filesAddedWarning = document.getElementById('filesAddedWarning');

if (filesInput && versionTypeSelector && filesAddedWarning) {
    filesInput.addEventListener('change', function() {
        if (this.files && this.files.length > 0) {
            // Archivos seleccionados: atenuar el selector y mostrar advertencia
            versionTypeSelector.style.opacity = '0.5';
            filesAddedWarning.classList.remove('d-none');
            feather.replace();
        } else {
            // Sin archivos: restaurar selector y ocultar advertencia
            versionTypeSelector.style.opacity = '1';
            filesAddedWarning.classList.add('d-none');
        }
    });
}
```

### Modal Crear Nueva Versión (Solo No Publicados)

```html
<!-- list_versions.html líneas 311-363 -->
<div class="modal fade" id="createVersionModal">
    <div class="modal-content">
        <form method="POST" action="{{ url_for('dataset.create_version', dataset_id=dataset.id) }}">
            <div class="modal-header">
                <h5><i data-feather="git-branch"></i> Crear Nueva Versión</h5>
            </div>
            <div class="modal-body">
                <div class="alert alert-info">
                    <small>
                        <strong>Versión local:</strong> Se guardará una instantánea del estado actual.
                        Cuando publiques en Zenodo, comenzará con v1.0.0 independientemente de tus números de versión locales.
                    </small>
                </div>

                <div class="mb-3">
                    <label class="form-label">Tipo de Versión</label>
                    <select class="form-select" name="bump_type">
                        <option value="patch" selected>🔧 Patch (X.Y.Z+1) - Correcciones de errores, cambios pequeños</option>
                        <option value="minor">✨ Minor (X.Y+1.0) - Nuevas características, cambios compatibles</option>
                        <option value="major">🚀 Major (X+1.0.0) - Cambios importantes, actualizaciones mayores</option>
                    </select>
                    <small class="text-muted">
                        Versión actual: <strong>v{{ latest_version.version_number if latest_version else '0.0.0' }}</strong>
                    </small>
                </div>

                <div class="mb-3">
                    <label for="changelog">Changelog <span class="text-danger">*</span></label>
                    <textarea class="form-control" id="changelog" name="changelog" rows="4" required
                              placeholder="Describe los cambios en esta versión...&#10;Ejemplo:&#10;- Añadidos nuevos modelos de características&#10;- Actualizados metadatos del dataset&#10;- Corregido nombrado de archivos"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    <i data-feather="x"></i> Cancelar
                </button>
                <button type="submit" class="btn btn-primary">
                    <i data-feather="save"></i> Crear Versión
                </button>
            </div>
        </form>
    </div>
</div>
```

## Sistema de DOIs

### DOI Conceptual
- Uno por dataset, nunca cambia
- Siempre apunta a la última versión publicada
- Formato: `10.9999/dataset-identifier` (sin `.vX`)
- Mostrado en cabecera del historial de versiones
- Almacenado en `DSMetaData.dataset_doi`

### DOI Específico de Versión
- Uno por versión mayor
- Permanentemente vinculado a los archivos de esa versión
- Formato: `10.9999/dataset-identifier.v1`, `.v2`, `.v3`, etc.
- Almacenado en `DatasetVersion.version_doi`
- Usado para citas para asegurar reproducibilidad

**Relación entre DOIs:**
```
DOI Conceptual:      10.9999/fakenodo.a843b04d
                              ↓
                    Siempre redirige a última versión
                              ↓
DOIs de Versión:     10.9999/fakenodo.a843b04d.v1 (Primera publicación)
                     10.9999/fakenodo.a843b04d.v2 (Republicación con archivos)
                     10.9999/fakenodo.a843b04d.v3 (Otra republicación)
```

## Mejores Prácticas

### Para Usuarios

**Durante Desarrollo (antes de publicación):**
- Usa versiones locales para rastrear tu progreso
- Elige tipos de versión (PATCH/MINOR/MAJOR) para organizar cambios
- Los números de versión son solo para tu referencia
- No te preocupes por "desperdiciar" números de versión

**Después de Publicación:**
- Usa PATCH para correcciones de errores tipográficos, correcciones menores
- Usa MINOR para mejoras sustanciales de metadatos (mejores descripciones, nuevas etiquetas)
- Añade archivos y republica para versiones MAJOR (nuevo DOI)
- Siempre añade mensajes de changelog significativos

**Para Citas:**
- Usa DOI específico de versión para reproducibilidad
- Usa DOI conceptual para referenciar "el dataset" en general

### Para Desarrolladores

**Añadir Nuevos Tipos de Versión:**
1. Añadir lógica de badge en `list_versions.html`
2. Actualizar creación de versión en `routes.py`
3. Actualizar selectores de UI en `edit_dataset.html`
4. Añadir tests en `test_versions.py`
5. Documentar en este archivo

**Modificar Lógica de Versionado:**
1. Actualizar `VersionService.create_version()`
2. Actualizar auto-versionado en ruta `edit_dataset`
3. Actualizar lógica de visualización en templates
4. Ejecutar suite completa de tests
5. Actualizar documentación

## Testing

Ejecutar tests relacionados con versionado:
```bash
# Tests de versionado
pytest app/modules/dataset/tests/test_versions.py -v

# Tests de republicación
pytest app/modules/dataset/tests/test_republication.py -v

# Tests de integración con Fakenodo
pytest app/modules/fakenodo/tests/test_fakenodo_integration.py -v

# Todos los tests
rosemary test
```

**Cobertura actual:** 83 tests pasando

**Tests importantes:**
- `test_publish_dataset_success` - Primera publicación
- `test_publish_dataset_already_published` - Republicación sin cambios
- `test_publish_after_changing_files_creates_new_version_and_doi` - Republicación con archivos
- `test_cannot_create_version_after_publish` - Bloqueo de versiones manuales
- `test_captures_new_deposition_id_from_response` - Captura de nuevo ID

## Mejoras Futuras

Posibles mejoras a considerar:

1. **UI de Comparación de Versiones**: Mostrar diffs detallados entre versiones
2. **Ramificación de Versiones**: Permitir crear versiones desde versiones no-últimas
3. **Etiquetas de Versión**: Etiquetas personalizadas para versiones (ej: "stable", "beta")
4. **Changelog Automatizado**: Generar changelog desde cambios detectados
5. **Analíticas de Versiones**: Rastrear qué versiones son más accedidas
6. **Operaciones Masivas de Versiones**: Revertir, fusionar o archivar múltiples versiones
7. **Comentarios de Versión**: Permitir hilos de discusión en versiones
8. **Exportación de Versión**: Exportar metadatos de versión y changelog como PDF

## Archivos Relacionados

### Backend
- `app/modules/dataset/routes.py` - Lógica principal de versionado
- `app/modules/dataset/models.py` - Modelo DatasetVersion
- `core/services/VersionService.py` - Servicio de creación de versiones
- `app/modules/fakenodo/services.py` - Integración con Zenodo

### Frontend
- `app/modules/dataset/templates/dataset/list_versions.html` - UI de historial de versiones
- `app/modules/dataset/templates/dataset/edit_dataset.html` - Formulario de edición con versionado
- `app/modules/dataset/templates/dataset/view_dataset.html` - Vista de dataset

### Tests
- `app/modules/dataset/tests/test_versions.py` - Tests de funcionalidad de versiones
- `app/modules/dataset/tests/test_republication.py` - Tests de republicación
- `app/modules/fakenodo/tests/test_fakenodo_integration.py` - Tests de integración con Zenodo

### Base de Datos
- `migrations/versions/2ff2c8b0a045_add_version_doi_field.py` - Migración añadiendo version_doi

## Soporte

Para preguntas o problemas:
- Revisar logs: archivos `app.log.*`
- Revisar casos de test para ejemplos
- Ver `docs/zenodo.md` para documentación específica de Zenodo
- Ver `docs/fakenodo.md` para testing local con Fakenodo

## Resumen de Cambios Implementados

### Cambios en Base de Datos
1. ✅ Añadido campo `version_doi` a tabla `data_set_version`
2. ✅ Migración aplicada: `2ff2c8b0a045_add_version_doi_field`

### Cambios en Backend
1. ✅ `routes.py::publish_dataset()` - Captura nuevo deposition_id y DOI
2. ✅ `routes.py::publish_dataset()` - Sincroniza archivos antes de publicar
3. ✅ `routes.py::publish_dataset()` - Auto-crea DatasetVersion con DOI
4. ✅ `routes.py::edit_dataset()` - Diferencia cambios de metadatos vs archivos
5. ✅ `routes.py::edit_dataset()` - Auto-crea versiones MINOR/PATCH para metadatos
6. ✅ `routes.py::create_version()` - Bloquea versiones manuales para datasets publicados
7. ✅ `models.py::DatasetVersion` - Añadido campo version_doi y to_dict()

### Cambios en Frontend
1. ✅ `list_versions.html` - Diferenciación visual de tipos de versión
2. ✅ `list_versions.html` - Sección de DOI Conceptual vs Tipos de Versiones
3. ✅ `list_versions.html` - Badges codificados por color con mejores textos
4. ✅ `list_versions.html` - Modal de crear versión simplificado para pre-publicación
5. ✅ `edit_dataset.html` - Selector de tipo de versión MINOR/PATCH
6. ✅ `edit_dataset.html` - JavaScript para advertencia cuando se añaden archivos
7. ✅ `edit_dataset.html` - Mensaje de auto-versionado para datasets no publicados

### Tests
1. ✅ `test_republication.py` - 4 tests para captura de deposition_id
2. ✅ `test_versions.py` - Test actualizado para MockZenodoService completo
3. ✅ 83/83 tests pasando

### Documentación
1. ✅ `docs/versioning-system.md` - Documentación completa en español con implementación
