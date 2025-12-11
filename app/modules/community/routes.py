import os

from flask import flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app.modules.community import community_bp
from app.modules.community.forms import CommunityForm, ProposeDatasetForm
from app.modules.community.services import CommunityService

# Necesitas importar el servicio de Perfil de Usuario para las acciones de seguimiento de usuario a usuario
from app.modules.profile.services import UserProfileService

community_service = CommunityService()
user_profile_service = UserProfileService()  # Servicio para seguimiento de User a User


# ======================================================================
# RUTAS DE COMUNIDAD (Creación, Listado, Vista, Gestión)
# ======================================================================


@community_bp.route("/community", methods=["GET"])
def index():
    """Redireccionar a la lista de comunidades"""
    return redirect(url_for("community.list_communities"))


@community_bp.route("/community/list", methods=["GET"])
def list_communities():
    """Listar todas las comunidades"""
    query = request.args.get("query", "")

    communities = community_service.get_all(query if query else None)

    return render_template("community/list.html", communities=communities, query=query)


@community_bp.route("/community/<string:slug>", methods=["GET"])
def view(slug):
    """Ver una comunidad específica"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    datasets = community_service.get_community_datasets(community.id)

    is_curator = False
    if current_user.is_authenticated:
        is_curator = community_service.is_curator(community.id, current_user.id)

    is_following = False
    if current_user.is_authenticated:
        is_following = community_service.is_following_community(current_user.id, community.id)

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
    """Crear una nueva comunidad"""
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
    """Gestionar comunidad (solo para curadores)"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    if not community_service.is_curator(community.id, current_user.id):
        flash("Only curators can manage this community", "error")
        return redirect(url_for("community.view", slug=slug))

    pending_requests = community_service.get_pending_requests(community.id)

    return render_template("community/manage.html", community=community, requests=pending_requests)


