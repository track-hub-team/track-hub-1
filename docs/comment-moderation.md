# Sistema de Moderación de Comentarios

## Descripción General

El sistema de comentarios de Track Hub incluye un mecanismo de moderación que permite a los propietarios de datasets gestionar los comentarios en sus publicaciones. Los propietarios actúan como **moderadores** con capacidad de eliminar (pero no editar) comentarios de otros usuarios en sus datasets.

## Ubicación

- **Servicio**: `app/modules/dataset/services.py` → `CommentService`
- **Repositorio**: `app/modules/dataset/repositories.py` → `CommentRepository`
- **Rutas**: `app/modules/dataset/routes.py` → Endpoints de comentarios
- **Modelos**: `app/modules/dataset/models.py` → `Comment`
- **Tests**: `app/modules/dataset/tests/test_comment_logic.py`

## Arquitectura del Sistema

### Modelo Comment

```python
class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('data_set.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    dataset = db.relationship('DataSet', backref='comments')
    user = db.relationship('User', backref='comments')
```

### CommentService

Servicio principal que gestiona toda la lógica de negocio de comentarios:

```python
class CommentService(BaseService):
    def __init__(self):
        super().__init__(CommentRepository())
        self.dataset_repository = DataSetRepository()
```

## Funcionalidades Principales

### 1. Crear Comentario

```python
def create_comment(self, dataset_id: int, user_id: int, content: str) -> dict:
    """
    Crear un nuevo comentario en un dataset.

    Validaciones:
    - Contenido no vacío
    - Longitud máxima 1000 caracteres
    - Sanitización HTML/XSS
    - Dataset existente
    """

    # Validar y sanitizar contenido
    clean_content = self._validate_content(content)

    # Verificar que existe el dataset
    dataset = self.dataset_repository.get_by_id(dataset_id)
    if not dataset:
        raise ValueError("Dataset not found")

    # Crear comentario
    comment = self.repository.create(
        dataset_id=dataset_id,
        user_id=user_id,
        content=clean_content
    )

    return comment.to_dict()
```

**Validaciones implementadas**:
- ✅ Contenido no vacío (strip de espacios)
- ✅ Longitud mínima: 1 carácter
- ✅ Longitud máxima: 1000 caracteres
- ✅ Sanitización HTML con `html.escape()`
- ✅ Dataset debe existir

### 2. Eliminar Comentario (con Moderación)

```python
def delete_comment(self, comment_id: int, user_id: int) -> bool:
    """
    Eliminar un comentario.

    Permisos:
    - El autor del comentario puede eliminarlo
    - El propietario del dataset puede eliminarlo (moderación)
    - Otros usuarios NO pueden eliminarlo
    """

    comment = self.repository.get_by_id(comment_id)
    if not comment:
        raise ValueError("Comment not found")

    # Verificar permisos
    is_owner = self._is_comment_owner(comment, user_id)
    is_moderator = self._is_dataset_owner(comment, user_id)

    if not (is_owner or is_moderator):
        raise PermissionError("You don't have permission to delete this comment")

    return self.repository.delete(comment_id)
```

**Sistema de permisos**:
- ✅ **Autor del comentario**: Puede eliminar su propio comentario
- ✅ **Propietario del dataset (moderador)**: Puede eliminar cualquier comentario en su dataset
- ❌ **Otros usuarios**: No tienen permiso

### 3. Editar Comentario (Solo Autor)

```python
def update_comment(self, comment_id: int, user_id: int, new_content: str) -> dict:
    """
    Actualizar el contenido de un comentario.

    Permisos:
    - SOLO el autor del comentario puede editarlo
    - El moderador NO puede editar comentarios ajenos
    """

    comment = self.repository.get_by_id(comment_id)
    if not comment:
        raise ValueError("Comment not found")

    # Verificar que es el autor (moderador NO puede editar)
    if not self._is_comment_owner(comment, user_id):
        raise PermissionError("Only the comment author can edit it")

    # Validar y sanitizar nuevo contenido
    clean_content = self._validate_content(new_content)

    # Actualizar
    updated = self.repository.update_content(comment_id, clean_content)
    if not updated:
        raise ValueError("Failed to update comment")

    return updated.to_dict()
```

**Regla importante**: Los moderadores pueden **eliminar** pero NO **editar** comentarios ajenos.

### 4. Métodos de Verificación de Permisos

#### Verificar propietario del comentario

```python
def _is_comment_owner(self, comment, user_id: int) -> bool:
    """Verificar si el usuario es el autor del comentario."""
    return comment.user_id == user_id
```

#### Verificar moderador (propietario del dataset)

```python
def _is_dataset_owner(self, comment, user_id: int) -> bool:
    """Verificar si el usuario es el propietario del dataset (moderador)."""
    dataset = self.dataset_repository.get_by_id(comment.dataset_id)
    if not dataset:
        return False
    return dataset.user_id == user_id
```

### 5. Validación y Sanitización

```python
def _validate_content(self, content: str) -> str:
    """
    Validar y sanitizar el contenido de un comentario.

    Protecciones:
    - XSS: html.escape() convierte <script> en &lt;script&gt;
    - Inyección: Escapado de caracteres especiales
    - Límites: Validación de longitud
    """

    # Eliminar espacios en blanco
    clean_content = content.strip() if content else ""

    # Verificar que no esté vacío
    if not clean_content:
        raise ValueError("Comment content cannot be empty")

    # Verificar longitud máxima (1000 caracteres)
    if len(clean_content) > 1000:
        raise ValueError("Comment content too long (max 1000 characters)")

    # Sanitizar HTML (evitar XSS)
    import html
    clean_content = html.escape(clean_content)

    return clean_content
```

