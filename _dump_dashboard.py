from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    page = browser.new_page(viewport={"width": 1600, "height": 2200})
    page.goto('http://localhost:8506', wait_until='domcontentloaded', timeout=120000)
    page.wait_for_timeout(5000)
    print(page.locator('body').inner_text()[:4000])
    browser.close()
