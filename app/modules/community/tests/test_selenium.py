import time

from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


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

        email_field = driver.find_element(By.ID, "email")
        password_field = driver.find_element(By.ID, "password")
        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
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

    except NoSuchElementException as e:
        raise AssertionError(f"Test fallido! Elemento no encontrado: {e}")

    finally:
        close_driver(driver)


# Call the test function
test_add_curator_via_manage_interface()
