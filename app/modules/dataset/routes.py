import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from flask import (
    abort,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.modules.dataset import dataset_bp
from app.modules.dataset.fetchers.base import FetchError
from app.modules.dataset.forms import DataSetForm
from app.modules.dataset.models import BaseDataset, DatasetVersion, DSDownloadRecord
from app.modules.dataset.registry import (
    get_allowed_extensions,
    get_descriptor,
    infer_kind_from_filename,
)
from app.modules.dataset.services import (
    AuthorService,
    DataSetService,
    DOIMappingService,
    DSDownloadRecordService,
    DSMetaDataService,
    DSViewRecordService,
    VersionService,
    calculate_checksum_and_size,
)
from app.modules.zenodo.services import ZenodoService

logger = logging.getLogger(__name__)

dataset_service = DataSetService()
author_service = AuthorService()
dsmetadata_service = DSMetaDataService()
zenodo_service = ZenodoService()
doi_mapping_service = DOIMappingService()
ds_view_record_service = DSViewRecordService()


# ========== CREATE DATASET (FORM + UVL/GPX) ==========


@dataset_bp.route("/dataset/upload", methods=["GET", "POST"])
@login_required
def create_dataset():
    form = DataSetForm()

    if request.method == "POST":
        if not form.validate_on_submit():
            return jsonify({"message": form.errors}), 400

        try:
            logger.info("Creating dataset...")
            dataset = dataset_service.create_from_form(form=form, current_user=current_user)
            logger.info(f"Created dataset: {dataset}")
            dataset_service.move_feature_models(dataset)
        except Exception as exc:
            logger.exception(f"Exception while create dataset data in local {exc}")
            return jsonify({"Exception while create dataset data in local: ": str(exc)}), 400

        # Enviar a Zenodo
        data = {}
        try:
            zenodo_response_json = zenodo_service.create_new_deposition(dataset)
            data = json.loads(json.dumps(zenodo_response_json))
        except Exception as exc:
            data = {}
            logger.exception(f"Exception while create dataset data in Zenodo {exc}")

        if data.get("conceptrecid"):
            deposition_id = data.get("id")
            dataset_service.update_dsmetadata(dataset.ds_meta_data_id, deposition_id=deposition_id)

            try:
                for feature_model in dataset.feature_models:
                    zenodo_service.upload_file(dataset, deposition_id, feature_model)

                zenodo_service.publish_deposition(deposition_id)

                deposition_doi = zenodo_service.get_doi(deposition_id)
                dataset_service.update_dsmetadata(dataset.ds_meta_data_id, dataset_doi=deposition_doi)
            except Exception as e:
                msg = f"it has not been possible upload feature models in Zenodo and update the DOI: {e}"
                return jsonify({"message": msg}), 200

        temp_folder = current_user.temp_folder()
        if os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder, ignore_errors=True)

        return jsonify({"message": "Everything works!"}), 200

    return render_template("dataset/upload_dataset.html", form=form)


# ========== LIST DATASETS ==========


@dataset_bp.route("/dataset/list", methods=["GET", "POST"])
@login_required
def list_dataset():
    return render_template(
        "dataset/list_datasets.html",
        datasets=dataset_service.get_synchronized(current_user.id),
        local_datasets=dataset_service.get_unsynchronized(current_user.id),
    )


# ========== FILE UPLOAD GENÉRICO (UVL/GPX/etc) ==========


