import os

from flask import flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app.modules.community import community_bp
from app.modules.community.forms import CommunityForm, ProposeDatasetForm
from app.modules.community.services import CommunityService
from app.modules.dataset.models import BaseDataset

# Necesitas importar el servicio de Perfil de Usuario para las acciones de seguimiento de usuario a usuario
from app.modules.profile.services import UserProfileService

community_service = CommunityService()
user_profile_service = UserProfileService()  # Servicio para seguimiento de User a User


# ======================================================================
# RUTAS DE COMUNIDAD (Creación, Listado, Vista, Gestión)
# ======================================================================


@community_bp.route("/community", methods=["GET"])
def index():
    """Redirect to list view"""
    return redirect(url_for("community.list_communities"))


@community_bp.route("/community/list", methods=["GET"])
def list_communities():
    """List all communities with search functionality"""
    query = request.args.get("query", "")

    # Get communities from database
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

    # Check if current user is curator and if they are following the community (ACTUALIZADO)
    is_curator = False
    is_following = False
    if current_user.is_authenticated:
        is_curator = community_service.is_curator(community_id, current_user.id)
        # Usamos el método is_followed_by que añadimos al modelo Community
        is_following = community.is_followed_by(current_user.id)

    return render_template(
        "community/view.html",
        community=community,
        datasets=datasets,
        is_curator=is_curator,
        is_following=is_following,  # Pasamos la variable a la plantilla
    )


@community_bp.route("/community/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new community"""
    form = CommunityForm()

    if form.validate_on_submit():
        # Create community using the service
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
        return redirect(url_for("community.view", community_id=community.id))

    return render_template("community/create.html", form=form)


@community_bp.route("/community/<int:community_id>/manage", methods=["GET"])
@login_required
def manage(community_id):
    """Manage community (for curators only)"""
    community = community_service.get_by_id(community_id)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Check if user is curator
    if not community_service.is_curator(community_id, current_user.id):
        flash("Only curators can manage this community", "error")
        return redirect(url_for("community.view", community_id=community_id))

    # Get pending requests
    pending_requests = community_service.get_pending_requests(community_id)

    return render_template("community/manage.html", community=community, requests=pending_requests)


# ======================================================================
# RUTAS DE SOLICITUDES (Propuesta, Aprobación, Rechazo)
# ======================================================================


@community_bp.route("/community/<int:community_id>/propose", methods=["GET", "POST"])
@login_required
def propose_dataset(community_id):
    """Propose a dataset to be added to a community"""
    community = community_service.get_by_id(community_id)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Get user's datasets
    user_datasets = BaseDataset.query.filter_by(user_id=current_user.id).all()

    if not user_datasets:
        flash("You need to have at least one dataset to propose to a community", "warning")
        return redirect(url_for("community.view", community_id=community_id))

    # Create form and populate dataset choices
    form = ProposeDatasetForm()
    form.dataset_id.choices = [(dataset.id, dataset.ds_meta_data.title) for dataset in user_datasets]

    if form.validate_on_submit():
        dataset_id = form.dataset_id.data
        message = form.message.data

        # Propose dataset using the service
        success, error = community_service.propose_dataset(
            community_id=community_id, dataset_id=dataset_id, requester_id=current_user.id, message=message
        )

        if error:
            flash(f"Error submitting proposal: {error}", "error")
            return redirect(url_for("community.propose_dataset", community_id=community_id))

        selected_dataset = next((d for d in user_datasets if d.id == dataset_id), None)
        flash(f'Proposal for dataset "{selected_dataset.ds_meta_data.title}" submitted successfully!', "success")
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


@community_bp.route("/community/<int:community_id>/request/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_request(community_id, request_id):
    """Approve a dataset request (curators only)"""
    comment = request.form.get("comment", None)

    _, error = community_service.approve_request(request_id, current_user.id, comment)

    if error:
        flash(f"Error approving request: {error}", "error")
    else:
        flash("Request approved successfully! Dataset added to the community.", "success")

    return redirect(url_for("community.manage", community_id=community_id))


@community_bp.route("/community/<int:community_id>/request/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_request(community_id, request_id):
    """Reject a dataset request (curators only)"""
    comment = request.form.get("comment", None)

    _, error = community_service.reject_request(request_id, current_user.id, comment)

    if error:
        flash(f"Error rejecting request: {error}", "error")
    else:
        flash("Request rejected.", "success")

    return redirect(url_for("community.manage", community_id=community_id))


# ======================================================================
# RUTAS DE SEGUIMIENTO (NUEVO)
# ======================================================================


@community_bp.route("/community/<int:community_id>/follow", methods=["POST"])
@login_required
def follow_community(community_id):
    """Permite al usuario actual seguir una comunidad."""
    community = community_service.get_by_id(community_id)
    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    success, error = community_service.follow_community(current_user.id, community_id)

    if error:
        flash(f"Error following community: {error}", "error")
    else:
        flash(f"You are now following {community.name}.", "success")

    return redirect(url_for("community.view", community_id=community_id))


@community_bp.route("/community/<int:community_id>/unfollow", methods=["POST"])
@login_required
def unfollow_community(community_id):
    """Permite al usuario actual dejar de seguir una comunidad."""
    community = community_service.get_by_id(community_id)
    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    success, error = community_service.unfollow_community(current_user.id, community_id)

    if error:
        flash(f"Error unfollowing community: {error}", "error")
    else:
        flash(f"You have unfollowed {community.name}.", "success")

    return redirect(url_for("community.view", community_id=community_id))


# Nota: Las rutas para seguir/dejar de seguir *usuarios* generalmente se colocan
# en el blueprint del módulo 'profile' o 'user', pero las incluyo aquí temporalmente
# ya que se relacionan con las funciones de seguimiento.


@community_bp.route("/user/<int:followed_id>/follow", methods=["POST"])
@login_required
def follow_user(followed_id):
    """Permite al usuario actual seguir a otro usuario."""
    if current_user.id == followed_id:
        flash("You cannot follow yourself.", "error")
        return redirect(request.referrer or url_for("public.index"))

    followed_user, error = user_profile_service.follow_user(current_user.id, followed_id)

    if error:
        flash(f"Error following user: {error}", "error")
    elif followed_user:
        flash(f"You are now following {followed_user.email}.", "success")

    # Redirige a la página anterior o a la página principal
    return redirect(request.referrer or url_for("public.index"))


@community_bp.route("/user/<int:followed_id>/unfollow", methods=["POST"])
@login_required
def unfollow_user(followed_id):
    """Permite al usuario actual dejar de seguir a otro usuario."""
    followed_user, error = user_profile_service.unfollow_user(current_user.id, followed_id)

    if error:
        flash(f"Error unfollowing user: {error}", "error")
    elif followed_user:
        flash(f"You have unfollowed {followed_user.email}.", "success")

    # Redirige a la página anterior o a la página principal
    return redirect(request.referrer or url_for("public.index"))


# ======================================================================
# RUTAS AUXILIARES
# ======================================================================


@community_bp.route("/uploads/communities/<path:filename>")
def uploaded_file(filename):
    """Serve uploaded community logos"""
    working_dir = os.getenv("WORKING_DIR", "")
    upload_dir = os.path.join(working_dir, "uploads", "communities")
    return send_from_directory(upload_dir, filename)
