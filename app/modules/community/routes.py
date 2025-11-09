from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.modules.community import community_bp
from app.modules.community.services import CommunityService

community_service = CommunityService()


@community_bp.route("/community/list")
def list_communities():
    query = request.args.get("query", "")
    communities = community_service.get_all(query if query else None)
    return render_template("community/list.html", communities=communities, query=query)


@community_bp.route("/community/<int:community_id>")
def view(community_id):
    community = community_service.repository.get_by_id(community_id)
    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    datasets = community_service.get_community_datasets(community_id)
    is_curator = current_user.is_authenticated and community_service.is_curator(community_id, current_user.id)
    return render_template("community/view.html", community=community, datasets=datasets, is_curator=is_curator)
