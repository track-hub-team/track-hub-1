var currentId = 0;
var amount_authors = 0;

function show_upload_dataset() {
    document.getElementById('upload_dataset').style.display = 'block';
}

function generateIncrementalId() {
    return currentId++;
}

function addField(newAuthor, name, text, className = 'col-lg-6 col-12 mb-3') {
    let fieldWrapper = document.createElement('div');
    fieldWrapper.className = className;

    let label = document.createElement('label');
    label.className = 'form-label';
    label.for = name;
    label.textContent = text;

    let field = document.createElement('input');
    field.name = name;
    field.className = 'form-control';

    fieldWrapper.appendChild(label);
    fieldWrapper.appendChild(field);
    newAuthor.appendChild(fieldWrapper);
}

function addRemoveButton(newAuthor) {
    let buttonWrapper = document.createElement('div');
    buttonWrapper.className = 'col-12 mb-2';

    let button = document.createElement('button');
    button.textContent = 'Remove author';
    button.className = 'btn btn-danger btn-sm';
    button.type = 'button';
    button.addEventListener('click', function (event) {
        event.preventDefault();
        newAuthor.remove();
    });

    buttonWrapper.appendChild(button);
    newAuthor.appendChild(buttonWrapper);
}

function createAuthorBlock(idx, suffix = "") {
    let newAuthor = document.createElement('div');
    newAuthor.className = 'author-block row mb-3';

    // Campo Name
    let nameCol = document.createElement('div');
    nameCol.className = 'col-md-4';
    nameCol.innerHTML = `
        <label class="form-label">Name *</label>
        <input type="text" name="${suffix}authors-${idx}-name" class="form-control" required>
    `;
    newAuthor.appendChild(nameCol);

    // Campo Affiliation
    let affiliationCol = document.createElement('div');
    affiliationCol.className = 'col-md-4';
    affiliationCol.innerHTML = `
        <label class="form-label">Affiliation</label>
        <input type="text" name="${suffix}authors-${idx}-affiliation" class="form-control">
    `;
    newAuthor.appendChild(affiliationCol);

    // Campo ORCID
    let orcidCol = document.createElement('div');
    orcidCol.className = 'col-md-3';
    orcidCol.innerHTML = `
        <label class="form-label">ORCID</label>
        <input type="text" name="${suffix}authors-${idx}-orcid" class="form-control" placeholder="0000-0000-0000-0000">
    `;
    newAuthor.appendChild(orcidCol);

    // Botón de eliminar
    let removeCol = document.createElement('div');
    removeCol.className = 'col-md-1 d-flex align-items-end';
    let removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-danger btn-sm remove-author';
    removeBtn.innerHTML = '<i data-feather="trash-2"></i>';
    removeBtn.addEventListener('click', function () {
        newAuthor.remove();
    });
    removeCol.appendChild(removeBtn);
    newAuthor.appendChild(removeCol);

    return newAuthor;
}

// Evento para añadir autores
document.addEventListener('DOMContentLoaded', function() {
    const addAuthorBtn = document.getElementById('add_author');
    if (addAuthorBtn) {
        addAuthorBtn.addEventListener('click', function () {
            let authorsList = document.getElementById('authors_list');
            let currentAuthors = authorsList.querySelectorAll('.author-block').length;
            let newAuthor = createAuthorBlock(currentAuthors, "");
            authorsList.appendChild(newAuthor);

            // Actualizar íconos de Feather
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        });
    }

    // Evento para eliminar autores (delegación de eventos)
    const authorsList = document.getElementById('authors_list');
    if (authorsList) {
        authorsList.addEventListener('click', function(e) {
            if (e.target.closest('.remove-author')) {
                const authorBlock = e.target.closest('.author-block');
                if (authorBlock) {
                    authorBlock.remove();
                }
            }
        });
    }
});

