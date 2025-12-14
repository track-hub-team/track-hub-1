
# Comment Moderation System

## General Description

The Track Hub comment system includes a moderation mechanism that allows dataset owners to manage comments on their posts. Owners act as **moderators** with the ability to delete (but not edit) comments from other users on their datasets.

## Location

- **Service**: `app/modules/dataset/services.py` → `CommentService`
- **Repository**: `app/modules/dataset/repositories.py` → `CommentRepository`
- **Routes**: `app/modules/dataset/routes.py` → Comment endpoints
- **Models**: `app/modules/dataset/models.py` → `Comment`
- **Tests**: `app/modules/dataset/tests/test_comment_logic.py`


## System Architecture

### Comment Model

```python
class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('data_set.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dataset = db.relationship('DataSet', backref='comments')
    user = db.relationship('User', backref='comments')
```


### CommentService

Main service that manages all business logic for comments:

```python
class CommentService(BaseService):
    def __init__(self):
        super().__init__(CommentRepository())
        self.dataset_repository = DataSetRepository()
```


## Main Features

### 1. Create Comment

```python
def create_comment(self, dataset_id: int, user_id: int, content: str) -> dict:
    """

    Create a new comment on a dataset.

    Validations:
    - Non-empty content
    - Maximum length 1000 characters
    - HTML/XSS sanitization
    - Existing dataset
    """

    # Validate and sanitize content
    clean_content = self._validate_content(content)

    # Check that the dataset exists
    dataset = self.dataset_repository.get_by_id(dataset_id)
    if not dataset:
        raise ValueError("Dataset not found")

    # Create comment
    comment = self.repository.create(
        dataset_id=dataset_id,
        user_id=user_id,
        content=clean_content
    )

    return comment.to_dict()
```

**Implemented validations**:
- ✅ Non-empty content (strip spaces)
- ✅ Minimum length: 1 character
- ✅ Maximum length: 1000 characters
- ✅ HTML sanitization with `html.escape()`
- ✅ Dataset must exist


### 2. Delete Comment (with Moderation)

```python
def delete_comment(self, comment_id: int, user_id: int) -> bool:
    """

    Delete a comment.

    Permissions:
    - The comment author can delete it
    - The dataset owner can delete it (moderation)
    - Other users CANNOT delete it
    """

    comment = self.repository.get_by_id(comment_id)
    if not comment:
        raise ValueError("Comment not found")


    # Check permissions
    is_owner = self._is_comment_owner(comment, user_id)
    is_moderator = self._is_dataset_owner(comment, user_id)

    if not (is_owner or is_moderator):
        raise PermissionError("You don't have permission to delete this comment")

    return self.repository.delete(comment_id)
```

**Permission system**:
- ✅ **Comment author**: Can delete their own comment
- ✅ **Dataset owner (moderator)**: Can delete any comment in their dataset
- ❌ **Other users**: No permission


### 3. Edit Comment (Author Only)

```python
def update_comment(self, comment_id: int, user_id: int, new_content: str) -> dict:
    """

    Update the content of a comment.

    Permissions:
    - ONLY the comment author can edit it
    - The moderator CANNOT edit others' comments
    """

    comment = self.repository.get_by_id(comment_id)
    if not comment:
        raise ValueError("Comment not found")


    # Check that the user is the author (moderator CANNOT edit)
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

**Important rule**: Moderators can **delete** but NOT **edit** others' comments.


### 4. Permission Verification Methods

#### Check comment owner

```python
def _is_comment_owner(self, comment, user_id: int) -> bool:
    """Check if the user is the author of the comment."""
    return comment.user_id == user_id
```


#### Check moderator (dataset owner)

```python
def _is_dataset_owner(self, comment, user_id: int) -> bool:
    """Check if the user is the owner of the dataset (moderator)."""
    dataset = self.dataset_repository.get_by_id(comment.dataset_id)
    if not dataset:
        return False
    return dataset.user_id == user_id
```


### 5. Validation and Sanitization

```python
def _validate_content(self, content: str) -> str:
    """

    Validate and sanitize the content of a comment.

    Protections:
    - XSS: html.escape() converts <script> to &lt;script&gt;
    - Injection: Escaping special characters
    - Limits: Length validation
    """

    # Remove whitespace
    clean_content = content.strip() if content else ""

    # Check not empty
    if not clean_content:
        raise ValueError("Comment content cannot be empty")

    # Check max length (1000 characters)
    if len(clean_content) > 1000:
        raise ValueError("Comment content too long (max 1000 characters)")

    # Sanitize HTML (prevent XSS)
    import html
    clean_content = html.escape(clean_content)

    return clean_content
