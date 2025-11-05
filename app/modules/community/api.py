"""
API endpoints for community module.
"""

from flask import jsonify, request
from flask_login import login_required

from app.modules.community import community_bp


@community_bp.route("/api/v1/communities/<int:community_id>/approve/<int:dataset_id>", methods=["POST"])
@login_required
def api_approve_dataset(community_id, dataset_id):
    """
    Approve a dataset request for a community.
    TODO: Add curator permission check and call community_service.approve_request()
    """
    # TODO: Check if current_user is curator of the community
    # if not community_service.is_curator(community_id, current_user.id):
    #     return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    # TODO: Call backend service
    # try:
    #     community_service.approve_request(request_id, current_user.id)
    #     return jsonify({'success': True, 'message': 'Dataset approved successfully'})
    # except Exception as e:
    #     return jsonify({'success': False, 'message': str(e)}), 400

    # MOCK response
    return jsonify({"success": True, "message": f"Dataset {dataset_id} approved for community {community_id} (Mock)"})


@community_bp.route("/api/v1/communities/<int:community_id>/reject/<int:dataset_id>", methods=["POST"])
@login_required
def api_reject_dataset(community_id, dataset_id):
    """
    Reject a dataset request for a community.
    TODO: Add curator permission check and call community_service.reject_request()
    """
    # Get optional rejection reason from request body
    data = request.get_json() or {}
    reason = data.get("reason", "")  # noqa: F841 - will be used when backend is implemented

    # TODO: Check if current_user is curator of the community
    # if not community_service.is_curator(community_id, current_user.id):
    #     return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    # TODO: Call backend service
    # try:
    #     community_service.reject_request(request_id, current_user.id, reason)
    #     return jsonify({'success': True, 'message': 'Dataset rejected successfully'})
    # except Exception as e:
    #     return jsonify({'success': False, 'message': str(e)}), 400

    # MOCK response
    return jsonify({"success": True, "message": f"Dataset {dataset_id} rejected for community {community_id} (Mock)"})


@community_bp.route("/api/v1/communities", methods=["GET"])
def api_list_communities():
    """
    List all communities with optional search.
    TODO: Replace with community_service.get_all() when backend is ready.
    """
    from app.modules.community.mock_data import MOCK_COMMUNITIES

    query = request.args.get("search", "").lower()

    # MOCK: Filter communities
    if query:
        communities = [c for c in MOCK_COMMUNITIES if query in c["name"].lower() or query in c["description"].lower()]
    else:
        communities = MOCK_COMMUNITIES

    return jsonify(communities)


@community_bp.route("/api/v1/communities/<int:community_id>", methods=["GET"])
def api_get_community(community_id):
    """
    Get a single community by ID.
    TODO: Replace with community_service.get_by_id() when backend is ready.
    """
    from app.modules.community.mock_data import MOCK_COMMUNITIES

    community = next((c for c in MOCK_COMMUNITIES if c["id"] == community_id), None)

    if not community:
        return jsonify({"error": "Community not found"}), 404

    return jsonify(community)
