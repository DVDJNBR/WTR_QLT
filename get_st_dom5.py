from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:8502")
        page.wait_for_selector("text=Jan")
        page.locator("button", has_text="Mode sombre").click()
        page.wait_for_timeout(1000)
        element = page.locator("text=Jan").locator("..").locator("..").locator("..").locator("..").locator("..").locator("..").locator("..")
        print("Fallback HTML:")
        print(element.evaluate("el => el.outerHTML"))
        browser.close()

if __name__ == "__main__":
    run()