function check_title_and_description() {
    let titleInput = document.querySelector('input[name="title"]');
    let descriptionTextarea = document.querySelector('textarea[name="desc"]');

    if (!titleInput || !descriptionTextarea) {
        return false;
    }

    titleInput.classList.remove("error");
    descriptionTextarea.classList.remove("error");
    clean_upload_errors();

    let titleLength = titleInput.value.trim().length;
    let descriptionLength = descriptionTextarea.value.trim().length;

    if (titleLength < 3) {
        write_upload_error("Title must be at least 3 characters long");
        titleInput.classList.add("error");
        return false;
    }

    if (descriptionLength < 3) {
        write_upload_error("Description must be at least 3 characters long");
        descriptionTextarea.classList.add("error");
        return false;
    }

    return true;
}

function show_loading() {
    const uploadBtn = document.getElementById("upload_dataset_btn");
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
    }
}

function hide_loading() {
    const uploadBtn = document.getElementById("upload_dataset_btn");
    if (uploadBtn) {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i data-feather="upload"></i> Upload dataset';
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

function clean_upload_errors() {
    const errorContainer = document.getElementById('upload_errors');
    if (errorContainer) {
        errorContainer.innerHTML = '';
        errorContainer.style.display = 'none';
    }
}

function write_upload_error(error_message) {
    const errorContainer = document.getElementById('upload_errors');
    if (errorContainer) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            ${error_message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        errorContainer.appendChild(errorDiv);
        errorContainer.style.display = 'block';
    } else {
        alert('Upload error: ' + error_message);
    }
    console.error('Upload error:', error_message);
}

function isValidOrcid(orcid) {
    let orcidRegex = /^\d{4}-\d{4}-\d{4}-\d{4}$/;
    return orcidRegex.test(orcid);
}

// ========================================
// DROPZONE PARA UVL
// ========================================
Dropzone.options.uvlDropzone = {
    paramName: "file",
    maxFilesize: 20,
    acceptedFiles: ".uvl",
    dictDefaultMessage: "Drop UVL files here or click to browse",
    dictFileTooBig: "File is too big ({{filesize}}MB). Max: {{maxFilesize}}MB",
    dictInvalidFileType: "Invalid file type. Only .uvl files allowed",

    init: function () {
        const dz = this;

        dz.on("success", function (file, response) {
            if (typeof show_upload_dataset === "function") show_upload_dataset();

            const fileList = document.getElementById("uvl-file-list");
            const li = document.createElement("li");
            li.className = "file-item mb-3 p-3 border rounded";

            const h4 = document.createElement("h4");
            h4.className = "h6 mb-2";
            h4.innerHTML = `<i data-feather="file-text"></i> ${response.filename}`;
            li.appendChild(h4);

            const id = generateIncrementalId();

            // Botones
            const btnInfo = document.createElement("button");
            btnInfo.type = "button";
            btnInfo.textContent = "Show info";
            btnInfo.className = "btn btn-outline-secondary btn-sm me-2";

            const btnDel = document.createElement("button");
            btnDel.type = "button";
            btnDel.textContent = "Delete";
            btnDel.className = "btn btn-outline-danger btn-sm";

            li.appendChild(btnInfo);
            li.appendChild(btnDel);

            // ✅ Formulario específico para UVL
            const form = document.createElement("div");
            form.className = "uvl_form mt-3";
            form.style.display = "none";
            form.innerHTML = `
                <div class="row">
                    <input type="hidden" name="feature_models-${id}-filename" value="${response.filename}">

                    <div class="col-12 mb-3">
                        <label class="form-label">Title *</label>
                        <input type="text" class="form-control" name="feature_models-${id}-title" required>
                    </div>

                    <div class="col-12 mb-3">
                        <label class="form-label">Description</label>
                        <textarea rows="3" class="form-control" name="feature_models-${id}-desc"></textarea>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">UVL Version</label>
                        <input type="text" class="form-control" name="feature_models-${id}-file_version" value="1.0">
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Publication type</label>
                        <select class="form-control" name="feature_models-${id}-publication_type">
                            <option value="none">None</option>
                            <option value="conference_paper">Conference paper</option>
                            <option value="journal_article">Journal article</option>
                            <option value="technical_note">Technical note</option>
                            <option value="other">Other</option>
                        </select>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Publication DOI</label>
                        <input type="text" class="form-control" name="feature_models-${id}-publication_doi" placeholder="10.1234/example.doi">
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Tags (separated by commas)</label>
                        <input type="text" class="form-control" name="feature_models-${id}-tags" placeholder="feature-model, spl, variability">
                    </div>
                </div>
            `;

            // Event listeners
            btnInfo.addEventListener("click", function () {
                const visible = form.style.display !== "none";
                form.style.display = visible ? "none" : "block";
                btnInfo.textContent = visible ? "Show info" : "Hide info";
            });

            btnDel.addEventListener("click", function () {
                fileList.removeChild(li);
                dz.removeFile(file);
                fetch("/dataset/file/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file: response.filename }),
                }).catch(() => {});
            });

            li.appendChild(form);
            fileList.appendChild(li);

            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        });

        dz.on("error", function (file, errorMessage) {
            console.error("UVL Upload error:", errorMessage);
            const alerts = document.getElementById("uvl-alerts");
            if (alerts) {
                alerts.innerHTML = `<div class="alert alert-danger alert-dismissible fade show">
                    ${errorMessage}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>`;
            }
            dz.removeFile(file);
        });
    }
};

// ========================================
// DROPZONE PARA GPX
// ========================================
Dropzone.options.gpxDropzone = {
    paramName: "file",
    maxFilesize: 20,
    acceptedFiles: ".gpx",
    dictDefaultMessage: "Drop GPX files here or click to browse",
    dictFileTooBig: "File is too big ({{filesize}}MB). Max: {{maxFilesize}}MB",
    dictInvalidFileType: "Invalid file type. Only .gpx files allowed",

    init: function () {
        const dz = this;

        dz.on("success", function (file, response) {
            if (typeof show_upload_dataset === "function") show_upload_dataset();

            const fileList = document.getElementById("gpx-file-list");
            const li = document.createElement("li");
            li.className = "file-item mb-3 p-3 border rounded";

            const h4 = document.createElement("h4");
            h4.className = "h6 mb-2";
            h4.innerHTML = `<i data-feather="map-pin"></i> ${response.filename}`;
            li.appendChild(h4);

            const id = generateIncrementalId();

            // Botones
            const btnInfo = document.createElement("button");
            btnInfo.type = "button";
            btnInfo.textContent = "Show info";
            btnInfo.className = "btn btn-outline-secondary btn-sm me-2";

            const btnDel = document.createElement("button");
            btnDel.type = "button";
            btnDel.textContent = "Delete";
            btnDel.className = "btn btn-outline-danger btn-sm";

            li.appendChild(btnInfo);
            li.appendChild(btnDel);

            // ✅ Formulario específico para GPX con publication_type
            const form = document.createElement("div");
            form.className = "gpx_form mt-3";
            form.style.display = "none";
            form.innerHTML = `
                <div class="row">
                    <input type="hidden" name="feature_models-${id}-filename" value="${response.filename}">

                    <div class="col-12 mb-3">
                        <label class="form-label">Track Name *</label>
                        <input type="text" class="form-control" name="feature_models-${id}-title" required>
                    </div>

                    <div class="col-12 mb-3">
                        <label class="form-label">Description</label>
                        <textarea rows="3" class="form-control" name="feature_models-${id}-desc" placeholder="Describe your track..."></textarea>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">GPX Version</label>
                        <input type="text" class="form-control" name="feature_models-${id}-file_version" value="1.1" readonly>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Track Type</label>
                        <select class="form-control" name="feature_models-${id}-gpx_type">
                            <option value="run">Running</option>
                            <option value="bike">Cycling</option>
                            <option value="hike">Hiking</option>
                            <option value="walk">Walking</option>
                            <option value="other">Other</option>
                        </select>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Publication type</label>
                        <select class="form-control" name="feature_models-${id}-publication_type">
                            <option value="none">None</option>
                            <option value="conference_paper">Conference paper</option>
                            <option value="journal_article">Journal article</option>
                            <option value="technical_note">Technical note</option>
                            <option value="other">Other</option>
                        </select>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Publication DOI</label>
                        <input type="text" class="form-control" name="feature_models-${id}-publication_doi" placeholder="10.1234/example.doi">
                    </div>

                    <div class="col-12 mb-3">
                        <label class="form-label">Tags (separated by commas)</label>
                        <input type="text" class="form-control" name="feature_models-${id}-tags" placeholder="outdoor, gps, trail">
                    </div>
                </div>
            `;

            // Event listeners
            btnInfo.addEventListener("click", function () {
                const visible = form.style.display !== "none";
                form.style.display = visible ? "none" : "block";
                btnInfo.textContent = visible ? "Show info" : "Hide info";
            });

            btnDel.addEventListener("click", function () {
                fileList.removeChild(li);
                dz.removeFile(file);
                fetch("/dataset/file/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file: response.filename }),
                }).catch(() => {});
            });

            li.appendChild(form);
            fileList.appendChild(li);

            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        });

        dz.on("error", function (file, errorMessage) {
            console.error("GPX Upload error:", errorMessage);
            const alerts = document.getElementById("gpx-alerts");
            if (alerts) {
                alerts.innerHTML = `<div class="alert alert-danger alert-dismissible fade show">
                    ${errorMessage}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>`;
            }
            dz.removeFile(file);
        });
    }
};

