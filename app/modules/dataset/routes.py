import json
import logging
import os
import re
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
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.modules.community.services import CommunityService
from app.modules.dataset import dataset_bp
from app.modules.dataset.fetchers.base import FetchError
from app.modules.dataset.forms import DataSetForm
from app.modules.dataset.models import BaseDataset, DatasetVersion, DSDownloadRecord, PublicationType
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
community_service = CommunityService()


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
            logger.info(f"[UPLOAD] Creating deposition for dataset {dataset.id}")
            zenodo_response_json = zenodo_service.create_new_deposition(dataset)
            data = json.loads(json.dumps(zenodo_response_json))
            logger.info(f"[UPLOAD] Deposition created successfully: {data.get('id')}")
        except Exception as exc:
            data = {}
            logger.exception(f"[UPLOAD] Exception while creating deposition in Zenodo: {exc}")
            return jsonify({"message": f"Failed to create deposition: {str(exc)}"}), 500

        if data.get("conceptrecid"):
            deposition_id = data.get("id")
            conceptrecid = data.get("conceptrecid")
            logger.info(
                f"[UPLOAD] Updating dataset {dataset.ds_meta_data_id} with "
                f"deposition_id={deposition_id}, conceptrecid={conceptrecid}"
            )
            dataset_service.update_dsmetadata(
                dataset.ds_meta_data_id, deposition_id=deposition_id, conceptrecid=conceptrecid
            )

            try:
                logger.info(f"[UPLOAD] Starting file upload for {len(dataset.feature_models)} feature models")
                for idx, feature_model in enumerate(dataset.feature_models, 1):
                    logger.info(f"[UPLOAD] Uploading file {idx}/{len(dataset.feature_models)}")
                    zenodo_service.upload_file(dataset, deposition_id, feature_model)
                logger.info("[UPLOAD] All files uploaded successfully")

                # NOTE: La publicación ahora es manual para permitir crear versiones antes de publicar
                # El usuario puede publicar desde el botón "Publish to Zenodo" en la vista del dataset
                logger.info(
                    f"[UPLOAD] Dataset {dataset.id} uploaded to Zenodo (deposition {deposition_id}), ready to publish"
                )
            except Exception as e:
                logger.exception(f"[UPLOAD] Failed during file upload: {e}")
                msg = f"Failed to upload files to Zenodo: {str(e)}"
                return jsonify({"message": msg}), 500

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


