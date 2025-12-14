
# Dataset Versioning System


## General Description

The Track Hub versioning system provides full version control for datasets, supporting both local development versions and versions synchronized with Zenodo with DOIs. The system implements semantic versioning (MAJOR.MINOR.PATCH) with automatic version creation and clear differentiation between local and published versions.


## Motivation and Implementation

### Original Problem

When a dataset was republished with file changes, Fakenodo/Zenodo created a new deposition with a new ID and DOI (e.g., `.v1` → `.v2`), but the system did not correctly capture this new ID, causing:
- The dataset to remain at v1 indefinitely
- Republishing was not possible again
- There was no record of Zenodo versions in the history

### Implemented Solution

A complete versioning system was implemented that synchronizes local versions with Zenodo:

1. **Captura del nuevo deposition_id**: Se modificó `publish_dataset` en `routes.py` para capturar el nuevo ID cuando Fakenodo crea una nueva versión
2. **Campo version_doi**: Se añadió el campo `version_doi` al modelo `DatasetVersion` para almacenar el DOI específico de cada versión de Zenodo
3. **Auto-creación de versiones**: El sistema crea automáticamente versiones `DatasetVersion` cuando se publica/republica, extrayendo el número de versión del DOI
4. **Sincronización de archivos**: Antes de publicar, se suben los archivos locales a Fakenodo para que detecte cambios correctamente
5. **Versionado de metadatos**: Se implementó la capacidad de crear versiones MINOR/PATCH para cambios solo de metadatos en datasets publicados


### Requirement Met

> "Allow users to explore and understand the evolution of a dataset through its versions, clearly differentiating between minor editions (without new DOI) and major editions (with new DOI)."

The system now clearly differentiates:
- **Major versions (MAJOR)**: File changes → New Zenodo DOI
- **Minor versions (MINOR/PATCH)**: Metadata changes → No DOI, local tracking only
- **Local versions**: Pre-publication → No DOI, local development


## Types of Versions

### 1. Local Versions (Pre-Publication)

**Badge:** 📦 Local version - Created before publishing to Zenodo

Local versions are created before a dataset is published to Zenodo. They allow users to track changes during the development and preparation of the dataset.

**Features:**
- No DOI assigned
- Can use any version number (e.g., v0.1.0, v1.0.0, v2.0.0)
- Version numbers are independent of future Zenodo versions
- Created manually via the "Create New Version" button or automatically when editing
- The user can choose the version type: PATCH, MINOR, or MAJOR

**When they are created:**
- Manually by clicking "Create New Version" in Version History
- Automatically when editing an unpublished dataset (auto-versioning)

**Version number behavior:**
- The user has full control via the version type selector
- Can increment PATCH (X.Y.Z+1), MINOR (X.Y+1.0), or MAJOR (X+1.0.0)

**Implementation:**
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


### 2. Major Versions (Zenodo Publications)

**Badge:** 📌 Major version (X.0.0) - Published in Zenodo with DOI

Major versions are created when a dataset is published or republished in Zenodo with file changes. Each major version has its own unique DOI.

**Features:**
- Has a specific version DOI (e.g., `10.9999/dataset.v1`, `10.9999/dataset.v2`)
- Stored in the `DatasetVersion.version_doi` field
- Version number format: X.0.0 (e.g., 1.0.0, 2.0.0, 3.0.0)
- Automatically created by the system
- Requires file changes to trigger a new major version

**When they are created:**
- First publication in Zenodo → v1.0.0 with DOI
- Republishing with file changes → v2.0.0, v3.0.0, etc. with new DOI
- Fakenodo/Zenodo detects file changes and creates a new deposition

**Version number behavior:**
- Extracted from the Zenodo DOI (e.g., `.v2` → `2.0.0`)
- Automatically incremented by Zenodo when files change
- Cannot be created manually

**Implementation - Part 1: File Synchronization**
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

**Implementation - Part 2: Capture of New ID and DOI**
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

**Implementation - Part 3: Auto-creation of DatasetVersion**
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


### 3. Minor Versions (Metadata Improvements)

**Badge:** 📝 Minor version (X.Y.0) - Metadata improvements (no DOI)

