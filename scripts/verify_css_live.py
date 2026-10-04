import asyncio
import urllib.request
import re
from playwright.async_api import async_playwright

def test_http():
    html = urllib.request.urlopen('http://localhost:3000/login').read().decode('utf-8')
    css_files = re.findall(r'href="(/_next/static/css/[^"]+\.css)"', html)
    print("Found CSS files in login HTML:", css_files)
    for c in css_files:
        resp = urllib.request.urlopen("http://localhost:3000" + c)
        print("CSS fetch:", c, "status:", resp.getcode(), "bytes:", len(resp.read()))

async def test_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True
        )
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://localhost:3000/login")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="verify_login.png")

        await page.goto("http://localhost:3000/brief")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="verify_brief.png")

        await page.goto("http://localhost:3000/dpr")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="verify_dpr.png")

        await page.goto("http://localhost:3000/petty-cash")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="verify_petty_cash.png")

        await page.goto("http://localhost:3000/attendance")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="verify_attendance.png")

        await browser.close()
        print("All 5 verification screenshots saved!")

if __name__ == "__main__":
    test_http()
    asyncio.run(test_browser())
