from playwright.sync_api import sync_playwright

url = "http://localhost:8506"
out = "dashboard_submission_live.png"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        args=["--disable-gpu", "--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1920, "height": 4000})
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(12000)
    page.screenshot(path=out, full_page=True)
    print("saved", out)
    browser.close()
