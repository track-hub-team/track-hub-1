import time

from selenium.common.exceptions import NoSuchElementException
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

    except NoSuchElementException as e:
        raise AssertionError(f"Test failed! Element not found: {e}")

    finally:
        close_driver(driver)


# Call the test function
test_propose_and_reject_dataset()
