from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://careers.google.com/jobs/results/")
    page.wait_for_timeout(10000)  # wait for JS to load

    # Get all visible text
    visible_text = page.inner_text("body")
    print(visible_text)

    browser.close()
