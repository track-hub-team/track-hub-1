from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.modules.community import community_bp
from app.modules.community.forms import CommunityForm, ProposeDatasetForm
from app.modules.community.services import CommunityService
from app.modules.dataset.models import BaseDataset

community_service = CommunityService()


def get_community_or_redirect(community_id):
    """Helper to fetch a community or redirect with error"""
    community = community_service.get_by_id(community_id)
    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))
    return community


def require_curator(community_id):
    """Helper to ensure current user is a curator"""
    if not current_user.is_authenticated or not community_service.is_curator(community_id, current_user.id):
        flash("Only curators can perform this action", "error")
        return False
    return True


@community_bp.route("/community", methods=["GET"])
def index():
    return redirect(url_for("community.list_communities"))


@community_bp.route("/community/list", methods=["GET"])
def list_communities():
    query = request.args.get("query", "")
    communities = community_service.get_all(query if query else None)
    return render_template("community/list.html", communities=communities, query=query)


@community_bp.route("/community/<int:community_id>", methods=["GET"])
def view(community_id):
    """View a single community with its datasets"""
    community = community_service.get_by_id(community_id)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Get datasets from the community
    datasets = community_service.get_community_datasets(community_id)

    # Check if current user is curator
    is_curator = False
    if current_user.is_authenticated:
        is_curator = community_service.is_curator(community_id, current_user.id)

    return render_template("community/view.html", community=community, datasets=datasets, is_curator=is_curator)


@community_bp.route("/community/create", methods=["GET", "POST"])
@login_required
def create():
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
        else:
            flash(f'Community "{community.name}" created successfully!', "success")
            return redirect(url_for("community.view", community_id=community.id))
    return render_template("community/create.html", form=form)


@community_bp.route("/community/<int:community_id>/manage", methods=["GET"])
@login_required
def manage(community_id):
    community = get_community_or_redirect(community_id)
    if not isinstance(community, type(redirect(url_for("community.list_communities")))):
        return community

    if not require_curator(community_id):
        return redirect(url_for("community.view", community_id=community_id))

    pending_requests = community_service.get_pending_requests(community_id)
    return render_template("community/manage.html", community=community, requests=pending_requests)


@community_bp.route("/community/<int:community_id>/propose", methods=["GET", "POST"])
@login_required
def propose_dataset(community_id):
    community = get_community_or_redirect(community_id)
    if not isinstance(community, type(redirect(url_for("community.list_communities")))):
        return community

    user_datasets = BaseDataset.query.filter_by(user_id=current_user.id).all()
    if not user_datasets:
        flash("You need at least one dataset to propose to a community", "warning")
        return redirect(url_for("community.view", community_id=community_id))

    form = ProposeDatasetForm()
    form.dataset_id.choices = [(d.id, d.ds_meta_data.title) for d in user_datasets]

    if form.validate_on_submit():
        dataset_id = form.dataset_id.data
        message = form.message.data
        success, error = community_service.propose_dataset(
            community_id=community_id,
            dataset_id=dataset_id,
            requester_id=current_user.id,
            message=message,
        )
        if error:
            flash(f"Error submitting proposal: {error}", "error")
        else:
            selected_dataset = next(d for d in user_datasets if d.id == dataset_id)
            flash(f'Proposal for dataset "{selected_dataset.ds_meta_data.title}" submitted successfully!', "success")
            return redirect(url_for("community.view", community_id=community_id))

    datasets_dict = [d.to_dict() for d in user_datasets]
    return render_template(
        "community/propose_dataset.html",
        community=community,
        datasets=user_datasets,
        datasets_json=datasets_dict,
        form=form,
    )


def handle_request_action(community_id, request_id, action):
    if not require_curator(community_id):
        return redirect(url_for("community.view", community_id=community_id))

    comment = request.form.get("comment", None)
    func = community_service.approve_request if action == "approve" else community_service.reject_request
    success, error = func(request_id, current_user.id, comment)

    if error:
        flash(f"Error {action}ing request: {error}", "error")
    else:
        msg = (
            "Request approved successfully! Dataset added to the community."
            if action == "approve"
            else "Request rejected."
        )
        flash(msg, "success")

    return redirect(url_for("community.manage", community_id=community_id))


@community_bp.route("/community/<int:community_id>/request/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_request(community_id, request_id):
    return handle_request_action(community_id, request_id, "approve")


@community_bp.route("/community/<int:community_id>/request/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_request(community_id, request_id):
    return handle_request_action(community_id, request_id, "reject")