@dataset_bp.route("/dataset/<int:dataset_id>/publish", methods=["POST"])
@login_required
def publish_dataset(dataset_id):
    """
    Publica o republi un dataset en Zenodo/Fakenodo.
    Soporta tres flujos:
    1. Primera publicación: Crea deposición, sube archivos, publica → v1
    2. Republicación sin cambios: Vuelve a publicar la misma deposición → mismo DOI
    3. Republicación con cambios: Fakenodo detecta cambios y crea nueva versión → nuevo DOI (.v2)

    Solo puede publicarlo el propietario del dataset.
    """
    dataset = BaseDataset.query.get_or_404(dataset_id)

    if dataset.user_id != current_user.id:
        return jsonify({"message": "Unauthorized"}), 403

    if not dataset.ds_meta_data.deposition_id:
        return jsonify({"message": "Dataset not uploaded to Zenodo"}), 400

    try:
        deposition_id = dataset.ds_meta_data.deposition_id
        is_first_publication = not dataset.ds_meta_data.dataset_doi

        current_fingerprint = dataset_service.calculate_files_fingerprint(dataset)
        logger.info(f"[PUBLISH] Current files fingerprint: {current_fingerprint}")

        if is_first_publication:
            logger.info(f"[PUBLISH] First publication for dataset {dataset_id}, deposition {deposition_id}")
        else:
            old_fingerprint = dataset.ds_meta_data.files_fingerprint
            if old_fingerprint == current_fingerprint:
                logger.info("[PUBLISH] Re-publication without changes - files unchanged")
            else:
                logger.info("[PUBLISH] Re-publication with changes - files modified")
                logger.info(f"[PUBLISH] Old fingerprint: {old_fingerprint}")
                logger.info(f"[PUBLISH] New fingerprint: {current_fingerprint}")

                # Upload new files to Fakenodo before publishing
                logger.info(f"[PUBLISH] Syncing local files with Fakenodo deposition {deposition_id}")
                try:
                    # Get current files in Fakenodo
                    deposition_data = zenodo_service.get_deposition(deposition_id)
                    fakenodo_files = {f["filename"] for f in deposition_data.get("files", [])}
                    logger.info(f"[PUBLISH] Files in Fakenodo: {fakenodo_files}")

                    # Upload any local files not in Fakenodo
                    uploaded_count = 0
                    for feature_model in dataset.feature_models:
                        for hubfile in feature_model.files:
                            if hubfile.name not in fakenodo_files:
                                logger.info(f"[PUBLISH] Uploading new file {hubfile.name} to Fakenodo")
                                zenodo_service.upload_file(dataset, deposition_id, feature_model, current_user)
                                uploaded_count += 1

                    if uploaded_count > 0:
                        logger.info(f"[PUBLISH] Uploaded {uploaded_count} new file(s) to Fakenodo")
                    else:
                        logger.info("[PUBLISH] All files already in Fakenodo")

                except Exception as e:
                    logger.error(f"[PUBLISH] Error syncing files with Fakenodo: {str(e)}")
                    return jsonify({"message": f"Failed to sync files with Zenodo: {str(e)}"}), 500

        # Publicar deposición - Fakenodo puede devolver una nueva deposición con nuevo ID si hay cambios
        publish_response = zenodo_service.publish_deposition(deposition_id)
        new_deposition_id = publish_response.get("id", deposition_id)

        # Si Fakenodo creó una nueva versión, actualizar el deposition_id
        if new_deposition_id != deposition_id:
            logger.info(
                f"[PUBLISH] New version created - Old deposition: {deposition_id}, New deposition: {new_deposition_id}"
            )
            deposition_id = new_deposition_id
        else:
            logger.info(f"[PUBLISH] No new version - Using same deposition: {deposition_id}")

        # Get DOI from publish response (it's already there!)
        deposition_doi = publish_response.get("doi")
        if not deposition_doi:
            # Fallback: get it from API if not in response
            logger.warning("[PUBLISH] DOI not in publish response, fetching from API")
            deposition_doi = zenodo_service.get_doi(deposition_id)

        conceptrecid = publish_response.get("conceptrecid")
        if not conceptrecid:
            # Fallback: get it from API if not in response
            conceptrecid = zenodo_service.get_conceptrecid(deposition_id)

        logger.info(f"[PUBLISH] DOI retrieved: {deposition_doi}, conceptrecid: {conceptrecid}")

        # Log publish response for debugging
        logger.info(f"[PUBLISH] Full publish response: {publish_response}")

        # Guardar DOI, conceptrecid, fingerprint y nuevo deposition_id si cambió
        update_data = {"dataset_doi": deposition_doi, "files_fingerprint": current_fingerprint}

        # Actualizar deposition_id si Fakenodo creó una nueva versión
        if new_deposition_id != dataset.ds_meta_data.deposition_id:
            update_data["deposition_id"] = new_deposition_id
            logger.info(
                f"[PUBLISH] Updating deposition_id from {dataset.ds_meta_data.deposition_id} to {new_deposition_id}"
            )

        if not dataset.ds_meta_data.conceptrecid and conceptrecid:
            update_data["conceptrecid"] = conceptrecid
            logger.info(f"[PUBLISH] Saving conceptrecid={conceptrecid} for dataset {dataset.ds_meta_data_id}")

        logger.info(f"[PUBLISH] Updating dataset {dataset.ds_meta_data_id} with {update_data}")
        dataset_service.update_dsmetadata(dataset.ds_meta_data_id, **update_data)

        # Auto-create DatasetVersion to track Zenodo versions
        try:
            logger.info(
                f"[PUBLISH] Checking if version with DOI {deposition_doi} already exists for dataset {dataset.id}"
            )
            version_exists = DatasetVersion.query.filter_by(dataset_id=dataset.id, version_doi=deposition_doi).first()

            if version_exists:
                logger.info(
                    f"[PUBLISH] Version with DOI {deposition_doi} already exists "
                    f"(version_id={version_exists.id}, version_number={version_exists.version_number})"
                )

            if not version_exists:
                # Determine version number based on DOI
                # Extract version number from DOI (e.g., "10.9999/dataset.v2" -> "2.0.0")
                doi_version = deposition_doi.split(".v")[-1] if ".v" in deposition_doi else "1"
                version_number = f"{doi_version}.0.0"

                logger.info(f"[PUBLISH] Creating new version {version_number} for DOI {deposition_doi}")

                # Generate changelog
                if is_first_publication:
                    changelog = "Initial publication to Zenodo"
                else:
                    if new_deposition_id != dataset.ds_meta_data.deposition_id:
                        changelog = "Re-publication with file changes - new Zenodo version created"
                    else:
                        changelog = "Re-publication without changes"

                logger.info(f"[PUBLISH] Changelog: {changelog}")

                # Create version snapshot
                version_class = VersionService._get_version_class(dataset)
                files_snapshot = VersionService._create_files_snapshot(dataset)

                version = version_class(
                    dataset_id=dataset.id,
                    version_number=version_number,
                    title=dataset.ds_meta_data.title,
                    description=dataset.ds_meta_data.description,
                    files_snapshot=files_snapshot,
                    changelog=changelog,
                    created_by_id=current_user.id,
                    version_doi=deposition_doi,  # Store Zenodo DOI
                )

                # Calculate specific metrics if needed
                if hasattr(version, "total_features"):
                    try:
                        version.total_features = dataset.calculate_total_features() or 0
                        version.total_constraints = dataset.calculate_total_constraints() or 0
                        version.model_count = (
                            dataset.feature_models.count()
                            if hasattr(dataset.feature_models, "count")
                            else len(dataset.feature_models or [])
                        )
                    except Exception as e:
                        logger.warning(f"Could not calculate metrics: {str(e)}")

                db.session.add(version)
                db.session.commit()
                logger.info(
                    f"[PUBLISH] ✅ Created DatasetVersion {version_number} (id={version.id}) with DOI {deposition_doi}"
                )

        except Exception as e:
            logger.error(f"[PUBLISH] ❌ Failed to create DatasetVersion: {str(e)}")
            logger.exception(e)
            # Don't fail the publication if version creation fails

        action = "published" if is_first_publication else "re-published"
        logger.info(f"[PUBLISH] Dataset {dataset_id} {action} successfully")

        return jsonify({"message": f"Dataset {action} successfully", "doi": deposition_doi}), 200
    except Exception as e:
        logger.exception(f"[PUBLISH] Failed to publish dataset {dataset_id}: {e}")
        return jsonify({"message": f"Failed to publish dataset: {str(e)}"}), 500


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

    # Check if this is a conceptual DOI
    if not re.search(r"\.v\d+$", doi):
        # If conceptual DOI - redirect to latest version
        match = re.search(r"fakenodo\.(.+)$", doi)
        if match:
            conceptrecid = match.group(1)
            ds_meta_data = dsmetadata_service.filter_by_conceptrecid(conceptrecid)
            if ds_meta_data and ds_meta_data.data_set:
                dataset = ds_meta_data.data_set
                # Get latest version with DOI
                latest_version = dataset.get_latest_published_version()
                if latest_version and latest_version.version_doi:
                    # Redirect to the specific version DOI
                    return redirect(url_for("dataset.subdomain_index", doi=latest_version.version_doi), code=302)

    ds_meta_data = dsmetadata_service.filter_by_doi(doi)
    if not ds_meta_data:
        abort(404)

    dataset = ds_meta_data.data_set

    is_following_author = False
    if current_user.is_authenticated:
        is_following_author = community_service.is_following_user(current_user.id, dataset.user.id)

    user_cookie = ds_view_record_service.create_cookie(dataset=dataset)
    resp = make_response(
        render_template("dataset/view_dataset.html", dataset=dataset, is_following_author=is_following_author)
    )
    resp.set_cookie("view_cookie", user_cookie)

    return resp


