"""
API endpoints for community module.
"""

from flask import jsonify, request
from flask_login import current_user, login_required

from app.modules.community import community_bp
from app.modules.community.services import CommunityService

community_service = CommunityService()


@community_bp.route("/api/v1/communities/<int:community_id>/approve/<int:dataset_id>", methods=["POST"])
@login_required
def api_approve_dataset(community_id, dataset_id):
    """
    Approve a dataset request for a community.
    """
    # Buscar el request pendiente para este community y dataset
    pending_request = community_service.request_repository.get_pending_request_by_dataset(community_id, dataset_id)

    if not pending_request:
        return jsonify({"success": False, "message": "No pending request found for this dataset"}), 404

    # Aprobar la solicitud
    success, error = community_service.approve_request(pending_request.id, current_user.id)

    if success:
        return jsonify({"success": True, "message": "Dataset approved successfully"})
    else:
        return jsonify({"success": False, "message": error}), 400


@community_bp.route("/api/v1/communities/<int:community_id>/reject/<int:dataset_id>", methods=["POST"])
@login_required
def api_reject_dataset(community_id, dataset_id):
    """
    Reject a dataset request for a community.
    """
    # Get optional rejection reason from request body
    data = request.get_json() or {}
    reason = data.get("reason", "")

    # Buscar el request pendiente para este community y dataset
    pending_request = community_service.request_repository.get_pending_request_by_dataset(community_id, dataset_id)

    if not pending_request:
        return jsonify({"success": False, "message": "No pending request found for this dataset"}), 404

    # Rechazar la solicitud
    success, error = community_service.reject_request(pending_request.id, current_user.id, reason)

    if success:
        return jsonify({"success": True, "message": "Dataset rejected successfully"})
    else:
        return jsonify({"success": False, "message": error}), 400


@community_bp.route("/api/v1/communities", methods=["GET"])
def api_list_communities():
    """
    List all communities with optional search.
    """
    query = request.args.get("search", "").lower()

    if query:
        communities = community_service.search_communities(query)
    else:
        communities = community_service.get_all()

    return jsonify([c.to_dict() for c in communities])


@community_bp.route("/api/v1/communities/<int:community_id>", methods=["GET"])
def api_get_community(community_id):
    """
    Get a single community by ID.
    """
    community = community_service.get_by_id(community_id)

    if not community:
        return jsonify({"error": "Community not found"}), 404

    return jsonify(community.to_dict())