```


## HTTP Endpoints


### POST /dataset/{dataset_id}/comments
Create new comment (requires authentication).

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
List comments (public, does not require authentication).

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
Delete comment (author or moderator).

**Response (200)**:
```json
{
  "success": true,
  "message": "Comment deleted successfully"
}
```

**Response (403)** - No permission:
```json
{
  "success": false,
  "message": "You don't have permission to delete this comment"
}
```


### PUT /dataset/comments/{comment_id}
Update comment (author only).

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


## Moderation System


### Permissions Matrix

| Action | Comment Author | Dataset Owner | Other Users |
|--------|---------------|--------------|-------------|
| **View comments** | ✅ Yes | ✅ Yes | ✅ Yes (public) |
| **Create comment** | ✅ Yes | ✅ Yes | ✅ Yes (authenticated) |
| **Edit comment** | ✅ Only own | ❌ No | ❌ No |
| **Delete comment** | ✅ Only own | ✅ Any in their dataset | ❌ No |


### Moderation Use Cases

#### Case 1: User comments on their own dataset
```python
# User1 creates dataset
dataset = create_dataset(user_id=user1)

# User1 comments on their own dataset
comment = create_comment(dataset_id=dataset.id, user_id=user1)

# User1 can:
✅ Edit the comment (is author)
✅ Delete the comment (is author AND moderator)
```

#### Case 2: User comments on someone else's dataset
```python
# User1 creates dataset
dataset = create_dataset(user_id=user1)

# User2 comments on User1's dataset
comment = create_comment(dataset_id=dataset.id, user_id=user2)

# User2 can:
✅ Edit the comment (is author)
✅ Delete the comment (is author)

# User1 can:
❌ Edit the comment (NOT author)
✅ Delete the comment (is moderator)
```

#### Case 3: Third party tries to delete
```python
# User1 creates dataset
dataset = create_dataset(user_id=user1)

# User2 comments
comment = create_comment(dataset_id=dataset.id, user_id=user2)

# User3 tries to delete
delete_comment(comment.id, user_id=user3)
# ❌ PermissionError: "You don't have permission to delete this comment"
```


## Testing


### Test Location

`app/modules/dataset/tests/test_comment_logic.py` (389 lines)


### Test Coverage

#### Moderation Tests

```python
def test_delete_comment_dataset_owner(app, dataset, user, user2, comment_service):
    """Test delete comment as dataset owner (moderator)."""
    # user2 comments on user's dataset
    comment = comment_repository.create(
        dataset_id=dataset,
        user_id=user2,
        content="Comment by user2"
    )

    # user (dataset owner) can delete it
    result = comment_service.delete_comment(comment.id, user)
    assert result is True

def test_update_comment_dataset_owner_cannot_edit(app, dataset, user, user2):
    """Test dataset owner CANNOT edit others' comments."""
    comment = comment_repository.create(
        dataset_id=dataset,
        user_id=user2,
        content="Original"
    )

    # user (moderator) CANNOT edit the comment
    with pytest.raises(PermissionError):
        comment_service.update_comment(comment.id, user, "Edited by moderator")
```


### Running Tests

```bash
# All comment tests
pytest app/modules/dataset/tests/test_comment_logic.py -v

# Only moderation tests
pytest app/modules/dataset/tests/test_comment_logic.py -v -k "moderator or dataset_owner"

# With coverage
pytest app/modules/dataset/tests/test_comment_logic.py --cov=app.modules.dataset
```


## Security

### XSS Protection

```python
# Malicious input
malicious = '<script>alert("XSS")</script>Hello'

# After sanitization
safe = '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;Hello'
```


### Access Control

```python
# Check BEFORE any destructive operation
if not (is_owner or is_moderator):
    raise PermissionError("Access denied")
```


## Conclusion

The moderation system implements a robust model where:

- ✅ **Authors** have full control over their comments
- ✅ **Moderators** can delete inappropriate comments
- ✅ **Moderators CANNOT edit** others' comments
- ✅ Thorough validation and sanitization against XSS
- ✅ Complete testing with 20+ test cases
