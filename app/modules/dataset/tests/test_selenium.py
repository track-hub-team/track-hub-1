import os
import time
import zipfile

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def count_datasets(driver, host):
    driver.get(f"{host}/dataset/list")
    wait_for_page_to_load(driver)

    try:
        amount_datasets = len(driver.find_elements(By.XPATH, "//table//tbody//tr"))
    except Exception:
        amount_datasets = 0
    return amount_datasets


def login_user(driver, host):
    """Helper para hacer login - reutilizable"""
    driver.get(f"{host}/login")
    wait_for_page_to_load(driver)

    email_field = driver.find_element(By.NAME, "email")
    password_field = driver.find_element(By.NAME, "password")

    email_field.send_keys("user1@example.com")
    password_field.send_keys("1234")
    password_field.send_keys(Keys.RETURN)

    time.sleep(4)
    wait_for_page_to_load(driver)


def test_upload_dataset():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Login
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)

        time.sleep(3)
        wait_for_page_to_load(driver)

        # Contar datasets iniciales
        initial_datasets = count_datasets(driver, host)

        # Ir a la página de upload
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Rellenar datos básicos (title, desc, tags)
        title_field = driver.find_element(By.NAME, "title")
        title_field.clear()
        title_field.send_keys("Title desde Selenium")

        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.clear()
        desc_field.send_keys("Description desde Selenium")

        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.clear()
        tags_field.send_keys("tag1,tag2")

        # El primer autor (authors-0-*) ya es el usuario logueado y es readonly.
        # No tocamos nada de autores en este test.

        # Rutas correctas a los UVL (relativas al propio test)
        file1_path = os.path.abspath(os.path.join(BASE_DIR, "..", "uvl_examples", "file1.uvl"))
        file2_path = os.path.abspath(os.path.join(BASE_DIR, "..", "uvl_examples", "file2.uvl"))

        assert os.path.exists(file1_path), f"No se encuentra file1.uvl en {file1_path}"
        assert os.path.exists(file2_path), f"No se encuentra file2.uvl en {file2_path}"

        # Subir archivos al dropzone UVL
        # Dropzone crea un <input type="file" class="dz-hidden-input"> dentro del form
        # Dropzone crea un input oculto global con clase "dz-hidden-input"
        dropzone_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.dz-hidden-input"))
        )

        # Subir primer archivo
        dropzone_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.dz-hidden-input"))
        )
        dropzone_input.send_keys(file1_path)

        # Dropzone reemplaza el input → debemos volver a obtenerlo
        time.sleep(1)

        dropzone_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.dz-hidden-input"))
        )
        dropzone_input.send_keys(file2_path)

        # Esperar a que aparezca la sección de "Upload dataset" (la muestra el JS)
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.ID, "upload_dataset")))

        # Marcar checkbox de confirmación (id real: confirm_upload)
        confirm_checkbox = driver.find_element(By.ID, "confirm_upload")
        if not confirm_checkbox.is_selected():
            confirm_checkbox.click()

        # Pulsar botón de upload (id real: upload_dataset_btn)
        upload_btn = driver.find_element(By.ID, "upload_dataset_btn")
        upload_btn.click()

        WebDriverWait(driver, 10).until(EC.url_contains("/dataset/list"))

        # Comprobar redirección a la lista
        assert driver.current_url == f"{host}/dataset/list", f"URL tras subir: {driver.current_url}"

        # Contar datasets finales
        final_datasets = count_datasets(driver, host)
        assert (
            final_datasets == initial_datasets + 1
        ), f"Esperaba {initial_datasets + 1} datasets, pero hay {final_datasets}"

        print("test_upload_dataset pasó correctamente")

    finally:
        close_driver(driver)


