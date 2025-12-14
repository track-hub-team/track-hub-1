import os
import time
import zipfile

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ✅ Importar modelos para limpiar la BD
from app import db
from app.modules.dataset.models import BaseDataset
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
        return len(driver.find_elements(By.XPATH, "//table//tbody//tr"))
    except Exception:
        return 0


def login_user(driver, host):
    driver.get(f"{host}/login")
    wait_for_page_to_load(driver)
    driver.find_element(By.NAME, "email").send_keys("user1@example.com")
    password = driver.find_element(By.NAME, "password")
    password.send_keys("1234")
    password.send_keys(Keys.RETURN)
    time.sleep(3)
    wait_for_page_to_load(driver)


def delete_dataset_by_title(title: str, user_email: str = "user1@example.com"):
    """
    ✅ Elimina un dataset por título y usuario para evitar duplicados en tests.
    """
    try:
        from app import create_app
        from app.modules.auth.models import User

        app = create_app()

        with app.app_context():
            user = User.query.filter_by(email=user_email).first()
            if not user:
                print(f"⚠️ Usuario {user_email} no encontrado")
                return False

            dataset = (
                BaseDataset.query.join(BaseDataset.ds_meta_data)
                .filter(BaseDataset.user_id == user.id, BaseDataset.ds_meta_data.has(title=title))
                .first()
            )

            if not dataset:
                print(f"ℹ️ No existe dataset '{title}'")
                return False

            print(f"🗑️ Eliminando dataset '{title}' (ID {dataset.id})")

            # Eliminar archivos físicos
            working_dir = os.getenv("WORKING_DIR", "")
            dataset_dir = os.path.join(working_dir, "uploads", f"user_{user.id}", f"dataset_{dataset.id}")
            if os.path.exists(dataset_dir):
                import shutil

                shutil.rmtree(dataset_dir, ignore_errors=True)

            db.session.delete(dataset)
            db.session.commit()
            print("✅ Dataset eliminado correctamente")
            return True

    except Exception as e:
        print(f"❌ Error eliminando dataset: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


# ----------------------------------------------------------------------
# TESTS
# ----------------------------------------------------------------------


def test_upload_dataset():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        delete_dataset_by_title("Title desde Selenium")

        login_user(driver, host)
        initial_datasets = count_datasets(driver, host)

        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Rellenar formulario
        driver.find_element(By.NAME, "title").clear()
        driver.find_element(By.NAME, "title").send_keys("Title desde Selenium")

        driver.find_element(By.NAME, "desc").clear()
        driver.find_element(By.NAME, "desc").send_keys("Description desde Selenium")

        driver.find_element(By.NAME, "tags").clear()
        driver.find_element(By.NAME, "tags").send_keys("tag1,tag2")

        # Subir archivos UVL con Dropzone
        file_paths = [
            os.path.abspath(os.path.join(BASE_DIR, "..", "uvl_examples", "file1.uvl")),
            os.path.abspath(os.path.join(BASE_DIR, "..", "uvl_examples", "file2.uvl")),
        ]

        for path in file_paths:
            assert os.path.exists(path), f"No se encuentra {os.path.basename(path)} en {path}"
            dropzone_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.dz-hidden-input"))
            )
            dropzone_input.send_keys(path)
            time.sleep(1)  # Dropzone reemplaza el input → esperar un momento

        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.ID, "upload_dataset")))

        # Checkbox confirmación
        confirm_checkbox = driver.find_element(By.ID, "confirm_upload")
        if not confirm_checkbox.is_selected():
            confirm_checkbox.click()

        driver.find_element(By.ID, "upload_dataset_btn").click()
        WebDriverWait(driver, 20).until(EC.url_contains("/dataset/list"))

        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1

        print("✅ test_upload_dataset pasó correctamente")
    finally:
        close_driver(driver)


def test_import_from_github():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()
        delete_dataset_by_title("Dataset desde GitHub")

        login_user(driver, host)
        initial = count_datasets(driver, host)

        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Import GitHub
        driver.find_element(By.ID, "github_url").send_keys("https://github.com/pcm290/testgithubrepositorytrackhub")
        driver.find_element(By.ID, "import_github_btn").click()

        # Esperar a que los archivos se carguen
        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#github-file-list li")))

        # Rellenar formulario
        driver.find_element(By.NAME, "title").send_keys("Dataset desde GitHub")
        driver.find_element(By.NAME, "desc").send_keys("Importado desde GitHub")
        driver.find_element(By.NAME, "tags").send_keys("github")

        driver.find_element(By.ID, "confirm_upload").click()
        driver.find_element(By.ID, "upload_dataset_btn").click()

        WebDriverWait(driver, 20).until(EC.url_contains("/dataset/list"))

        assert count_datasets(driver, host) == initial + 1
        print("✅ test_import_from_github OK")
    finally:
        close_driver(driver)


def test_import_from_zip():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()
        delete_dataset_by_title("Dataset ZIP Test")

        login_user(driver, host)
        initial = count_datasets(driver, host)

        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        zip_dir = os.path.join(BASE_DIR, "..", "test_data")
        os.makedirs(zip_dir, exist_ok=True)
        zip_path = os.path.join(zip_dir, "sample.zip")

        file1 = os.path.join(BASE_DIR, "..", "uvl_examples", "file1.uvl")
        file2 = os.path.join(BASE_DIR, "..", "uvl_examples", "file2.uvl")

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(file1, "file1.uvl")
            zf.write(file2, "file2.uvl")

        driver.find_element(By.ID, "zip_file").send_keys(zip_path)
        driver.find_element(By.ID, "import_zip_btn").click()

        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#zip-file-list li")))

        driver.find_element(By.NAME, "title").send_keys("Dataset ZIP Test")
        driver.find_element(By.NAME, "desc").send_keys("ZIP import")
        driver.find_element(By.NAME, "tags").send_keys("zip")

        driver.find_element(By.ID, "confirm_upload").click()
        driver.find_element(By.ID, "upload_dataset_btn").click()

        WebDriverWait(driver, 20).until(EC.url_contains("/dataset/list"))

        assert count_datasets(driver, host) == initial + 1
        print("✅ test_import_from_zip OK")
    finally:
        close_driver(driver)