## Endpoints HTTP

### POST /dataset/{dataset_id}/comments
Crear nuevo comentario (requiere autenticación).

**Request**:
```json
{
  "content": "Great dataset! Very useful GPS tracks."
}
```

**Response (201)**:
```json
{
  "success": true,
  "comment": {
    "id": 123,
    "dataset_id": 45,
    "user_id": 67,
    "content": "Great dataset! Very useful GPS tracks.",
    "created_at": "2025-12-06T10:30:00Z",
    "updated_at": "2025-12-06T10:30:00Z"
  }
}
```

### GET /dataset/{dataset_id}/comments
Listar comentarios (público, no requiere autenticación).

**Response (200)**:
```json
{
  "success": true,
  "comments": [
    {
      "id": 123,
      "dataset_id": 45,
      "user_id": 67,
      "user_name": "John Doe",
      "content": "Great dataset!",
      "created_at": "2025-12-06T10:30:00Z"
    }
  ]
}
```

### DELETE /dataset/comments/{comment_id}
Eliminar comentario (autor o moderador).

**Response (200)**:
```json
{
  "success": true,
  "message": "Comment deleted successfully"
}
```

**Response (403)** - Sin permisos:
```json
{
  "success": false,
  "message": "You don't have permission to delete this comment"
}
```

### PUT /dataset/comments/{comment_id}
Actualizar comentario (solo autor).

**Request**:
```json
{
  "content": "Updated comment content"
}
```

**Response (200)**:
```json
{
  "success": true,
  "comment": {
    "id": 123,
    "content": "Updated comment content",
    "updated_at": "2025-12-06T12:00:00Z"
  }
}
```

## Sistema de Moderación

### Matriz de Permisos

| Acción | Autor del Comentario | Propietario del Dataset | Otros Usuarios |
|--------|---------------------|------------------------|----------------|
| **Ver comentarios** | ✅ Sí | ✅ Sí | ✅ Sí (público) |
| **Crear comentario** | ✅ Sí | ✅ Sí | ✅ Sí (autenticado) |
| **Editar comentario** | ✅ Solo el propio | ❌ No | ❌ No |
| **Eliminar comentario** | ✅ Solo el propio | ✅ Cualquiera en su dataset | ❌ No |

### Casos de Uso de Moderación

#### Caso 1: Usuario comenta en su propio dataset
```python
# User1 crea dataset
dataset = create_dataset(user_id=user1)

# User1 comenta en su dataset
comment = create_comment(dataset_id=dataset.id, user_id=user1)

# User1 puede:
✅ Editar el comentario (es autor)
✅ Eliminar el comentario (es autor Y moderador)
```

#### Caso 2: Usuario comenta en dataset ajeno
```python
# User1 crea dataset
dataset = create_dataset(user_id=user1)

# User2 comenta en dataset de User1
comment = create_comment(dataset_id=dataset.id, user_id=user2)

# User2 puede:
✅ Editar el comentario (es autor)
✅ Eliminar el comentario (es autor)

# User1 puede:
❌ Editar el comentario (NO es autor)
✅ Eliminar el comentario (es moderador)
```

#### Caso 3: Tercero intenta eliminar
```python
# User1 crea dataset
dataset = create_dataset(user_id=user1)

# User2 comenta
comment = create_comment(dataset_id=dataset.id, user_id=user2)

# User3 intenta eliminar
delete_comment(comment.id, user_id=user3)
# ❌ PermissionError: "You don't have permission to delete this comment"
```

## Testing

### Ubicación de Tests

`app/modules/dataset/tests/test_comment_logic.py` (389 líneas)

### Cobertura de Tests

#### Tests de Moderación

```python
def test_delete_comment_dataset_owner(app, dataset, user, user2, comment_service):
    """Test eliminar comentario siendo el propietario del dataset (moderador)."""
    # user2 comenta en el dataset de user
    comment = comment_repository.create(
        dataset_id=dataset,
        user_id=user2,
        content="Comment by user2"
    )

    # user (propietario del dataset) puede eliminarlo
    result = comment_service.delete_comment(comment.id, user)
    assert result is True

def test_update_comment_dataset_owner_cannot_edit(app, dataset, user, user2):
    """Test propietario del dataset NO puede editar comentarios ajenos."""
    comment = comment_repository.create(
        dataset_id=dataset,
        user_id=user2,
        content="Original"
    )

    # user (moderador) NO puede editar el comentario
    with pytest.raises(PermissionError):
        comment_service.update_comment(comment.id, user, "Edited by moderator")
```

### Ejecutar Tests

```bash
# Todos los tests de comentarios
pytest app/modules/dataset/tests/test_comment_logic.py -v

# Solo tests de moderación
pytest app/modules/dataset/tests/test_comment_logic.py -v -k "moderator or dataset_owner"

# Con cobertura
pytest app/modules/dataset/tests/test_comment_logic.py --cov=app.modules.dataset
```

## Seguridad

### Protección contra XSS

```python
# Entrada maliciosa
malicious = '<script>alert("XSS")</script>Hello'

# Después de sanitización
safe = '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;Hello'
```

### Control de Acceso

```python
# Verificación ANTES de cualquier operación destructiva
if not (is_owner or is_moderator):
    raise PermissionError("Access denied")
```

## Conclusión

El sistema de moderación implementa un modelo robusto donde:

- ✅ Los **autores** tienen control total sobre sus comentarios
- ✅ Los **moderadores** pueden eliminar comentarios inapropiados
- ✅ Los **moderadores NO pueden editar** comentarios ajenos
- ✅ Validación y sanitización exhaustiva contra XSS
- ✅ Testing completo con 20+ casos de prueba
