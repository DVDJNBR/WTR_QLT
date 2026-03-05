import subprocess
import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:8502")
        page.wait_for_selector("text=Janvier", timeout=10000)
        page.screenshot(path="final_screenshot2.png")
        browser.close()

if __name__ == "__main__":
    run()
