import subprocess
import time
from playwright.sync_api import sync_playwright

def run():
    # Run the actual app and take a screenshot
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:8502")
        # Wait for the main page to render something
        page.wait_for_selector("text=France")
        # Screenshot the pills
        page.screenshot(path="final_screenshot.png")
        browser.close()

if __name__ == "__main__":
    run()
