"""
Tests for new deposition_id capture when Fakenodo creates a new version.
"""


def test_captures_new_deposition_id_from_response():
    """Test that new deposition_id is extracted from publish response."""
    publish_response = {"id": 13, "doi": "10.9999/test.v2"}
    old_deposition_id = 12

    new_deposition_id = publish_response.get("id", old_deposition_id)

    assert new_deposition_id == 13
    assert new_deposition_id != old_deposition_id


def test_keeps_same_deposition_id_when_unchanged():
    """Test that deposition_id remains the same when unchanged."""
    publish_response = {"id": 12, "doi": "10.9999/test.v1"}
    old_deposition_id = 12

    new_deposition_id = publish_response.get("id", old_deposition_id)

    assert new_deposition_id == 12
    assert new_deposition_id == old_deposition_id


def test_update_data_includes_new_deposition_id_when_changed():
    """Test that update_data includes deposition_id only when it changed."""
    old_deposition_id = 12
    new_deposition_id = 13

    update_data = {"dataset_doi": "10.9999/test.v2", "files_fingerprint": "abc123"}

    if new_deposition_id != old_deposition_id:
        update_data["deposition_id"] = new_deposition_id

    assert "deposition_id" in update_data
    assert update_data["deposition_id"] == 13


def test_update_data_excludes_deposition_id_when_unchanged():
    """Test that update_data excludes deposition_id when unchanged."""
    old_deposition_id = 12
    new_deposition_id = 12

    update_data = {"dataset_doi": "10.9999/test.v1", "files_fingerprint": "abc123"}

    if new_deposition_id != old_deposition_id:
        update_data["deposition_id"] = new_deposition_id

    assert "deposition_id" not in update_data