def test_import_from_github():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        login_user(driver, host)

        initial_datasets = count_datasets(driver, host)

        # Ir a la página de upload
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Rellenar URL del repo (ID correcto: github_url)
        github_url_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "github_url")))
        github_url_input.clear()
        github_url_input.send_keys("https://github.com/pcm290/testgithubrepositorytrackhub")

        # Pulsar el botón real (ID correcto: import_github_btn)
        import_btn = driver.find_element(By.ID, "import_github_btn")
        import_btn.click()

        # Esperar a que se muestren archivos importados
        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#github-file-list li")))

        # Rellenar metadata básica
        title_field = driver.find_element(By.NAME, "title")
        title_field.send_keys("Dataset desde GitHub")

        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.send_keys("Dataset importado automáticamente desde GitHub")

        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.send_keys("github,import,test")

        # Añadir un autor extra
        add_author_button = driver.find_element(By.ID, "add_author")
        add_author_button.click()
        wait_for_page_to_load(driver)

        name_field = driver.find_element(By.NAME, "authors-1-name")
        name_field.send_keys("GitHub Selenium")

        affiliation_field = driver.find_element(By.NAME, "authors-1-affiliation")
        affiliation_field.send_keys("Selenium Institute")

        # Confirmar subida
        confirm_checkbox = driver.find_element(By.ID, "confirm_upload")
        if not confirm_checkbox.is_selected():
            confirm_checkbox.click()

        upload_btn = driver.find_element(By.ID, "upload_dataset_btn")
        upload_btn.click()

        wait_for_page_to_load(driver)
        time.sleep(3)

        assert driver.current_url == f"{host}/dataset/list", f"URL inesperada tras subir dataset: {driver.current_url}"

        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, f"Esperaba {initial_datasets + 1}, pero hay {final_datasets}"

        print("test_import_from_github pasó correctamente")

    finally:
        close_driver(driver)


def test_import_from_zip():
    """
    TEST: Importar archivos desde un ZIP (corrregido según plantillas actuales)
    """
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        login_user(driver, host)

        initial_datasets = count_datasets(driver, host)

        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Crear ZIP de prueba en tiempo real
        zip_dir = os.path.join(BASE_DIR, "..", "test_data")
        os.makedirs(zip_dir, exist_ok=True)

        zip_path = os.path.join(zip_dir, "sample_models.zip")

        # Archivos UVL reales
        file1 = os.path.join(BASE_DIR, "..", "uvl_examples", "file1.uvl")
        file2 = os.path.join(BASE_DIR, "..", "uvl_examples", "file2.uvl")

        assert os.path.exists(file1), f"No se encuentra {file1}"
        assert os.path.exists(file2), f"No se encuentra {file2}"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(file1, "file1.uvl")
            zf.write(file2, "file2.uvl")

        assert os.path.exists(zip_path), f"ZIP no creado: {zip_path}"

        # 👉 Input real: id="zip_file"
        zip_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "zip_file")))
        zip_input.send_keys(zip_path)

        # 👉 Botón real: id="import_zip_btn"
        import_btn = driver.find_element(By.ID, "import_zip_btn")
        import_btn.click()

        # Esperar a que aparezcan los archivos importados
        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#zip-file-list li")))

        # Rellenar metadatos
        title_field = driver.find_element(By.NAME, "title")
        title_field.send_keys("Dataset ZIP Test")

        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.send_keys("Dataset creado desde ZIP por Selenium")

        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.send_keys("zip,selenium")

        # Añadir autor extra
        add_author_button = driver.find_element(By.ID, "add_author")
        add_author_button.click()
        wait_for_page_to_load(driver)

        name_field = driver.find_element(By.NAME, "authors-1-name")
        name_field.send_keys("ZIP Selenium")

        affiliation_field = driver.find_element(By.NAME, "authors-1-affiliation")
        affiliation_field.send_keys("Selenium Academy")

        # Confirmar subida
        confirm_checkbox = driver.find_element(By.ID, "confirm_upload")
        if not confirm_checkbox.is_selected():
            confirm_checkbox.click()

        upload_btn = driver.find_element(By.ID, "upload_dataset_btn")
        upload_btn.click()

        wait_for_page_to_load(driver)
        time.sleep(3)

        assert driver.current_url == f"{host}/dataset/list", f"URL inesperada tras subir dataset: {driver.current_url}"

        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, f"Esperaba {initial_datasets + 1}, pero hay {final_datasets}"

        print(" test_import_from_zip pasó correctamente")

    finally:
        close_driver(driver)