// ========================================
// IMPORT FROM GITHUB
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    // Buscar directamente por ID (como hace ZIP)
    const githubBtn = document.getElementById('import_github_btn');

    if (githubBtn) {

        githubBtn.addEventListener('click', function() {

            // Buscar input por ID también
            const githubUrlInput = document.getElementById('github_url');
            const githubUrl = githubUrlInput ? githubUrlInput.value.trim() : '';

            // Contenedor de alertas (crear si no existe)
            let alertsContainer = document.getElementById('github-alerts');
            if (!alertsContainer) {
                alertsContainer = githubBtn.closest('.card-body').querySelector('#github-alerts');
            }
            if (!alertsContainer) {
                alertsContainer = document.createElement('div');
                alertsContainer.id = 'github-alerts';
                alertsContainer.className = 'mt-3';
                const cardBody = githubBtn.closest('.card-body');
                const firstChild = cardBody.querySelector('.mb-3');
                if (firstChild) {
                    cardBody.insertBefore(alertsContainer, firstChild);
                } else {
                    cardBody.insertBefore(alertsContainer, githubBtn);
                }
            }

            // Validación básica
            if (!githubUrl) {
                showAlert(alertsContainer, 'Please enter a GitHub URL', 'danger');
                return;
            }

            if (!githubUrl.includes('github.com')) {
                showAlert(alertsContainer, 'Invalid GitHub URL', 'danger');
                return;
            }

            // Deshabilitar botón y mostrar loading
            const originalHTML = githubBtn.innerHTML;
            githubBtn.disabled = true;
            githubBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Importing...';

            // Limpiar alertas previas
            alertsContainer.innerHTML = '';


            // Llamar al endpoint
            fetch('/dataset/import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ github_url: githubUrl })
            })
            .then(response => {
                console.log('GitHub response status:', response.status); // Debug
                if (!response.ok) {
                    return response.json().then(err => Promise.reject(err));
                }
                return response.json();
            })
            .then(data => {
                console.log('GitHub import success:', data); // Debug

                githubBtn.disabled = false;
                githubBtn.innerHTML = originalHTML;

                if (typeof feather !== 'undefined') {
                    feather.replace();
                }

                if (data.files && data.files.length > 0) {
                    // Éxito
                    showAlert(alertsContainer,
                        `Successfully imported ${data.count} file(s) from GitHub`,
                        'success'
                    );

                    // Mostrar archivos importados
                    displayImportedFiles('github', data.files);

                    // Limpiar el input
                    if (githubUrlInput) {
                        githubUrlInput.value = '';
                    }

                    // Mostrar botón de submit del dataset si estaba oculto
                    show_upload_dataset();
                } else {
                    showAlert(alertsContainer, data.message || 'No files imported', 'warning');
                }
            })
            .catch(error => {
                console.error('GitHub import error:', error); // Debug

                githubBtn.disabled = false;
                githubBtn.innerHTML = originalHTML;

                if (typeof feather !== 'undefined') {
                    feather.replace();
                }

                const errorMsg = error.message || 'Failed to import from GitHub';
                showAlert(alertsContainer, `${errorMsg}`, 'danger');
            });
        });
    }
});


