from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.modules.community import community_bp
from app.modules.community.forms import CommunityForm, ProposeDatasetForm
from app.modules.community.mock_data import MOCK_COMMUNITIES, MOCK_PENDING_REQUESTS
from app.modules.dataset.models import DataSet


@community_bp.route("/community", methods=["GET"])
def index():
    """Redirect to list view"""
    return redirect(url_for("community.list"))


@community_bp.route("/community/list", methods=["GET"])
def list():
    """
    List all communities with search functionality.
    TODO: Replace MOCK_COMMUNITIES with community_service.get_all() when backend is ready.
    """
    query = request.args.get("query", "").lower()

    # MOCK: Filter communities by search query
    if query:
        communities = [c for c in MOCK_COMMUNITIES if query in c["name"].lower() or query in c["description"].lower()]
    else:
        communities = MOCK_COMMUNITIES

    return render_template("community/list.html", communities=communities, query=query)


@community_bp.route("/community/<int:community_id>", methods=["GET"])
def view(community_id):
    """
    View a single community with its datasets.
    TODO: Replace with community_service.get_by_id(community_id) when backend is ready.
    """
    # MOCK: Find community by id
    community = next((c for c in MOCK_COMMUNITIES if c["id"] == community_id), None)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list"))

    # REAL: Get actual datasets from database (simulate that they belong to this community)
    datasets = DataSet.query.limit(3).all()

    return render_template("community/view.html", community=community, datasets=datasets)


@community_bp.route("/community/create", methods=["GET", "POST"])
@login_required
def create():
    """
    Create a new community.
    TODO: Replace with community_service.create(form.data) when backend is ready.
    """
    form = CommunityForm()

    if form.validate_on_submit():
        # MOCK: Simulate community creation
        community_name = form.name.data
        # community_description = form.description.data  # TODO: Will be used when backend is ready
        logo_file = form.logo.data

        # Handle logo upload (mock - in real implementation, save to uploads folder)
        logo_filename = None
        if logo_file:
            logo_filename = secure_filename(logo_file.filename)
            # TODO: Save file when backend is ready
            # logo_path = os.path.join('uploads', 'communities', logo_filename)
            # logo_file.save(logo_path)
            flash(f'Logo "{logo_filename}" would be uploaded (Mock)', "info")

        # TODO: Call community_service.create() when backend is ready
        # community = community_service.create({
        #     'name': community_name,
        #     'description': community_description,
        #     'logo_path': logo_path if logo_filename else None,
        #     'creator_id': current_user.id
        # })

        flash(f'Community "{community_name}" created successfully! (Mock)', "success")
        return redirect(url_for("community.list"))

    return render_template("community/create.html", form=form)


@community_bp.route("/community/<int:community_id>/manage", methods=["GET"])
def manage(community_id):
    """
    Manage community (for curators only).
    TODO: Replace with real service calls and add curator authorization check.
    """
    # MOCK: Find community by id
    community = next((c for c in MOCK_COMMUNITIES if c["id"] == community_id), None)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list"))

    # MOCK: Get pending requests for this community
    # Update requests to include real datasets
    pending_requests = []
    for req in MOCK_PENDING_REQUESTS:
        if req["community_id"] == community_id:
            # Try to get the real dataset if it exists
            dataset = DataSet.query.get(req["dataset_id"])
            if dataset:
                req_copy = req.copy()
                req_copy["dataset"] = dataset
                pending_requests.append(req_copy)
            else:
                pending_requests.append(req)

    return render_template("community/manage.html", community=community, requests=pending_requests)


@community_bp.route("/community/<int:community_id>/propose", methods=["GET", "POST"])
@login_required
def propose_dataset(community_id):
    """
    Propose a dataset to be added to a community.
    TODO: Replace with community_service.propose_dataset() when backend is ready.
    """
    # MOCK: Find community by id
    community = next((c for c in MOCK_COMMUNITIES if c["id"] == community_id), None)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list"))

    # REAL: Get user's actual datasets from database
    user_datasets = DataSet.query.filter_by(user_id=current_user.id).all()

    if not user_datasets:
        flash("You need to have at least one dataset to propose to a community", "warning")
        return redirect(url_for("community.view", community_id=community_id))

    # Create form and populate dataset choices
    form = ProposeDatasetForm()
    form.dataset_id.choices = [(dataset.id, dataset.ds_meta_data.title) for dataset in user_datasets]

    if form.validate_on_submit():
        dataset_id = form.dataset_id.data
        # message = form.message.data  # TODO: Will be used when backend is ready

        # TODO: Call community_service.propose_dataset() when backend is ready
        # try:
        #     community_service.propose_dataset(
        #         community_id=community_id,
        #         dataset_id=dataset_id,
        #         requester_id=current_user.id,
        #         message=message
        #     )
        #     flash('Dataset proposal submitted successfully!', 'success')
        # except Exception as e:
        #     flash(f'Error submitting proposal: {str(e)}', 'error')
        #     return redirect(url_for('community.propose_dataset', community_id=community_id))

        # MOCK: Simulate proposal submission
        selected_dataset = next((d for d in user_datasets if d.id == dataset_id), None)
        flash(f'Proposal for dataset "{selected_dataset.ds_meta_data.title}" submitted successfully! (Mock)', "success")
        return redirect(url_for("community.view", community_id=community_id))

    # Convert datasets to dict for JSON serialization
    datasets_dict = [dataset.to_dict() for dataset in user_datasets]

    return render_template(
        "community/propose_dataset.html",
        community=community,
        datasets=user_datasets,
        datasets_json=datasets_dict,
        form=form,
    )