# ========== UNSYNCHRONIZED VIEW ==========


@dataset_bp.route("/dataset/unsynchronized/<int:dataset_id>/", methods=["GET"])
@login_required
def get_unsynchronized_dataset(dataset_id):
    dataset = dataset_service.get_unsynchronized_dataset(current_user.id, dataset_id)
    if not dataset:
        abort(404)
    is_following_author = False
    if current_user.is_authenticated:
        is_following_author = community_service.is_following_user(current_user.id, dataset.user.id)
    return render_template(
        "dataset/view_dataset.html",
        dataset=dataset,
        is_following_author=is_following_author,
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

    # Block manual version creation for published datasets
    # Published datasets use automatic Zenodo versioning only
    if dataset.ds_meta_data.dataset_doi:
        flash(
            "Cannot create local versions for published datasets. Use 'Republish to Zenodo' to create new versions.",
            "warning",
        )
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


@dataset_bp.route("/version/<int:dataset_id>/<int:version_id>/")
def view_version(dataset_id, version_id):
    version = DatasetVersion.query.get_or_404(version_id)

    if version.dataset_id != dataset_id:
        abort(404)

    dataset = version.dataset

    return render_template(
        "dataset/view_version.html",
        dataset=dataset,
        version=version,
    )


@dataset_bp.route("/version/<int:dataset_id>/<int:version_id>/download")
def download_version_zip(dataset_id, version_id):
    version = DatasetVersion.query.get_or_404(version_id)

    if version.dataset_id != dataset_id:
        abort(404)

    dataset = version.dataset

    zip_path = VersionService.build_version_zip(version, dataset)

    return send_file(zip_path, as_attachment=True, download_name=f"{dataset.id}_v{version.version_number}.zip")


# ========== EDIT DATASET ==========


@dataset_bp.route("/dataset/<int:dataset_id>/edit", methods=["GET", "POST"])
@login_required
def edit_dataset(dataset_id):
    dataset = BaseDataset.query.get_or_404(dataset_id)

    if dataset.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        # Solo procesar cambios de metadatos (title, description, tags)
        # Los archivos se procesan en add_files_to_dataset
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

        if changes:
            try:
                db.session.commit()

                if not dataset.ds_meta_data.dataset_doi:
                    try:
                        changelog = "Metadata update:\n" + "\n".join(f"- {c}" for c in changes)
                        version = VersionService.create_version(
                            dataset=dataset,
                            changelog=changelog,
                            user=current_user,
                            bump_type="patch",
                        )
                        flash(
                            f"Dataset updated successfully! New version: v{version.version_number}",
                            "success",
                        )
                    except Exception as e:
                        logger.error(f"Could not create automatic version: {str(e)}")
                        flash(
                            "Dataset updated but version creation failed",
                            "warning",
                        )
                else:
                    flash("Dataset updated successfully!", "success")

                if dataset.ds_meta_data.dataset_doi:
                    return redirect(url_for("dataset.subdomain_index", doi=dataset.ds_meta_data.dataset_doi))
                else:
                    return redirect(url_for("dataset.get_unsynchronized_dataset", dataset_id=dataset.id))

            except Exception as e:
                db.session.rollback()
                flash(f"Error updating dataset: {str(e)}", "danger")

    return render_template("dataset/edit_dataset.html", dataset=dataset)


@dataset_bp.route("/dataset/file/upload_multiple", methods=["POST"])
@login_required
def upload_multiple():
    """
    Sube múltiples archivos a la vez a la carpeta temporal del usuario.
    Usado en la página de edición de datasets.
    """
    files = request.files.getlist("files")
    if not files:
        return jsonify({"success": False, "message": "No files provided"}), 400

    allowed_exts = tuple(get_allowed_extensions())
    temp_folder = current_user.temp_folder()
    os.makedirs(temp_folder, exist_ok=True)

    uploaded_files = []
    errors = []

    for file in files:
        filename = file.filename or ""

        if not any(filename.lower().endswith(ext) for ext in allowed_exts):
            errors.append(f"{filename}: Invalid file type")
            continue

        new_filename = secure_filename(filename)
        file_path = os.path.join(temp_folder, new_filename)

        # Si existe, añadir sufijo numérico
        base, ext = os.path.splitext(new_filename)
        counter = 1
        while os.path.exists(file_path):
            new_filename = f"{base}_{counter}{ext}"
            file_path = os.path.join(temp_folder, new_filename)
            counter += 1

        file.save(file_path)

        kind = infer_kind_from_filename(new_filename)
        descriptor = get_descriptor(kind)

        try:
            descriptor.handler.validate(file_path)
            uploaded_files.append(new_filename)
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            errors.append(f"{filename}: {str(e)}")

    if errors:
        return (
            jsonify(
                {"success": False, "message": "Some files failed validation", "errors": errors, "files": uploaded_files}
            ),
            400,
        )

    return (
        jsonify(
            {
                "success": True,
                "message": f"Successfully uploaded {len(uploaded_files)} file(s)",
                "files": uploaded_files,
                "count": len(uploaded_files),
            }
        ),
        200,
    )


@dataset_bp.route("/dataset/<int:dataset_id>/add_files", methods=["POST"])
@login_required
def add_files_to_dataset(dataset_id):
    """
    Añade archivos importados (desde GitHub, ZIP o local) a un dataset existente.
    Los archivos ya deben estar en la carpeta temporal del usuario.
    """
    dataset = BaseDataset.query.get_or_404(dataset_id)

    if dataset.user_id != current_user.id:
        abort(403)

    # Obtener lista de archivos desde el formulario
    files_to_add = []
    for key in request.form.keys():
        if key.startswith("file_"):
            files_to_add.append(request.form[key])

    if not files_to_add:
        flash("No files to add", "warning")
        return redirect(url_for("dataset.edit_dataset", dataset_id=dataset_id))

    source = request.form.get("source", "unknown")
    temp_folder = current_user.temp_folder()

    working_dir = os.getenv("WORKING_DIR", "")
    dest_dir = os.path.join(
        working_dir,
        "uploads",
        f"user_{current_user.id}",
        f"dataset_{dataset.id}",
    )
    os.makedirs(dest_dir, exist_ok=True)

    added_count = 0
    changes = []

    for filename in files_to_add:
        temp_file_path = os.path.join(temp_folder, filename)

        if not os.path.exists(temp_file_path):
            logger.warning(f"File not found in temp folder: {filename}")
            continue

        # Validar tipo de archivo
        file_kind = infer_kind_from_filename(filename)

        descriptor = get_descriptor(file_kind)

        try:
            descriptor.handler.validate(temp_file_path)
        except Exception as e:
            flash(f"File validation failed for {filename}: {str(e)}", "danger")
            continue

        # Mover archivo a destino definitivo
        dest_file_path = os.path.join(dest_dir, filename)

        # Si existe, añadir sufijo
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_file_path):
            new_filename = f"{base}_{counter}{ext}"
            dest_file_path = os.path.join(dest_dir, new_filename)
            counter += 1
            filename = new_filename

        shutil.move(temp_file_path, dest_file_path)

        # Crear registros en BD
        from app.modules.featuremodel.repositories import (
            FeatureModelRepository,
            FMMetaDataRepository,
        )
        from app.modules.hubfile.repositories import HubfileRepository

        fmmetadata = FMMetaDataRepository().create(
            commit=False,
            filename=filename,
            title=filename,
            description=f"Added via {source}",
            publication_type=PublicationType.NONE,
        )

        fm = FeatureModelRepository().create(
            commit=False,
            data_set_id=dataset.id,
            fm_meta_data_id=fmmetadata.id,
        )

        checksum, size = calculate_checksum_and_size(dest_file_path)

        HubfileRepository().create(
            commit=False,
            name=filename,
            checksum=checksum,
            size=size,
            feature_model_id=fm.id,
        )

        added_count += 1
        changes.append(f"Added file from {source}: {filename}")

    if added_count > 0:
        try:
            db.session.commit()

            # Crear versión automática si no está sincronizado
            if not dataset.ds_meta_data.dataset_doi:
                try:
                    changelog = f"Added {added_count} file(s) from {source}:\n" + "\n".join(f"- {c}" for c in changes)
                    version = VersionService.create_version(
                        dataset=dataset,
                        changelog=changelog,
                        user=current_user,
                        bump_type="minor",
                    )
                    flash(
                        f"Successfully added {added_count} file(s)! New version: v{version.version_number} 🎉",
                        "success",
                    )
                except Exception as e:
                    logger.error(f"Could not create automatic version: {str(e)}")
                    flash(
                        f"Files added successfully but version creation failed ({added_count} files)",
                        "warning",
                    )
            else:
                flash(f"Successfully added {added_count} file(s)! ✅", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Error saving files: {str(e)}", "danger")
            return redirect(url_for("dataset.edit_dataset", dataset_id=dataset_id))
    else:
        flash("No files were added", "warning")

    if dataset.ds_meta_data.dataset_doi:
        return redirect(url_for("dataset.subdomain_index", doi=dataset.ds_meta_data.dataset_doi))
    else:
        return redirect(url_for("dataset.get_unsynchronized_dataset", dataset_id=dataset.id))


# ========== DATASET COMMENTS ==========
@dataset_bp.route("/dataset/<int:dataset_id>/comments", methods=["POST"])
@login_required
def create_comment(dataset_id):
    """Crear un comentario en un dataset."""
    from app.modules.dataset.services import CommentService

    try:
        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"success": False, "message": "Content is required"}), 400

        comment_service = CommentService()
        comment = comment_service.create_comment(
            dataset_id=dataset_id, user_id=current_user.id, content=data["content"]
        )

        return jsonify({"success": True, "comment": comment}), 201

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating comment: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500


