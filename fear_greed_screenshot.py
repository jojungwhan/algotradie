import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service

def extract_fear_greed_historical(html):
    soup = BeautifulSoup(html, "html.parser")
    historical = {}
    for item in soup.select('.market-fng-gauge__historical-item'):
        label = item.select_one('.market-fng-gauge__historical-item-label')
        value = item.select_one('.market-fng-gauge__historical-item-index-value')
        if label and value:
            historical[label.text.strip()] = value.text.strip()
    return historical

def try_accept_consent(driver):
    try:
        consent_selectors = [
            'button[aria-label="Accept"]',
            'button#onetrust-accept-btn-handler',
            'button[title="Accept All"]',
            'button[mode="primary"]',
            'button[mode="primary"] span',
        ]
        for selector in consent_selectors:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)
                    break
            except Exception:
                continue
    except Exception:
        pass

def capture_fear_greed_graph(screenshot_path="fear_greed_full.png", crop_box=None, wait_time=10, debug_html_path="fear_greed_debug.html"):
    """
    Captures a screenshot of the CNN Fear & Greed Index page and saves it locally.
    Optionally crops the image to the specified crop_box (left, upper, right, lower).
    Returns the path to the saved image and a dict of historical values. If extraction fails, saves HTML for debugging.
    """
    url = "https://edition.cnn.com/markets/fear-and-greed"
    options = Options()
    # To run in headless mode, uncomment the next line:
    # options.add_argument("--headless")
    options.add_argument("--window-size=1200,900")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    print("If a consent popup appears, please click 'Accept' in the browser window.")
    time.sleep(2)  # Let the page start loading
    try_accept_consent(driver)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".market-fng-gauge__historical"))
        )
    except Exception:
        pass
    time.sleep(wait_time)  # Increased wait for JS and manual consent

    html = driver.page_source
    historical = extract_fear_greed_historical(html)

    if not historical and debug_html_path:
        with open(debug_html_path, "w", encoding="utf-8") as f:
            f.write(html)

    driver.save_screenshot(screenshot_path)
    driver.quit()

    if crop_box:
        img = Image.open(screenshot_path)
        cropped_img = img.crop(crop_box)
        cropped_path = screenshot_path.replace(".png", "_cropped.png")
        cropped_img.save(cropped_path)
        return cropped_path, historical if historical else {"debug_html_path": debug_html_path}
    return screenshot_path, historical if historical else {"debug_html_path": debug_html_path}

if __name__ == "__main__":
    path, historical = capture_fear_greed_graph()
    print(f"Screenshot saved to: {path}")
    print(f"Historical values: {historical}")

    # Update the selector below based on the actual page structure
    index_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "your_selector_here")))
    index_value = index_element.text
    print(f"Fear & Greed Index: {index_value}") 