Minor versions track significant metadata improvements after publication without creating a new DOI.

**Features:**
- No DOI (uses the parent dataset's conceptual DOI)
- Version number format: X.Y.0 (e.g., 1.1.0, 1.2.0, 2.1.0)
- Only for published datasets
- Only for metadata changes
- The user selects "Minor" in the version type selector

**When they are created:**
- When editing metadata of a published dataset (title, description, tags)
- User selects "Minor" version type in the edit form
- No files added

**Version number behavior:**
- Increments Y in X.Y.0 (e.g., 1.0.0 → 1.1.0 → 1.2.0)
- Resets Z to 0

**Implementation:**
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


### 4. Patch Versions (Metadata Corrections)

**Badge:** 🔧 Patch version (X.Y.Z) - Metadata corrections (no DOI)

Patch versions track minor metadata corrections after publication without creating a new DOI.

**Features:**
- No DOI (uses the parent dataset's conceptual DOI)
- Version number format: X.Y.Z (e.g., 1.0.1, 1.0.2, 1.1.1)
- Only for published datasets
- Only for metadata changes
- The user selects "Patch" in the version type selector (default)

**When they are created:**
- When editing metadata of a published dataset (fixing typos, formatting)
- User selects "Patch" version type in the edit form (default)
- No files added

**Version number behavior:**
- Increments Z in X.Y.Z (e.g., 1.0.0 → 1.0.1 → 1.0.2)

**Implementation:**
See Minor Versions code above - uses the same logic with `version_bump_type = "patch"`


## Workflow Examples

### Example 1: New Dataset Development and Publication

```
1. Crear dataset → v0.0.1 (local, auto-creada)
2. Editar metadatos → v0.0.2 (local, auto-creada)
3. Crear versión manual → v0.1.0 (local, usuario elige MINOR)
4. Crear versión manual → v1.0.0 (local, usuario elige MAJOR)
5. Publicar en Zenodo → v1.0.0 (mayor, DOI: 10.9999/dataset.v1)
   └─ La v1.0.0 local permanece como versión local
   └─ Se crea nueva v1.0.0 con DOI


Version History shows:
- 📌 v1.0.0 (DOI: 10.9999/dataset.v1) - Published in Zenodo
- 📦 v1.0.0 - Local version
- 📦 v0.1.0 - Local version
- 📦 v0.0.2 - Local version
- 📦 v0.0.1 - Local version
```


### Example 2: Published Dataset with Metadata Changes

```
1. Dataset publicado en v1.0.0 (DOI: 10.9999/dataset.v1)
2. Editar metadatos, elegir PATCH → v1.0.1 (parche, sin DOI)
3. Editar metadatos, elegir PATCH → v1.0.2 (parche, sin DOI)
4. Editar metadatos, elegir MINOR → v1.1.0 (menor, sin DOI)
5. Editar metadatos, elegir PATCH → v1.1.1 (parche, sin DOI)


Version History shows:
- 🔧 v1.1.1 - Patch version ✓ Current
- 📝 v1.1.0 - Minor version
- 🔧 v1.0.2 - Patch version
- 🔧 v1.0.1 - Patch version
- 📌 v1.0.0 (DOI: 10.9999/dataset.v1) - Published in Zenodo
```


### Example 3: Published Dataset with File Changes

```
1. Dataset publicado en v1.0.0 (DOI: 10.9999/dataset.v1)
2. Editar metadatos, elegir MINOR → v1.1.0 (menor, sin DOI)
3. Editar metadatos, elegir PATCH → v1.1.1 (parche, sin DOI)
4. Añadir nuevo archivo, guardar → Archivos guardados localmente, mensaje: "Requiere republicación"
5. Republicar en Zenodo → v2.0.0 (mayor, DOI: 10.9999/dataset.v2)


Version History shows:
- 📌 v2.0.0 (DOI: 10.9999/dataset.v2) - Published in Zenodo ✓ Current
- 🔧 v1.1.1 - Patch version
- 📝 v1.1.0 - Minor version
- 📌 v1.0.0 (DOI: 10.9999/dataset.v1) - Published in Zenodo
```


## Complete Technical Implementation

### Database Schema

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


**Key field: `version_doi`**
- `NULL` = Local, Minor, or Patch Version (no DOI)
- `NOT NULL` = Major Version (published in Zenodo with DOI)

**Migración de Base de Datos:**
```python
# migrations/versions/2ff2c8b0a045_add_version_doi_field.py
def upgrade():
    op.add_column('data_set_version',
        sa.Column('version_doi', sa.String(length=120), nullable=True))

def downgrade():
    op.drop_column('data_set_version', 'version_doi')
```


### Manual Version Creation Restrictions

**Block for Published Datasets:**
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


### Version Display Logic

**In list_versions.html:**
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


**Differentiation logic:**
1. If `version.version_doi` exists → Major Version (with DOI)
2. If dataset has DOI AND version >= 1.x.x → Minor/Patch Version (post-publication)
    - If second number > 0 (X.Y.0 where Y > 0) → Minor Version
    - Else → Patch Version
3. Else → Local Version (pre-publication)


### Integration with Zenodo/Fakenodo

**File Synchronization Before Publishing:**
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


**Detection of New Version:**
```python
# Publicar en Zenodo
publish_response = zenodo_service.publish_deposition(deposition_id)
new_deposition_id = publish_response.get("id")

# Si Zenodo creó nueva deposición, detectó cambios de archivos
if new_deposition_id != old_deposition_id:
    # Nueva versión mayor creada
    deposition_id = new_deposition_id
```


## User Interface

### Version History Page


**Header Section (for published datasets):**
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


**Version List:**
- Each version shown in a card with color-coded header
- Version badge (v1.0.0, v1.1.0, etc.) in large font
- "Current" badge on the latest version
- Type badge (📌 Major / 📝 Minor / 🔧 Patch / 📦 Local)
- DOI field with copy button (major versions only)
- Changelog display
- Action buttons: Compare, View
- Statistics (features, constraints, models)


**Version Card Style:**
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


### Edit Dataset Page

**For Unpublished Datasets:**
```html
<!-- edit_dataset.html líneas 30-34 -->
<div class="alert alert-info">
    <i data-feather="info"></i>
    <strong>Auto-versionado habilitado:</strong> Los cambios crearán una nueva versión local automáticamente.
</div>
```


**For Published Datasets:**
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


**JavaScript for File Monitoring:**
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


### Create New Version Modal (Unpublished Only)

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


## DOI System

### Conceptual DOI
- One per dataset, never changes
- Always points to the latest published version
- Format: `10.9999/dataset-identifier` (without `.vX`)
- Shown in the version history header
- Stored in `DSMetaData.dataset_doi`

### Specific Version DOI
- One per major version
- Permanently linked to the files of that version
- Format: `10.9999/dataset-identifier.v1`, `.v2`, `.v3`, etc.
- Stored in `DatasetVersion.version_doi`
- Used for citations to ensure reproducibility

**Relationship between DOIs:**
```
DOI Conceptual:      10.9999/fakenodo.a843b04d
                              ↓
                    Siempre redirige a última versión
                              ↓
DOIs de Versión:     10.9999/fakenodo.a843b04d.v1 (Primera publicación)
                     10.9999/fakenodo.a843b04d.v2 (Republicación con archivos)
                     10.9999/fakenodo.a843b04d.v3 (Otra republicación)
```


## Best Practices

### For Users

**During Development (before publication):**
- Use local versions to track your progress
- Choose version types (PATCH/MINOR/MAJOR) to organize changes
- Version numbers are for your reference only
- Don't worry about "wasting" version numbers

**After Publication:**
- Use PATCH for typo fixes, minor corrections
- Use MINOR for substantial metadata improvements (better descriptions, new tags)
- Add files and republish for MAJOR versions (new DOI)
- Always add meaningful changelog messages

**For Citations:**
- Use specific version DOI for reproducibility
- Use conceptual DOI to reference "the dataset" in general

### For Developers

**Adding New Version Types:**
1. Add badge logic in `list_versions.html`
2. Update version creation in `routes.py`
3. Update UI selectors in `edit_dataset.html`
4. Add tests in `test_versions.py`
5. Document in this file

**Modifying Versioning Logic:**
1. Update `VersionService.create_version()`
2. Update auto-versioning in `edit_dataset` route
3. Update display logic in templates
4. Run the full test suite
5. Update documentation

## Testing

Run versioning-related tests:
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


**Current coverage:** 83 tests passing

**Important tests:**
- `test_publish_dataset_success` - First publication
- `test_publish_dataset_already_published` - Republishing without changes
- `test_publish_after_changing_files_creates_new_version_and_doi` - Republishing with files
- `test_cannot_create_version_after_publish` - Manual version block
- `test_captures_new_deposition_id_from_response` - Capture of new ID


## Future Improvements

Possible improvements to consider:

1. **UI de Comparación de Versiones**: Mostrar diffs detallados entre versiones
2. **Ramificación de Versiones**: Permitir crear versiones desde versiones no-últimas
3. **Etiquetas de Versión**: Etiquetas personalizadas para versiones (ej: "stable", "beta")
4. **Changelog Automatizado**: Generar changelog desde cambios detectados
5. **Analíticas de Versiones**: Rastrear qué versiones son más accedidas
6. **Operaciones Masivas de Versiones**: Revertir, fusionar o archivar múltiples versiones
7. **Comentarios de Versión**: Permitir hilos de discusión en versiones
8. **Exportación de Versión**: Exportar metadatos de versión y changelog como PDF


## Related Files

### Backend
- `app/modules/dataset/routes.py` - Main versioning logic
- `app/modules/dataset/models.py` - DatasetVersion model
- `core/services/VersionService.py` - Version creation service
- `app/modules/fakenodo/services.py` - Zenodo integration

### Frontend
- `app/modules/dataset/templates/dataset/list_versions.html` - Version history UI
- `app/modules/dataset/templates/dataset/edit_dataset.html` - Edit form with versioning
- `app/modules/dataset/templates/dataset/view_dataset.html` - Dataset view

### Tests
- `app/modules/dataset/tests/test_versions.py` - Versioning functionality tests
- `app/modules/dataset/tests/test_republication.py` - Republishing tests
- `app/modules/fakenodo/tests/test_fakenodo_integration.py` - Zenodo integration tests

### Database
- `migrations/versions/2ff2c8b0a045_add_version_doi_field.py` - Migration adding version_doi


## Support

For questions or issues:
- Check logs: `app.log.*` files
- Review test cases for examples
- See `docs/zenodo.md` for Zenodo-specific documentation
- See `docs/fakenodo.md` for local testing with Fakenodo


## Summary of Implemented Changes

### Database Changes
1. ✅ Added `version_doi` field to `data_set_version` table
2. ✅ Migration applied: `2ff2c8b0a045_add_version_doi_field`

### Backend Changes
1. ✅ `routes.py::publish_dataset()` - Captures new deposition_id and DOI
2. ✅ `routes.py::publish_dataset()` - Synchronizes files before publishing
3. ✅ `routes.py::publish_dataset()` - Auto-creates DatasetVersion with DOI
4. ✅ `routes.py::edit_dataset()` - Differentiates metadata vs file changes
5. ✅ `routes.py::edit_dataset()` - Auto-creates MINOR/PATCH versions for metadata
6. ✅ `routes.py::create_version()` - Blocks manual versions for published datasets
7. ✅ `models.py::DatasetVersion` - Added version_doi field and to_dict()

### Frontend Changes
1. ✅ `list_versions.html` - Visual differentiation of version types
2. ✅ `list_versions.html` - Conceptual DOI vs Version Types section
3. ✅ `list_versions.html` - Color-coded badges with better texts
4. ✅ `list_versions.html` - Simplified create version modal for pre-publication
5. ✅ `edit_dataset.html` - MINOR/PATCH version type selector
6. ✅ `edit_dataset.html` - JavaScript warning when files are added
7. ✅ `edit_dataset.html` - Auto-versioning message for unpublished datasets

### Tests
1. ✅ `test_republication.py` - 4 tests for deposition_id capture
2. ✅ `test_versions.py` - Updated test for full MockZenodoService
3. ✅ 83/83 tests passing

### Documentation
1. ✅ `docs/versioning-system.md` - Complete documentation in Spanish with implementation
