import os
import shutil

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager


def initialize_driver():
    options = webdriver.FirefoxOptions()

    if os.environ.get('SELENIUM_HEADLESS', 'true').lower() != 'false':
        options.add_argument('--headless')

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    snap_tmp = os.path.expanduser("~/snap/firefox/common/tmp")
    os.makedirs(snap_tmp, exist_ok=True)
    os.environ["TMPDIR"] = snap_tmp

    # Try to use system geckodriver first, fallback to webdriver-manager
    system_geckodriver = shutil.which('geckodriver')
    if system_geckodriver:
        service = Service(system_geckodriver)
    else:
        service = Service(GeckoDriverManager().install())

    driver = webdriver.Firefox(service=service, options=options)
    return driver


def close_driver(driver):
    driver.quit()
