import time

from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_propose_and_reject_dataset():
    """
    Test para proponer un dataset y rechazarlo.
    """

    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Login user1
        driver.get(f"{host}/login")
        time.sleep(2)

        driver.find_element(By.ID, "email").send_keys("user1@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()
        time.sleep(2)

        # Communities
        driver.get(f"{host}/community")
        time.sleep(2)

        driver.find_element(By.LINK_TEXT, "Machine Learning Models").click()
        time.sleep(2)

        driver.find_element(By.LINK_TEXT, "Propose Dataset").click()
        time.sleep(2)

        # Seleccionar dataset sin usar index
        dataset_select = Select(driver.find_element(By.ID, "datasetSelect"))
        options = dataset_select.options

        selected = False
        for opt in options:
            text = opt.text.strip().lower()
            if text and "select" not in text and "choose" not in text:
                opt.click()
                selected = True
                break

        if not selected:
            raise AssertionError("No valid dataset available to propose")

        driver.find_element(By.ID, "message").send_keys("esto es una prueba")
        time.sleep(1)

        driver.find_element(By.ID, "submit").click()
        time.sleep(2)

        # Logout user1
        driver.find_element(By.LINK_TEXT, "Doe, John").click()
        time.sleep(1)
        driver.find_element(By.CSS_SELECTOR, ".dropdown-item:nth-child(2)").click()
        time.sleep(2)

        # Login user2
        driver.get(f"{host}/login")
        time.sleep(2)

        driver.find_element(By.ID, "email").send_keys("user2@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()
        time.sleep(2)

        driver.get(f"{host}/community")
        time.sleep(2)

        driver.find_element(By.LINK_TEXT, "Machine Learning Models").click()
        time.sleep(2)

        driver.find_element(By.LINK_TEXT, "Manage").click()
        time.sleep(2)

        # Rechazar
        driver.find_element(By.XPATH, "//button[contains(@onclick, 'openRejectModal')]").click()
        time.sleep(1)

        driver.find_element(By.ID, "rejectReason").send_keys("rechazo de prueba")
        time.sleep(1)

        driver.find_element(By.ID, "confirmRejectBtn").click()
        time.sleep(2)

        # Validar alerta
        alert = driver.switch_to.alert
        assert "rejected successfully" in alert.text.lower()
        alert.accept()
        time.sleep(1)

        page_source = driver.page_source
        assert "No pending requests" in page_source, "Proposal was not rejected correctly"

        print("Test passed!")

    except NoSuchElementException as e:
        raise AssertionError(f"Test failed! Element not found: {e}")

    finally:
        close_driver(driver)


def test_add_curator_via_manage_interface():
    """
    Test para añadir un curador desde la interfaz de gestión.
    """

    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Login
        driver.get(f"{host}/login")
        time.sleep(2)

        driver.find_element(By.ID, "email").send_keys("user1@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()
        time.sleep(2)

        # Navegar a la comunidad y gestión
        driver.get(f"{host}/community/software-engineering-research")
        time.sleep(2)

        manage_button = driver.find_element(By.LINK_TEXT, "Manage")
        manage_button.click()
        time.sleep(2)

        # Cambiar al tab Curators
        curators_tab = driver.find_element(By.ID, "curators-tab")
        curators_tab.click()
        time.sleep(1)

        # Si user2 ya existe como curador, lo eliminamos primero para que el test no falle
        page_source = driver.page_source
        if "user2@example.com" in page_source:

            remove_button = driver.find_element(By.CSS_SELECTOR, ".btn-sm")
            remove_button.click()
            time.sleep(1)

            # Aceptar alerta
            try:
                driver.switch_to.alert.accept()
                time.sleep(2)
            except NoAlertPresentException:
                pass

        # Añadir curador
        add_curator_button = driver.find_element(By.XPATH, "//button[contains(@onclick, 'openAddCuratorModal')]")
        add_curator_button.click()
        time.sleep(1)

        # Buscar usuario
        search_input = driver.find_element(By.ID, "curatorSearch")
        search_input.send_keys("user2")
        time.sleep(2)

        # Click en primer resultado
        first_result = driver.find_element(By.CSS_SELECTOR, "#curatorResultsList .list-group-item")
        first_result.click()
        time.sleep(2)

        # Verificar que el curador fue añadido
        page_source = driver.page_source
        assert "user2@example.com" in page_source, "El nuevo curador no aparece en la lista"

        # Eliminamos el curador para limpiar el estado
        remove_button = driver.find_element(By.CSS_SELECTOR, ".btn-sm")
        remove_button.click()
        time.sleep(1)

        # Aceptar alerta
        driver.switch_to.alert.accept()
        time.sleep(2)

        # Verificar que fue eliminado
        page_source = driver.page_source
        assert "user2@example.com" not in page_source, "El curador no fue eliminado correctamente"

        print("Test passed!")

    except NoSuchElementException as e:
        raise AssertionError(f"Test fallido! Elemento no encontrado: {e}")

    finally:
        close_driver(driver)


# Call the test function
test_add_curator_via_manage_interface()
test_propose_and_reject_dataset()