@dataset_bp.route("/dataset/<int:dataset_id>/comments", methods=["GET"])
def get_comments(dataset_id):
    """Listar comentarios de un dataset (público)."""
    from app.modules.dataset.services import CommentService

    try:
        comment_service = CommentService()
        comments = comment_service.get_comments_by_dataset(dataset_id)

        return jsonify({"success": True, "comments": comments}), 200

    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500


@dataset_bp.route("/dataset/comments/<int:comment_id>", methods=["DELETE"])
@login_required
def delete_comment(comment_id):
    """
    Eliminar comentario.
    Puede hacerlo el autor del comentario O el propietario del dataset.
    """
    from app.modules.dataset.services import CommentService

    try:
        comment_service = CommentService()
        comment_service.delete_comment(comment_id, current_user.id)
        return jsonify({"success": True, "message": "Comment deleted successfully"}), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {str(e)}")
        return jsonify({"success": False, "error": "Failed to delete comment"}), 500


@dataset_bp.route("/dataset/comments/<int:comment_id>", methods=["PUT"])
@login_required
def update_comment(comment_id):
    """
    Actualizar comentario.
    Solo el autor del comentario puede editarlo.
    """
    from app.modules.dataset.services import CommentService

    try:
        comment_service = CommentService()
        data = request.get_json()
        content = data.get("content", "").strip()

        if not content:
            return jsonify({"success": False, "error": "Content cannot be empty"}), 400

        updated = comment_service.update_comment(comment_id, current_user.id, content)
        return jsonify({"success": True, "comment": updated}), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        logger.error(f"Error updating comment {comment_id}: {str(e)}")
        return jsonify({"success": False, "error": "Failed to update comment"}), 500


# ======================================================================
# RUTAS DE COMENTARIOS
# ======================================================================


@dataset_bp.route("/dataset/<int:dataset_id>/comments/<int:comment_id>/reply", methods=["POST"])
@login_required
def reply_to_comment(dataset_id, comment_id):
    """
    Crear una respuesta (reply) a un comentario de un dataset.
    """
    from app.modules.dataset.services import CommentService

    comment_service = CommentService()

    comment = comment_service.get_comment_by_id(comment_id)
    if not comment or comment.dataset_id != dataset_id:
        return jsonify({"success": False, "message": "Comment not found"}), 404

    data = request.get_json() or request.form
    content = data.get("content")

    if not content or not content.strip():
        return jsonify({"success": False, "message": "Message cannot be empty"}), 400

    try:
        reply = comment_service.reply_to_comment(
            original_comment_id=comment_id,
            user_id=current_user.id,
            content=content.strip(),
        )
        return jsonify({"success": True, "comment": reply}), 201

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception:
        logger.exception("Error posting reply")
        return jsonify({"success": False, "message": "Internal server error"}), 500
