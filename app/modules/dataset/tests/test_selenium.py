import os
import time
import zipfile

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


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

        # Open the login page
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        # Find the username and password field and enter the values
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)
        time.sleep(4)
        wait_for_page_to_load(driver)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open the upload dataset
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Find basic info and UVL model and fill values
        title_field = driver.find_element(By.NAME, "title")
        title_field.send_keys("Title")
        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.send_keys("Description")
        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.send_keys("tag1,tag2")

        # Add two authors and fill
        add_author_button = driver.find_element(By.ID, "add_author")
        add_author_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)
        add_author_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field0 = driver.find_element(By.NAME, "authors-0-name")
        name_field0.send_keys("Author0")
        affiliation_field0 = driver.find_element(By.NAME, "authors-0-affiliation")
        affiliation_field0.send_keys("Club0")
        orcid_field0 = driver.find_element(By.NAME, "authors-0-orcid")
        orcid_field0.send_keys("0000-0000-0000-0000")

        name_field1 = driver.find_element(By.NAME, "authors-1-name")
        name_field1.send_keys("Author1")
        affiliation_field1 = driver.find_element(By.NAME, "authors-1-affiliation")
        affiliation_field1.send_keys("Club1")

        # Obtén las rutas absolutas de los archivos
        file1_path = os.path.abspath("app/modules/dataset/uvl_examples/file1.uvl")
        file2_path = os.path.abspath("app/modules/dataset/uvl_examples/file2.uvl")

        # Subir el primer archivo
        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(file1_path)
        wait_for_page_to_load(driver)

        # Subir el segundo archivo
        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(file2_path)
        wait_for_page_to_load(driver)

        # Add authors in UVL models
        show_button = driver.find_element(By.ID, "0_button")
        show_button.send_keys(Keys.RETURN)
        add_author_uvl_button = driver.find_element(By.ID, "0_form_authors_button")
        add_author_uvl_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field = driver.find_element(By.NAME, "feature_models-0-authors-2-name")
        name_field.send_keys("Author3")
        affiliation_field = driver.find_element(By.NAME, "feature_models-0-authors-2-affiliation")
        affiliation_field.send_keys("Club3")

        # Check I agree and send form
        check = driver.find_element(By.ID, "agreeCheckbox")
        check.send_keys(Keys.SPACE)
        wait_for_page_to_load(driver)

        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)
        time.sleep(2)  # Force wait time

        assert driver.current_url == f"{host}/dataset/list", "Test failed!"

        # Count final datasets
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Test failed!"

        print("Test passed!")

    finally:
        # Close the browser
        close_driver(driver)


def test_import_from_github():
    """
    TEST: Importar archivos desde repositorio GitHub

    Verifica que se puedan importar modelos UVL/GPX desde una URL de GitHub
    y que aparezcan correctamente en la lista de archivos.
    """
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        login_user(driver, host)

        # Contar datasets iniciales
        initial_datasets = count_datasets(driver, host)

        # Ir a la página de upload
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Buscar el botón/input para importar desde GitHub
        # NOTA: Ajusta los selectores según tu HTML real
        try:
            github_import_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "import_github_btn"))
            )
            github_import_btn.click()
            time.sleep(1)
        except Exception:
            print("No se encontró botón de GitHub, intentando input directo")

        # Ingresar URL del repositorio
        try:
            github_url_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "github_url_input"))
            )
            github_url_input.clear()
            # Usar un repo de prueba real o mock
            github_url_input.send_keys("https://github.com/diverso-lab/uvlhub-dataset-example")

            # Confirmar importación
            try:
                confirm_btn = driver.find_element(By.ID, "confirm_github_import")
                confirm_btn.click()
            except Exception:
                github_url_input.send_keys(Keys.RETURN)

            # Esperar a que se complete la importación
            time.sleep(8)  # Tiempo para clonar repo
            wait_for_page_to_load(driver)

            # Verificar que aparecieron archivos
            imported_files = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "uploaded-file-item"))
            )

            assert len(imported_files) > 0, "No se importaron archivos desde GitHub"
            print(f"Se importaron {len(imported_files)} archivos desde GitHub")

        except Exception as e:
            print(f"Error en importación de GitHub: {e}")
            driver.save_screenshot("/tmp/selenium_github_import_error.png")
            raise

        # Completar metadata y crear dataset
        title_field = driver.find_element(By.NAME, "title")
        title_field.send_keys("Dataset from GitHub")

        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.send_keys("Test import from GitHub repository")

        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.send_keys("github,import")

        # Agregar autor
        add_author_button = driver.find_element(By.ID, "add_author")
        add_author_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field = driver.find_element(By.NAME, "authors-0-name")
        name_field.send_keys("GitHub Author")

        affiliation_field = driver.find_element(By.NAME, "authors-0-affiliation")
        affiliation_field.send_keys("GitHub University")

        # Aceptar términos y enviar
        check = driver.find_element(By.ID, "agreeCheckbox")
        check.send_keys(Keys.SPACE)
        wait_for_page_to_load(driver)

        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        time.sleep(5)
        wait_for_page_to_load(driver)

        # Verificar que se creó el dataset
        assert driver.current_url == f"{host}/dataset/list", "No redirected to dataset list!"

        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Dataset not created!"

        print("Test de importación desde GitHub completado exitosamente")

    except Exception as e:
        print(f"Test falló: {e}")
        driver.save_screenshot("/tmp/selenium_github_final_error.png")
        raise

    finally:
        close_driver(driver)


