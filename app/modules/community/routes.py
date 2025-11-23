import os

from flask import flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app.modules.community import community_bp
from app.modules.community.forms import CommunityForm, ProposeDatasetForm
from app.modules.community.services import CommunityService

community_service = CommunityService()


@community_bp.route("/community", methods=["GET"])
def index():
    """Redirect to list view"""
    return redirect(url_for("community.list_communities"))


@community_bp.route("/community/list", methods=["GET"])
def list_communities():
    """List all communities with search functionality"""
    query = request.args.get("query", "")

    communities = community_service.get_all(query if query else None)

    return render_template("community/list.html", communities=communities, query=query)


@community_bp.route("/community/<string:slug>", methods=["GET"])
def view(slug):
    """View a single community with its datasets"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Get datasets from the community
    datasets = community_service.get_community_datasets(community.id)

    # Check if current user is curator
    is_curator = False
    if current_user.is_authenticated:
        is_curator = community_service.is_curator(community.id, current_user.id)

    return render_template("community/view.html", community=community, datasets=datasets, is_curator=is_curator)


@community_bp.route("/community/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new community"""
    form = CommunityForm()

    if form.validate_on_submit():
        community, error = community_service.create_community(
            name=form.name.data,
            description=form.description.data,
            creator_id=current_user.id,
            logo_file=form.logo.data if form.logo.data else None,
        )

        if error:
            flash(f"Error creating community: {error}", "error")
            return render_template("community/create.html", form=form)

        flash(f'Community "{community.name}" created successfully!', "success")
        return redirect(url_for("community.view", slug=community.slug))

    return render_template("community/create.html", form=form)


@community_bp.route("/community/<string:slug>/manage", methods=["GET"])
@login_required
def manage(slug):
    """Manage community (for curators only)"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Check if user is curator
    if not community_service.is_curator(community.id, current_user.id):
        flash("Only curators can manage this community", "error")
        return redirect(url_for("community.view", slug=slug))

    # Get pending requests
    pending_requests = community_service.get_pending_requests(community.id)

    return render_template("community/manage.html", community=community, requests=pending_requests)


@community_bp.route("/community/<string:slug>/propose", methods=["GET", "POST"])
@login_required
def propose_dataset(slug):
    """Propose a dataset to be added to a community"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Get user's datasets
    user_datasets = community_service.get_user_datasets(current_user.id)

    if not user_datasets:
        flash("You need to have at least one dataset to propose to a community", "warning")
        return redirect(url_for("community.view", slug=slug))

    # Create form and populate dataset choices
    form = ProposeDatasetForm()
    form.dataset_id.choices = [(dataset.id, dataset.ds_meta_data.title) for dataset in user_datasets]

    if form.validate_on_submit():
        dataset_id = form.dataset_id.data
        message = form.message.data

        success, error = community_service.propose_dataset(
            community_id=community.id, dataset_id=dataset_id, requester_id=current_user.id, message=message
        )

        if error:
            flash(f"Error submitting proposal: {error}", "error")
            return redirect(url_for("community.propose_dataset", slug=slug))

        selected_dataset = next((d for d in user_datasets if d.id == dataset_id), None)
        flash(f'Proposal for dataset "{selected_dataset.ds_meta_data.title}" submitted successfully!', "success")
        return redirect(url_for("community.view", slug=slug))

    # Convert datasets to dict for JSON serialization
    datasets_dict = [dataset.to_dict() for dataset in user_datasets]

    return render_template(
        "community/propose_dataset.html",
        community=community,
        datasets=user_datasets,
        datasets_json=datasets_dict,
        form=form,
    )


@community_bp.route("/community/<string:slug>/request/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_request(slug, request_id):
    """Approve a dataset request (curators only)"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Validar que el request pertenece a la comunidad indicada en la URL
    community_request = community_service.get_request_by_id(request_id)
    if not community_request or community_request.community_id != community.id:
        flash("Request not found in this community", "error")
        return redirect(url_for("community.manage", slug=slug))

    comment = request.form.get("comment", None)

    success, error = community_service.approve_request(request_id, current_user.id, comment)

    if not success:
        flash(f"Error approving request: {error}", "error")
    else:
        flash("Request approved successfully! Dataset added to the community.", "success")

    return redirect(url_for("community.manage", slug=slug))


@community_bp.route("/community/<string:slug>/request/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_request(slug, request_id):
    """Reject a dataset request (curators only)"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Validar que el request pertenece a la comunidad indicada en la URL
    community_request = community_service.get_request_by_id(request_id)
    if not community_request or community_request.community_id != community.id:
        flash("Request not found in this community", "error")
        return redirect(url_for("community.manage", slug=slug))

    comment = request.form.get("comment", None)

    success, error = community_service.reject_request(request_id, current_user.id, comment)

    if not success:
        flash(f"Error rejecting request: {error}", "error")
    else:
        flash("Request rejected.", "success")

    return redirect(url_for("community.manage", slug=slug))


@community_bp.route("/uploads/communities/<path:filename>")
def uploaded_file(filename):
    """Serve uploaded community logos"""
    working_dir = os.getenv("WORKING_DIR", "")
    if not working_dir:
        # Si WORKING_DIR está vacío, usar la raíz del proyecto
        working_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    upload_dir = os.path.join(working_dir, "uploads", "communities")
    return send_from_directory(upload_dir, filename)
