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


def test_follow_unfollow_community():
    """
    Test para seguir y dejar de seguir una comunidad.
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

        # Navegar a la lista de comunidades
        driver.get(f"{host}/community")
        time.sleep(2)

        # Seleccionar una comunidad específica (Machine Learning Models)
        driver.find_element(By.LINK_TEXT, "Machine Learning Models").click()
        time.sleep(2)

        # Buscar el botón de follow/unfollow con diferentes estrategias
        follow_button = None

        # Estrategia 1: Buscar por diferentes IDs posibles
        possible_ids = ["followButton", "follow-btn", "followCommunityBtn"]
        for btn_id in possible_ids:
            try:
                follow_button = driver.find_element(By.ID, btn_id)
                break
            except NoSuchElementException:
                continue

        # Estrategia 2: Buscar por clase CSS
        if not follow_button:
            try:
                follow_button = driver.find_element(By.CSS_SELECTOR, ".btn-follow, .follow-btn, .btn-community-follow")
            except NoSuchElementException:
                pass

        # Estrategia 3: Buscar formulario de follow y su botón submit
        if not follow_button:
            try:
                follow_form = driver.find_element(By.XPATH, "//form[contains(@action, '/follow')]")
                follow_button = follow_form.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except NoSuchElementException:
                pass

        # Estrategia 4: Buscar cualquier botón que contenga "Follow" en el texto
        if not follow_button:
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    btn_text = btn.text.strip().lower()
                    if "follow" in btn_text:
                        follow_button = btn
                        break
            except NoSuchElementException:
                pass

        # Si aún no encontramos el botón, el test falla
        if not follow_button:
            page_source = driver.page_source
            raise AssertionError(
                f"No se pudo encontrar el botón de follow/unfollow. "
                f"Página actual: {driver.current_url}. "
                f"Busca 'follow' en el HTML: {'follow' in page_source.lower()}"
            )

        initial_button_text = follow_button.text.strip().lower()
        print(f"Estado inicial del botón: '{initial_button_text}'")

        # Si ya está siguiendo, primero dejar de seguir para tener un estado conocido
        if (
            "unfollow" in initial_button_text
            or "siguiendo" in initial_button_text
            or "following" in initial_button_text
        ):
            follow_button.click()
            time.sleep(2)
            # Volver a buscar el botón
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "follow" in btn.text.strip().lower():
                    follow_button = btn
                    break

        # Ahora seguir la comunidad
        follow_button.click()
        time.sleep(2)

        # Verificar que el estado cambió (buscar el botón nuevamente)
        buttons = driver.find_elements(By.TAG_NAME, "button")
        follow_button = None
        for btn in buttons:
            btn_text = btn.text.strip().lower()
            if "follow" in btn_text or "siguiendo" in btn_text:
                follow_button = btn
                break

        if not follow_button:
            raise AssertionError("No se encontró el botón después de seguir la comunidad")

        button_text_after_follow = follow_button.text.strip().lower()
        print(f"Estado después de seguir: '{button_text_after_follow}'")
        assert (
            "unfollow" in button_text_after_follow
            or "siguiendo" in button_text_after_follow
            or "following" in button_text_after_follow
        ), f"El botón debería mostrar 'Unfollow' o 'Following', pero muestra: '{button_text_after_follow}'"

        # Dejar de seguir la comunidad
        follow_button.click()
        time.sleep(2)

        # Verificar que el botón volvió a "Follow"
        buttons = driver.find_elements(By.TAG_NAME, "button")
        follow_button = None
        for btn in buttons:
            btn_text = btn.text.strip().lower()
            if "follow" in btn_text:
                follow_button = btn
                break

        if not follow_button:
            raise AssertionError("No se encontró el botón después de dejar de seguir")

        button_text_after_unfollow = follow_button.text.strip().lower()
        print(f"Estado después de dejar de seguir: '{button_text_after_unfollow}'")
        assert (
            "follow" in button_text_after_unfollow and "unfollow" not in button_text_after_unfollow
        ) or "seguir" in button_text_after_unfollow, (
            f"El botón debería mostrar 'Follow', pero muestra: '{button_text_after_unfollow}'"
        )

        print("Test follow/unfollow community passed!")

    except NoSuchElementException as e:
        raise AssertionError(f"Test failed! Element not found: {e}")
    except AssertionError as e:
        raise AssertionError(f"Test failed! Assertion error: {e}")

    finally:
        close_driver(driver)


# Call the test functions
test_add_curator_via_manage_interface()
test_propose_and_reject_dataset()
test_follow_unfollow_community()