@community_bp.route("/community/<string:slug>/propose", methods=["GET", "POST"])
@login_required
def propose_dataset(slug):
    """Proponer un dataset para ser añadido a una comunidad"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    # Obtener datasets elegibles del usuario
    user_datasets = community_service.get_eligible_datasets_for_community(current_user.id, community.id)

    if not user_datasets:
        flash(
            "You don't have any eligible datasets. They may already be in this community or have a pending request.",
            "warning",
        )
        return redirect(url_for("community.view", slug=slug))

    # Crear el formulario
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
    """Aprobar una solicitud de dataset (solo para curadores)"""
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
    """Rechazar una solicitud de dataset (solo para curadores)"""
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


# ======================================================================
# RUTAS DE SEGUIMIENTO (NUEVO)
# ======================================================================


@community_bp.route("/community/<string:slug>/follow", methods=["POST"])
@login_required
def follow_community(slug):
    community = community_service.get_by_slug(slug)
    if not community:
        return jsonify({"success": False, "error": "Community not found"}), 404

    success, error = community_service.follow_community(current_user.id, community.id)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": success, "error": error, "following": True}), (200 if success else 400)

    return redirect(url_for("community.view", slug=slug))


@community_bp.route("/community/<string:slug>/unfollow", methods=["POST"])
@login_required
def unfollow_community(slug):
    community = community_service.get_by_slug(slug)
    if not community:
        return jsonify({"success": False, "error": "Community not found"}), 404

    success, error = community_service.unfollow_community(current_user.id, community.id)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": success, "error": error, "following": False}), (200 if success else 400)

    return redirect(url_for("community.view", slug=slug))


# Nota: Las rutas para seguir/dejar de seguir *usuarios* generalmente se colocan
# en el blueprint del módulo 'profile' o 'user', pero las incluyo aquí temporalmente
# ya que se relacionan con las funciones de seguimiento.


@community_bp.route("/community/user/<int:followed_id>/follow", methods=["POST"])
@login_required
def follow_user(followed_id):
    if current_user.id == followed_id:
        return jsonify({"success": False, "error": "You cannot follow yourself"}), 400

    record, error = community_service.follow_user(current_user.id, followed_id)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": error is None, "error": error, "following": True})

    if error:
        flash(error, "error")
    return redirect(request.referrer or url_for("public.index"))


@community_bp.route("/community/user/<int:followed_id>/unfollow", methods=["POST"])
@login_required
def unfollow_user(followed_id):
    ok, error = community_service.unfollow_user(current_user.id, followed_id)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": error is None, "error": error, "following": False})

    if error:
        flash(error, "error")
    return redirect(request.referrer or url_for("public.index"))


# ======================================================================
# RUTAS AUXILIARES
# ======================================================================


@community_bp.route("/uploads/communities/<path:filename>")
def uploaded_file(filename):
    """Servir logos de comunidades subidos"""
    working_dir = os.getenv("WORKING_DIR", "")
    if not working_dir:
        working_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    upload_dir = os.path.join(working_dir, "uploads", "communities")
    return send_from_directory(upload_dir, filename)


@community_bp.route("/community/api/search-users", methods=["GET"])
@login_required
def search_users():
    """Buscar usuarios por email o nombre para añadir como curadores"""
    query = request.args.get("q", "").strip()
    community_id = request.args.get("community_id", type=int)

    # Si se proporciona community_id, excluir curadores existentes en la comunidad
    exclude_ids = None
    if community_id:
        exclude_ids = community_service.get_curator_user_ids(community_id)

    users = community_service.search_users(query, exclude_user_ids=exclude_ids)
    return jsonify({"users": users})


@community_bp.route("/community/<string:slug>/add-curator", methods=["POST"])
@login_required
def add_curator_route(slug):
    """Añadir un curador a una comunidad"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    if not community_service.is_curator(community.id, current_user.id):
        flash("Only curators can add other curators", "error")
        return redirect(url_for("community.manage", slug=slug))

    user_id = request.form.get("user_id", type=int)
    if not user_id:
        flash("User ID is required", "error")
        return redirect(url_for("community.manage", slug=slug))

    success, error = community_service.add_curator(community.id, user_id)

    if success:
        curator_info = community_service.get_curator_info(user_id)
        curator_name = f"{curator_info['name']} {curator_info['surname']}".strip() or curator_info["email"]
        flash(f'Curator "{curator_name}" added successfully!', "success")
    else:
        flash(f"Error adding curator: {error}", "error")

    return redirect(url_for("community.manage", slug=slug))


@community_bp.route("/community/<string:slug>/remove-curator", methods=["POST"])
@login_required
def remove_curator_route(slug):
    """Eliminar un curador de una comunidad"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    user_id = request.form.get("user_id", type=int)
    if not user_id:
        flash("User ID is required", "error")
        return redirect(url_for("community.manage", slug=slug))

    curator_info = community_service.get_curator_info(user_id)

    success, error = community_service.remove_curator(community.id, user_id, current_user.id)

    if success:
        curator_name = f"{curator_info['name']} {curator_info['surname']}".strip() or curator_info["email"]
        flash(f'Curator "{curator_name}" removed successfully!', "success")
    else:
        flash(f"Error removing curator: {error}", "error")

    return redirect(url_for("community.manage", slug=slug))


@community_bp.route("/community/<string:slug>/update", methods=["POST"])
@login_required
def update_community(slug):
    """Actualizar la configuración de la comunidad (solo para curadores)"""
    community = community_service.get_by_slug(slug)

    if not community:
        flash("Community not found", "error")
        return redirect(url_for("community.list_communities"))

    if not community_service.is_curator(community.id, current_user.id):
        flash("Only curators can update community settings", "error")
        return redirect(url_for("community.view", slug=slug))

    description = request.form.get("description")
    logo_file = request.files.get("logo")

    success, error = community_service.update_community(community.id, description=description, logo_file=logo_file)

    if success:
        flash("Community settings updated successfully!", "success")
    else:
        flash(f"Error updating community: {error}", "error")

    return redirect(url_for("community.manage", slug=slug))
