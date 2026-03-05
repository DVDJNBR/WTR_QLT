from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:8505")
        page.wait_for_selector("text=Jan")
        page.screenshot(path="screenshot3.png")
        browser.close()

if __name__ == "__main__":
    run()