// ========================================
// IMPORT FROM ZIP
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    // Buscar el botón por el texto
    const zipBtn = Array.from(document.querySelectorAll('button')).find(btn =>
        btn.textContent.includes('Import from ZIP')
    );

    if (zipBtn) {
        zipBtn.addEventListener('click', function() {
            const zipFileInput = document.querySelector('input[type="file"][accept=".zip"]');

            // Contenedor de alertas
            let alertsContainer = zipBtn.closest('.card-body').querySelector('.alerts-container');
            if (!alertsContainer) {
                alertsContainer = document.createElement('div');
                alertsContainer.className = 'alerts-container mt-3';
                zipBtn.parentNode.insertBefore(alertsContainer, zipBtn.nextSibling);
            }

            // Validación básica
            if (!zipFileInput || !zipFileInput.files || zipFileInput.files.length === 0) {
                showAlert(alertsContainer, 'Please select a ZIP file', 'danger');
                return;
            }

            const file = zipFileInput.files[0];

            if (!file.name.toLowerCase().endsWith('.zip')) {
                showAlert(alertsContainer, 'Only ZIP files are allowed', 'danger');
                return;
            }

            // Validar tamaño (100 MB)
            const maxSize = 100 * 1024 * 1024; // 100 MB en bytes
            if (file.size > maxSize) {
                showAlert(alertsContainer, 'File is too large. Maximum size: 100 MB', 'danger');
                return;
            }

            // Deshabilitar botón y mostrar loading
            const originalHTML = zipBtn.innerHTML;
            zipBtn.disabled = true;
            zipBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Importing...';

            // Limpiar alertas previas
            alertsContainer.innerHTML = '';

            // Crear FormData
            const formData = new FormData();
            formData.append('file', file);

            // Llamar al endpoint
            fetch('/dataset/import', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => Promise.reject(err));
                }
                return response.json();
            })
            .then(data => {
                zipBtn.disabled = false;
                zipBtn.innerHTML = originalHTML;

                if (typeof feather !== 'undefined') {
                    feather.replace();
                }

                if (data.files && data.files.length > 0) {
                    // Éxito
                    showAlert(alertsContainer,
                        `Successfully imported ${data.count} file(s) from ZIP`,
                        'success'
                    );

                    // Mostrar archivos importados
                    displayImportedFiles('zip', data.files);

                    // Limpiar el input
                    if (zipFileInput) {
                        zipFileInput.value = '';
                    }

                    // Mostrar botón de submit del dataset si estaba oculto
                    show_upload_dataset();
                } else {
                    showAlert(alertsContainer, data.message || 'No files imported', 'warning');
                }
            })
            .catch(error => {
                zipBtn.disabled = false;
                zipBtn.innerHTML = originalHTML;

                if (typeof feather !== 'undefined') {
                    feather.replace();
                }

                console.error('ZIP import error:', error);
                const errorMsg = error.message || 'Failed to import from ZIP';
                showAlert(alertsContainer, `${errorMsg}`, 'danger');
            });
        });
    }
});