@dataset_bp.route("/dataset/file/upload", methods=["POST"])
@login_required
def upload():
    """
    Sube un archivo individual a la carpeta temporal del usuario.
    Valida extensión y contenido según el registro de tipos.
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"message": "No file provided"}), 400

    allowed_exts = tuple(get_allowed_extensions())
    filename = file.filename or ""

    if not any(filename.lower().endswith(ext) for ext in allowed_exts):
        return jsonify({"message": f"Invalid file type. Allowed: {', '.join(allowed_exts)}"}), 400

    temp_folder = current_user.temp_folder()
    os.makedirs(temp_folder, exist_ok=True)

    new_filename = secure_filename(filename)
    file_path = os.path.join(temp_folder, new_filename)
    file.save(file_path)

    kind = infer_kind_from_filename(new_filename)
    descriptor = get_descriptor(kind)

    try:
        descriptor.handler.validate(file_path)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Validation failed for {new_filename}: {e}")
        return jsonify({"message": f"Validation failed: {str(e)}"}), 400

    return (
        jsonify(
            {
                "message": "File uploaded and validated successfully",
                "filename": new_filename,
                "file_type": kind,
            }
        ),
        200,
    )


# ========== IMPORT (GITHUB o ZIP) ==========


@dataset_bp.route("/dataset/import", methods=["POST"])
@login_required
def import_dataset():
    """
    Importa modelos (.uvl / .gpx) desde:
    - URL de GitHub (github_url)
    - ZIP subido (file)
    Los deja en la carpeta temporal del usuario.
    """
    json_data = request.get_json(silent=True) or {}
    form_data = request.form or {}

    github_url = json_data.get("github_url") or form_data.get("github_url")
    zip_file = request.files.get("file")

    if github_url and zip_file:
        return jsonify({"message": "Provide either 'github_url' or a ZIP file, not both"}), 400
    if not github_url and not zip_file:
        return jsonify({"message": "Provide 'github_url' or a ZIP file"}), 400

    temp_folder = Path(current_user.temp_folder())
    temp_folder.mkdir(parents=True, exist_ok=True)

    try:
        if github_url:
            added = dataset_service.fetch_models_from_github(
                github_url=github_url,
                dest_dir=temp_folder,
                current_user=current_user,
            )
        else:
            added = dataset_service.fetch_models_from_zip_upload(
                file_storage=zip_file,
                dest_dir=temp_folder,
                current_user=current_user,
            )

        if not added:
            return jsonify({"message": "No .uvl or .gpx files found"}), 400

        return (
            jsonify(
                {
                    "message": "Models imported into current session",
                    "files": [p.name for p in added],
                    "count": len(added),
                }
            ),
            200,
        )

    except FetchError as fe:
        logger.warning(f"FetchError importing models: {fe}")
        return jsonify({"message": str(fe)}), 400
    except Exception as exc:
        logger.exception(f"Error importing models: {exc}")
        return jsonify({"message": "Internal server error"}), 500


# ========== DELETE FILE TEMPORAL ==========


@dataset_bp.route("/dataset/file/delete", methods=["POST"])
@login_required
def delete():
    data = request.get_json() or {}
    filename = data.get("file")
    if not filename:
        return jsonify({"error": "Missing 'file'"}), 400

    temp_folder = current_user.temp_folder()
    filepath = os.path.join(temp_folder, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"message": "File deleted successfully"}), 200

    return jsonify({"error": "Error: File not found"}), 404


# ========== DOWNLOAD DATASET COMO ZIP ==========


@dataset_bp.route("/dataset/download/<int:dataset_id>", methods=["GET"])
def download_dataset(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)
    base_path = f"uploads/user_{dataset.user_id}/dataset_{dataset.id}/"

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"dataset_{dataset_id}.zip")

    with ZipFile(zip_path, "w") as zipf:
        for subdir, _, files in os.walk(base_path):
            for file in files:
                full_path = os.path.join(subdir, file)
                relative_path = os.path.relpath(full_path, base_path)
                zipf.write(
                    full_path,
                    arcname=os.path.join(os.path.basename(zip_path[:-4]), relative_path),
                )

    user_cookie = request.cookies.get("download_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())
        resp = make_response(
            send_from_directory(
                temp_dir,
                f"dataset_{dataset_id}.zip",
                as_attachment=True,
                mimetype="application/zip",
            )
        )
        resp.set_cookie("download_cookie", user_cookie)
    else:
        resp = send_from_directory(
            temp_dir,
            f"dataset_{dataset_id}.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    existing_record = DSDownloadRecord.query.filter_by(
        user_id=current_user.id if current_user.is_authenticated else None,
        dataset_id=dataset_id,
        download_cookie=user_cookie,
    ).first()

    if not existing_record:
        DSDownloadRecordService().create(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset_id,
            download_date=datetime.now(timezone.utc),
            download_cookie=user_cookie,
        )

    return resp


# ========== DOI RESOLVER ==========


@dataset_bp.route("/doi/<path:doi>/", methods=["GET"])
def subdomain_index(doi):
    new_doi = doi_mapping_service.get_new_doi(doi)
    if new_doi:
        return redirect(url_for("dataset.subdomain_index", doi=new_doi), code=302)

    ds_meta_data = dsmetadata_service.filter_by_doi(doi)
    if not ds_meta_data:
        abort(404)

    dataset = ds_meta_data.data_set

    user_cookie = ds_view_record_service.create_cookie(dataset=dataset)
    resp = make_response(render_template("dataset/view_dataset.html", dataset=dataset))
    resp.set_cookie("view_cookie", user_cookie)

    return resp


# ========== UNSYNCHRONIZED VIEW ==========


@dataset_bp.route("/dataset/unsynchronized/<int:dataset_id>/", methods=["GET"])
@login_required
def get_unsynchronized_dataset(dataset_id):
    dataset = dataset_service.get_unsynchronized_dataset(current_user.id, dataset_id)
    if not dataset:
        abort(404)

    return render_template(
        "dataset/view_dataset.html",
        dataset=dataset,
        FLASK_ENV=os.getenv("FLASK_ENV", "development"),
    )


# ========== GPX API ==========


@dataset_bp.route("/api/gpx/<int:file_id>")
def get_gpx_data(file_id):
    """Retorna datos parseados de un archivo GPX."""
    from flask import current_app, jsonify

    from app.modules.dataset.handlers.gpx_handler import GPXHandler

    try:
        # Query directa
        result = db.session.execute(
            db.text(
                """
                SELECT
                    ds.user_id,
                    ds.id as dataset_id,
                    dsm.dataset_doi,
                    f.id as file_id,
                    f.name as file_name
                FROM feature_model fm
                JOIN data_set ds ON fm.data_set_id = ds.id
                LEFT JOIN ds_meta_data dsm ON ds.ds_meta_data_id = dsm.id
                LEFT JOIN file f ON f.feature_model_id = fm.id
                WHERE fm.fm_meta_data_id = :file_id
                LIMIT 1
                """
            ),
            {"file_id": file_id},
        ).first()

        if not result:
            return jsonify({"error": "File not found"}), 404

        user_id, dataset_id, dataset_doi, gpx_file_id, gpx_file_name = result

        if not gpx_file_name or not gpx_file_name.lower().endswith(".gpx"):
            return jsonify({"error": "File is not a GPX file"}), 400

        if not dataset_doi:
            if not current_user.is_authenticated or user_id != current_user.id:
                return jsonify({"error": "Unauthorized"}), 403

        project_root = os.path.dirname(current_app.root_path)
        file_path = os.path.join(
            project_root,
            "uploads",
            f"user_{user_id}",
            f"dataset_{dataset_id}",
            gpx_file_name,
        )

        if not os.path.exists(file_path):
            logger.error(f"File not found at: {file_path}")
            return jsonify({"error": "File not found on disk"}), 404

        handler = GPXHandler()
        gpx_data = handler.parse_gpx(file_path)

        if gpx_data is None:
            return jsonify({"error": "Invalid GPX file"}), 500

        return jsonify(gpx_data)

    except Exception as e:
        logger.error(f"Error parsing GPX {file_id}: {str(e)}")
        return jsonify({"error": f"Error processing GPX file: {str(e)}"}), 500


# ========== VERSIONES ==========


@dataset_bp.route("/dataset/<int:dataset_id>/versions")
def list_versions(dataset_id):
    dataset = BaseDataset.query.get_or_404(dataset_id)
    versions = dataset.versions.order_by(DatasetVersion.created_at.desc()).all()
    return render_template("dataset/list_versions.html", dataset=dataset, versions=versions)


@dataset_bp.route("/versions/<int:version1_id>/compare/<int:version2_id>")
def compare_versions(version1_id, version2_id):
    version1 = DatasetVersion.query.get_or_404(version1_id)
    version2 = DatasetVersion.query.get_or_404(version2_id)

    if version1.dataset_id != version2.dataset_id:
        flash("Versions must belong to the same dataset", "danger")
        abort(400)

    dataset = version1.dataset
    all_versions = (
        DatasetVersion.query.filter_by(dataset_id=dataset.id).order_by(DatasetVersion.created_at.desc()).all()
    )

    if version1.created_at < version2.created_at:
        version1, version2 = version2, version1

    comparison = VersionService.compare_versions(version1.id, version2.id)

    return render_template(
        "dataset/compare_versions.html",
        dataset=dataset,
        version1=version1,
        version2=version2,
        comparison=comparison,
        all_versions=all_versions,
    )


@dataset_bp.route("/dataset/<int:dataset_id>/create_version", methods=["POST"])
@login_required
def create_version(dataset_id):
    dataset = BaseDataset.query.get_or_404(dataset_id)

    if dataset.user_id != current_user.id:
        abort(403)

    if dataset.ds_meta_data.dataset_doi:
        flash("Cannot create versions for synchronized datasets. Unsynchronize first.", "warning")
        return redirect(url_for("dataset.list_versions", dataset_id=dataset_id))

    changelog = request.form.get("changelog", "").strip()
    bump_type = request.form.get("bump_type", "patch")

    if not changelog:
        flash("Changelog is required", "warning")
        return redirect(url_for("dataset.get_unsynchronized_dataset", dataset_id=dataset_id))

    if bump_type not in ["major", "minor", "patch"]:
        bump_type = "patch"

    try:
        version = VersionService.create_version(dataset, changelog, current_user, bump_type)
        flash(f"Version {version.version_number} created successfully! 🎉", "success")
    except Exception as e:
        flash(f"Error creating version: {str(e)}", "danger")
        logger.error(f"Error creating version for dataset {dataset_id}: {str(e)}")

    return redirect(url_for("dataset.list_versions", dataset_id=dataset_id))


@dataset_bp.route("/api/dataset/<int:dataset_id>/versions")
def api_list_versions(dataset_id):
    dataset = BaseDataset.query.get_or_404(dataset_id)
    versions = [v.to_dict() for v in dataset.versions.all()]
    return jsonify({"dataset_id": dataset_id, "version_count": len(versions), "versions": versions})


# ========== EDIT DATASET ==========


@dataset_bp.route("/dataset/<int:dataset_id>/edit", methods=["GET", "POST"])
@login_required
def edit_dataset(dataset_id):
    dataset = BaseDataset.query.get_or_404(dataset_id)

    if dataset.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        changes = []

        new_title = request.form.get("title", "").strip()
        if new_title and new_title != dataset.ds_meta_data.title:
            old_title = dataset.ds_meta_data.title
            dataset.ds_meta_data.title = new_title
            changes.append(f"Changed title from '{old_title}' to '{new_title}'")

        new_description = request.form.get("description", "").strip()
        if new_description and new_description != dataset.ds_meta_data.description:
            dataset.ds_meta_data.description = new_description
            changes.append("Updated description")

        new_tags = request.form.get("tags", "").strip()
        if new_tags != (dataset.ds_meta_data.tags or ""):
            dataset.ds_meta_data.tags = new_tags
            changes.append("Updated tags")

        uploaded_files = request.files.getlist("files")
        if uploaded_files and uploaded_files[0].filename:
            for file in uploaded_files:
                if not file.filename:
                    continue

                filename = secure_filename(file.filename)
                file_kind = infer_kind_from_filename(filename)

                if file_kind != dataset.dataset_kind:
                    flash(
                        f"File type mismatch: {filename} is {file_kind.upper()} "
                        f"but dataset is {dataset.dataset_kind.upper()}",
                        "danger",
                    )
                    continue

                working_dir = os.getenv("WORKING_DIR", "")
                dest_dir = os.path.join(
                    working_dir,
                    "uploads",
                    f"user_{current_user.id}",
                    f"dataset_{dataset.id}",
                )
                os.makedirs(dest_dir, exist_ok=True)

                file_path = os.path.join(dest_dir, filename)
                file.save(file_path)

                descriptor = get_descriptor(file_kind)
                try:
                    descriptor.handler.validate(file_path)
                except Exception as e:
                    os.remove(file_path)
                    flash(f"File validation failed for {filename}: {str(e)}", "danger")
                    continue

                from app.modules.featuremodel.repositories import (
                    FeatureModelRepository,
                    FMMetaDataRepository,
                )
                from app.modules.hubfile.repositories import HubfileRepository

                fmmetadata = FMMetaDataRepository().create(
                    commit=False,
                    filename=filename,
                    title=filename,
                    description="Added via edit",
                    publication_type="none",
                )

                fm = FeatureModelRepository().create(
                    commit=False,
                    data_set_id=dataset.id,
                    fm_meta_data_id=fmmetadata.id,
                )

                checksum, size = calculate_checksum_and_size(file_path)

                HubfileRepository().create(
                    commit=False,
                    name=filename,
                    checksum=checksum,
                    size=size,
                    feature_model_id=fm.id,
                )

                changes.append(f"Added file: {filename}")

        if changes:
            try:
                db.session.commit()

                if not dataset.ds_meta_data.dataset_doi:
                    try:
                        changelog = "Automatic version after edit:\n" + "\n".join(f"- {c}" for c in changes)
                        version = VersionService.create_version(
                            dataset=dataset,
                            changelog=changelog,
                            user=current_user,
                            bump_type="patch",
                        )
                        flash(
                            f"Dataset updated successfully! New version: v{version.version_number} 🎉",
                            "success",
                        )
                    except Exception as e:
                        logger.error(f"Could not create automatic version: {str(e)}")
                        flash(
                            "Dataset updated but version creation failed",
                            "warning",
                        )
                else:
                    flash("Dataset updated successfully! ✅", "success")

                if dataset.ds_meta_data.dataset_doi:
                    return redirect(
                        url_for(
                            "dataset.subdomain_index",
                            doi=dataset.ds_meta_data.dataset_doi,
                        )
                    )
                else:
                    return redirect(
                        url_for(
                            "dataset.get_unsynchronized_dataset",
                            dataset_id=dataset.id,
                        )
                    )

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating dataset {dataset_id}: {str(e)}")
                flash(f"Error updating dataset: {str(e)}", "danger")
        else:
            flash("No changes detected", "info")

    return render_template("dataset/edit_dataset.html", dataset=dataset)