def test_import_from_zip():
    """
    TEST: Importar archivos desde un ZIP

    Verifica que se puedan subir archivos ZIP y que se extraigan
    correctamente los modelos UVL/GPX.
    """
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        login_user(driver, host)

        initial_datasets = count_datasets(driver, host)

        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Buscar input para subir ZIP
        try:
            # Intentar clic en botón si existe
            try:
                import_zip_btn = driver.find_element(By.ID, "import_zip_btn")
                import_zip_btn.click()
                time.sleep(1)
            except Exception:
                pass

            zip_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "import_zip_input")))

        except Exception as e:
            print(f"No se encontró input de ZIP: {e}")
            driver.save_screenshot("/tmp/selenium_no_zip_input.png")
            raise

        # Crear ZIP de prueba si no existe
        zip_path = os.path.abspath("app/modules/dataset/test_data/sample_models.zip")

        if not os.path.exists(zip_path):
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)

            with zipfile.ZipFile(zip_path, "w") as zf:
                file1 = "app/modules/dataset/uvl_examples/file1.uvl"
                file2 = "app/modules/dataset/uvl_examples/file2.uvl"

                if os.path.exists(file1):
                    zf.write(file1, "file1.uvl")
                if os.path.exists(file2):
                    zf.write(file2, "file2.uvl")

        assert os.path.exists(zip_path), f"ZIP de prueba no encontrado: {zip_path}"

        # Subir ZIP
        zip_input.send_keys(zip_path)
        time.sleep(3)

        # Confirmar si hay botón
        try:
            confirm_btn = driver.find_element(By.ID, "confirm_zip_import")
            confirm_btn.click()
            time.sleep(2)
        except Exception:
            pass

        wait_for_page_to_load(driver)

        # Verificar archivos extraídos
        try:
            imported_files = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "uploaded-file-item"))
            )

            assert len(imported_files) > 0, "No se importaron archivos desde ZIP"
            print(f"Se importaron {len(imported_files)} archivos desde ZIP")

        except Exception as e:
            print(f"No se encontraron archivos: {e}")
            driver.save_screenshot("/tmp/selenium_no_zip_files.png")
            raise

        # Completar dataset
        title_field = driver.find_element(By.NAME, "title")
        title_field.send_keys("Dataset from ZIP")

        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.send_keys("Test import from ZIP file")

        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.send_keys("zip,import")

        add_author_button = driver.find_element(By.ID, "add_author")
        add_author_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field = driver.find_element(By.NAME, "authors-0-name")
        name_field.send_keys("ZIP Author")

        affiliation_field = driver.find_element(By.NAME, "authors-0-affiliation")
        affiliation_field.send_keys("ZIP University")

        check = driver.find_element(By.ID, "agreeCheckbox")
        check.send_keys(Keys.SPACE)
        wait_for_page_to_load(driver)

        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        time.sleep(5)
        wait_for_page_to_load(driver)

        assert driver.current_url == f"{host}/dataset/list"

        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1

        print("Test de importación desde ZIP completado exitosamente")

    except Exception as e:
        print(f"Test falló: {e}")
        driver.save_screenshot("/tmp/selenium_zip_final_error.png")
        raise

    finally:
        close_driver(driver)
