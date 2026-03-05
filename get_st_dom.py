from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:8502")
        page.wait_for_selector("text=Jan") # wait for pills to render
        element = page.locator("[data-testid='stPills']")
        if element.count() == 0:
            print("No stPills found, trying to find by text")
            element = page.locator("text=Jan").locator("..").locator("..")
            print("Fallback HTML:")
            print(element.evaluate("el => el.outerHTML"))
        else:
            print("Found stPills:")
            print(element.evaluate("el => el.outerHTML"))
        browser.close()

if __name__ == "__main__":
    run()
