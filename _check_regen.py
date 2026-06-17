from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    page = browser.new_page(viewport={"width": 1600, "height": 2400})
    page.goto('http://localhost:8506', wait_until='domcontentloaded', timeout=120000)
    page.wait_for_timeout(8000)
    page.get_by_role('button', name='Regenerate Recommendations').click()
    page.wait_for_timeout(15000)
    text = page.locator('body').inner_text()
    for needle in ['Recommendations refreshed from Ollama', 'Live Ollama successes', 'Cache fallbacks', 'Quantity:', 'Timing:', 'Ref:', 'N/A']:
        print(needle + '::' + ('yes' if needle in text else 'no'))
    browser.close()