// ========================================
// FUNCIONES AUXILIARES
// ========================================

function showAlert(container, message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    container.appendChild(alertDiv);

    // Auto-dismiss después de 5 segundos (solo para success)
    if (type === 'success') {
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
}

function displayImportedFiles(source, files) {
    // Determinar IDs según la fuente
    const containerId = source === 'github' ? 'github-imported-files' : 'zip-imported-files';
    const listId = source === 'github' ? 'github-file-list' : 'zip-file-list';

    // Obtener elementos del DOM (ya existen en el HTML)
    const container = document.getElementById(containerId);
    const list = document.getElementById(listId);

    if (!container || !list) {
        console.error(`Elements not found: ${containerId} or ${listId}`);
        return;
    }

    // Limpiar lista previa
    list.innerHTML = '';

    // Añadir archivos
    files.forEach(filename => {
        const li = document.createElement('li');
        li.className = 'mb-2';

        // Detectar tipo de archivo
        const isUVL = filename.toLowerCase().endsWith('.uvl');
        const icon = isUVL ? 'git-branch' : 'map-pin';
        const badge = isUVL ? 'UVL' : 'GPX';
        const badgeClass = isUVL ? 'bg-success' : 'bg-info';

        li.innerHTML = `
            <i data-feather="${icon}" style="width: 16px; height: 16px;"></i>
            <span class="badge ${badgeClass} me-2">${badge}</span>
            <code>${filename}</code>
        `;

        list.appendChild(li);

        createHiddenFormForImportedFile(filename, isUVL);
    });

    // Mostrar contenedor
    container.style.display = 'block';

    // Actualizar íconos de Feather
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

function createHiddenFormForImportedFile(filename, isUVL) {
    const id = generateIncrementalId();

    // Determinar dónde agregar el formulario
    const fileListId = isUVL ? 'uvl-file-list' : 'gpx-file-list';
    const fileList = document.getElementById(fileListId);

    if (!fileList) {
        console.error(`File list not found: ${fileListId}`);
        return;
    }

    // Crear elemento de lista (oculto, solo para el formulario)
    const li = document.createElement('li');
    li.className = 'file-item-hidden';
    li.style.display = 'none'; // Oculto porque ya se muestra en la lista de importados
    li.setAttribute('data-imported', 'true'); // Marcar como importado

    // Crear formulario según el tipo
    const formClass = isUVL ? 'uvl_form' : 'gpx_form';
    const form = document.createElement('div');
    form.className = formClass;

    // Extraer nombre base sin extensión
    const baseName = filename.replace(/\.(uvl|gpx)$/i, '');

    if (isUVL) {
        form.innerHTML = `
            <input type="hidden" name="feature_models-${id}-filename" value="${filename}">
            <input type="hidden" name="feature_models-${id}-title" value="${baseName}">
            <input type="hidden" name="feature_models-${id}-desc" value="Imported file">
            <input type="hidden" name="feature_models-${id}-file_version" value="1.0">
            <input type="hidden" name="feature_models-${id}-publication_type" value="none">
            <input type="hidden" name="feature_models-${id}-publication_doi" value="">
            <input type="hidden" name="feature_models-${id}-tags" value="">
        `;
    } else {
        // GPX
        form.innerHTML = `
            <input type="hidden" name="feature_models-${id}-filename" value="${filename}">
            <input type="hidden" name="feature_models-${id}-title" value="${baseName}">
            <input type="hidden" name="feature_models-${id}-desc" value="Imported GPX track">
            <input type="hidden" name="feature_models-${id}-file_version" value="1.1">
            <input type="hidden" name="feature_models-${id}-gpx_type" value="other">
            <input type="hidden" name="feature_models-${id}-publication_type" value="none">
            <input type="hidden" name="feature_models-${id}-publication_doi" value="">
            <input type="hidden" name="feature_models-${id}-tags" value="">
        `;
    }

    li.appendChild(form);
    fileList.appendChild(li);

    console.log(`Created hidden form for ${filename} with ID ${id}`);
}

// Detectar fuente de importación
function getImportSource() {
    // Determinar si fue GitHub o ZIP basándose en cuál lista tiene archivos
    const githubFiles = document.querySelectorAll('#github-file-list li').length;
    const zipFiles = document.querySelectorAll('#zip-file-list li').length;

    if (githubFiles > 0 && zipFiles === 0) return 'GitHub';
    if (zipFiles > 0 && githubFiles === 0) return 'ZIP';
    return 'Import'; // Por si hay ambos
}


// ========================================
// SUBMIT DEL FORMULARIO
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    const uploadBtn = document.getElementById('upload_dataset_btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function(e) {
            e.preventDefault();

            // Validar que hay al menos 1 archivo UVL o GPX
            const uvlForms = document.querySelectorAll('.uvl_form').length;
            const gpxForms = document.querySelectorAll('.gpx_form').length;

            const totalFiles = uvlForms + gpxForms;

            console.log(`Total forms found: UVL=${uvlForms}, GPX=${gpxForms}, Total=${totalFiles}`);

            if (totalFiles === 0) {
                write_upload_error('Please upload at least one file (UVL or GPX) using any of the available methods');
                return;
            }

            // Validar título y descripción
            if (!check_title_and_description()) {
                return;
            }

            // Validar autores
            const authors = document.querySelectorAll('.author-block');
            let validAuthors = true;

            authors.forEach((author) => {
                const nameInput = author.querySelector('input[name*="-name"]');
                const orcidInput = author.querySelector('input[name*="-orcid"]');

                if (nameInput && nameInput.value.trim() === '') {
                    write_upload_error("Author's name cannot be empty");
                    validAuthors = false;
                    return;
                }

                if (orcidInput && orcidInput.value.trim() !== '' && !isValidOrcid(orcidInput.value.trim())) {
                    write_upload_error("ORCID value does not conform to valid format: " + orcidInput.value);
                    validAuthors = false;
                    return;
                }
            });

            if (!validAuthors) {
                return;
            }

            clean_upload_errors();
            show_loading();

            // Recopilar datos del formulario
            const formData = new FormData();

            // CSRF Token
            const csrfToken = document.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                formData.append('csrf_token', csrfToken.value);
            }

            // Información básica
            const basicForm = document.getElementById('basic_info_form');
            if (basicForm) {
                const inputs = basicForm.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.name && input.name !== 'csrf_token') {
                        formData.append(input.name, input.value);
                    }
                });
            }

            // Añadir feature models de UVL
            document.querySelectorAll('.uvl_form').forEach(form => {
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.name) {
                        formData.append(input.name, input.value);
                    }
                });
            });

            // Añadir feature models de GPX
            document.querySelectorAll('.gpx_form').forEach(form => {
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.name) {
                        formData.append(input.name, input.value);
                    }
                });
            });

            // Añadir autores
            authors.forEach((author) => {
                const inputs = author.querySelectorAll('input');
                inputs.forEach(input => {
                    if (input.name) {
                        formData.append(input.name, input.value);
                    }
                });
            });

            // Debug: mostrar datos que se van a enviar
            console.log('FormData contents:');
            for (let pair of formData.entries()) {
                console.log(pair[0] + ': ' + pair[1]);
            }

            // Enviar formulario
            fetch('/dataset/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log('Response status:', response.status);
                return response.json().then(data => {
                    return { status: response.status, data: data };
                });
            })
            .then(result => {
                hide_loading();
                console.log('Response data:', result.data);

                if (result.status === 200) {
                    window.location.href = '/dataset/list';
                } else {
                    const errorMessage = result.data.message || 'Unknown error';
                    const errors = result.data.errors || [];

                    let fullError = errorMessage;
                    if (errors.length > 0) {
                        fullError += '\n\nDetails:\n' + errors.join('\n');
                    }

                    write_upload_error(fullError);
                }
            })
            .catch(error => {
                hide_loading();
                console.error('Fetch error:', error);
                write_upload_error('Network error: ' + error.message);
            });
        });
    }
});

// ========================================
// TEST ZENODO CONNECTION (si existe)
// ========================================
window.addEventListener('load', function() {
    if (typeof test_zenodo_connection === "function") {
        test_zenodo_connection();
    }
});
