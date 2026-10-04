import asyncio
import os
import shutil
import sys
import time
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = r"D:\prj\AI-Review-System\raw_browser_recording"

CURSOR_SCRIPT = """
(() => {
    if (document.getElementById('virtual-cursor')) return;
    const c = document.createElement('div');
    c.id = 'virtual-cursor';
    c.style.cssText = `
        position: fixed;
        width: 24px;
        height: 24px;
        background: rgba(245, 158, 11, 0.9);
        border: 2.5px solid #ffffff;
        border-radius: 50%;
        pointer-events: none;
        z-index: 2147483647;
        box-shadow: 0 0 14px rgba(0,0,0,0.55);
        transform: translate(-50%, -50%);
        transition: transform 0.1s ease-out, background 0.15s;
        top: 200px;
        left: 200px;
    `;
    document.body.appendChild(c);

    window.addEventListener('mousemove', (e) => {
        c.style.left = e.clientX + 'px';
        c.style.top = e.clientY + 'px';
    });
    window.addEventListener('mousedown', () => {
        c.style.transform = 'translate(-50%, -50%) scale(0.7)';
        c.style.background = 'rgba(239, 68, 68, 0.95)';
    });
    window.addEventListener('mouseup', () => {
        c.style.transform = 'translate(-50%, -50%) scale(1.0)';
        c.style.background = 'rgba(245, 158, 11, 0.9)';
    });
})();
"""

current_mouse = [200, 200]

async def smooth_move(page, target_x, target_y, steps=18, step_delay=0.015):
    start_x, start_y = current_mouse[0], current_mouse[1]
    for i in range(1, steps + 1):
        t = i / steps
        t_smooth = t * t * (3 - 2 * t)
        curr_x = start_x + (target_x - start_x) * t_smooth
        curr_y = start_y + (target_y - start_y) * t_smooth
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(step_delay)
    current_mouse[0] = target_x
    current_mouse[1] = target_y

async def move_and_click(page, selector, offset_x=0, offset_y=0, wait_after=0.6):
    elem = await page.wait_for_selector(selector, state="visible", timeout=12000)
    box = await elem.bounding_box()
    if box:
        target_x = box["x"] + box["width"] / 2 + offset_x
        target_y = box["y"] + box["height"] / 2 + offset_y
        await smooth_move(page, target_x, target_y)
        await asyncio.sleep(0.2)
        await page.mouse.down()
        await asyncio.sleep(0.12)
        await page.mouse.up()
        await asyncio.sleep(wait_after)

async def navigate_to_module(page, link_selector, target_heading, url_fallback):
    try:
        await move_and_click(page, link_selector, wait_after=1.2)
        await page.wait_for_selector(f"h1:has-text('{target_heading}')", timeout=5000)
    except Exception:
        await page.goto(url_fallback)
        await page.wait_for_selector(f"h1:has-text('{target_heading}')", timeout=10000)
    await page.evaluate(CURSOR_SCRIPT)

async def smooth_scroll_down(page, amount=400, steps=14, delay=0.03):
    step_amount = amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep(delay)
    await asyncio.sleep(0.5)

async def smooth_scroll_up(page, amount=400, steps=14, delay=0.03):
    step_amount = -amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep(delay)
    await asyncio.sleep(0.5)

async def type_text_smooth(page, text, delay=0.05):
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(delay)
    await asyncio.sleep(0.3)

async def run_walkthrough():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Launching Chromium browser with video recording at 1920x1080...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--start-maximized", "--no-sandbox"]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=OUTPUT_DIR,
            record_video_size={"width": 1920, "height": 1080}
        )

        await context.add_init_script(CURSOR_SCRIPT)
        page = await context.new_page()

        # ==========================================
        # SCENE 1: AUTHENTICATION & RAPID LOGIN (/login)
        # ==========================================
        print("--> Scene 1: Authentication & Zero-Friction Login")
        await page.goto("http://localhost:3000/login")
        await page.wait_for_load_state("networkidle")
        await page.evaluate(CURSOR_SCRIPT)
        await smooth_move(page, 960, 450)
        await asyncio.sleep(2.5)

        # Highlight Management Email tab
        await move_and_click(page, "button:has-text('Management (Email)')", wait_after=1.2)
        # Switch back to Field Worker PIN tab
        await move_and_click(page, "button:has-text('Field Worker (PIN)')", wait_after=1.0)

        # Re-ensure credentials in state
        await smooth_move(page, 960, 420)
        await page.locator("input[type='tel']").fill("9876543210")
        await asyncio.sleep(0.4)

        await smooth_move(page, 960, 490)
        await page.locator("input[type='password']").fill("1234")
        await asyncio.sleep(0.6)

        # Click Sign In button
        await move_and_click(page, "button[type='submit']", wait_after=1.5)

        # Wait for dashboard with fallback
        try:
            await page.wait_for_selector("h1:has-text('Executive Daily Brief')", timeout=6000)
        except Exception:
            await page.goto("http://localhost:3000/brief")
            await page.wait_for_selector("h1:has-text('Executive Daily Brief')", timeout=10000)
        await page.evaluate(CURSOR_SCRIPT)

        # ==========================================
        # SCENE 2: EXECUTIVE BRIEF SCORECARD (/brief)
        # ==========================================
        print("--> Scene 2: Executive Daily Brief Scorecard")
        await asyncio.sleep(2.0)

        # Move across 6 KPI scorecards
        await smooth_move(page, 450, 240)
        await asyncio.sleep(0.8)
        await smooth_move(page, 750, 240)
        await asyncio.sleep(0.8)
        await smooth_move(page, 1050, 240)
        await asyncio.sleep(0.8)
        await smooth_move(page, 1350, 240)
        await asyncio.sleep(0.8)

        # Scroll down to foundation progress & site alerts
        await smooth_scroll_down(page, amount=380)
        await smooth_move(page, 600, 520)
        await asyncio.sleep(1.5)

        # Scroll further to exceptions
        await smooth_scroll_down(page, amount=400)
        await smooth_move(page, 800, 600)
        await asyncio.sleep(1.8)

        # Scroll back up to action buttons
        await smooth_scroll_up(page, amount=780)
        await asyncio.sleep(0.8)

        # Click "Generate Brief Now"
        print("    Triggering 'Generate Brief Now'...")
        await move_and_click(page, "button:has-text('Generate Brief Now')", wait_after=2.5)

        # Click "Copy Payload"
        print("    Clicking 'Copy Payload'...")
        await move_and_click(page, "button:has-text('Copy Payload')", wait_after=1.8)

        # Scroll down to view formatted WhatsApp preview card
        await smooth_scroll_down(page, amount=520)
        await smooth_move(page, 1100, 600)
        await asyncio.sleep(3.0)

        # Scroll back to top
        await smooth_scroll_up(page, amount=520)
        await asyncio.sleep(1.0)

        # ==========================================
        # SCENE 3: DAILY PROGRESS REPORT (/dpr)
        # ==========================================
        print("--> Scene 3: Daily Progress Report (DPR)")
        await navigate_to_module(page, "aside a:has-text('DPR Entry')", "Daily Progress Report", "http://localhost:3000/dpr")
        await asyncio.sleep(1.8)

        # Switch shift to NIGHT
        try:
            shift_select = await page.wait_for_selector("select:has(option[value='NIGHT'])", timeout=5000)
            await shift_select.select_option("NIGHT")
            await asyncio.sleep(0.8)
        except Exception:
            pass

        # Scroll to Piling details
        await smooth_scroll_down(page, amount=320)
        await smooth_move(page, 600, 420)
        await asyncio.sleep(1.2)

        # Highlight 1000mm diameter guard & depths
        await smooth_move(page, 850, 420)
        await asyncio.sleep(1.0)
        await smooth_move(page, 1100, 420)
        await asyncio.sleep(1.0)

        # Scroll to equipment section
        await smooth_scroll_down(page, amount=450)
        await smooth_move(page, 700, 500)
        await asyncio.sleep(1.5)

        # Scroll to manpower & photo upload
        await smooth_scroll_down(page, amount=450)
        await smooth_move(page, 500, 600)
        await asyncio.sleep(1.2)
        await smooth_move(page, 1100, 600)
        await asyncio.sleep(1.8)

        # Submit DPR
        print("    Submitting DPR report...")
        try:
            await move_and_click(page, "button:has-text('Submit Daily Progress Report')", wait_after=2.5)
        except Exception:
            pass

        # Scroll to top to show confirmation
        await smooth_scroll_up(page, amount=1220)
        await asyncio.sleep(2.0)

        # ==========================================
        # SCENE 4: PETTY CASH & DEFICIT GUARDS (/petty-cash)
        # ==========================================
        print("--> Scene 4: Site Petty Cash & Deficit Guards")
        await navigate_to_module(page, "aside a:has-text('Petty Cash')", "Site Petty Cash", "http://localhost:3000/petty-cash")
        await asyncio.sleep(1.8)

        # Highlight Site Wallet & Supervisor Deficit cards
        await smooth_move(page, 500, 220)
        await asyncio.sleep(1.0)
        await smooth_move(page, 850, 220)
        await asyncio.sleep(1.0)
        await smooth_move(page, 1200, 220)
        await asyncio.sleep(1.2)

        # Open "Log New Expense" modal
        print("    Opening Log Expense modal...")
        await move_and_click(page, "button:has-text('Log New Expense')", wait_after=1.5)

        # Demonstrate Deficit Cap Guard: Click Out-of-Pocket checkbox
        print("    Demonstrating Rs.50,000 Deficit Cap Guard...")
        try:
            await move_and_click(page, "label:has-text('Paid Out-of-Pocket by Supervisor')", wait_after=0.8)
        except Exception:
            pass

        # Type excessive amount 65000 to trigger guard alert
        try:
            amt_input = await page.wait_for_selector("input[placeholder*='2500'], input[step='0.01']", timeout=5000)
            await amt_input.click()
            await type_text_smooth(page, "65000", delay=0.06)
            await asyncio.sleep(2.5)  # Viewers observe strict deficit cap alert banner

            # Adjust back to legitimate site expense
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await type_text_smooth(page, "2450", delay=0.06)
        except Exception:
            pass

        # Select category SPARES
        try:
            modal_select = await page.wait_for_selector("div.fixed select", timeout=5000)
            await modal_select.select_option("SPARES")
            await asyncio.sleep(0.6)
        except Exception:
            pass

        # Type description
        try:
            desc_input = await page.wait_for_selector("input[placeholder*='generator' i], input[placeholder*='Diesel' i]", timeout=5000)
            await desc_input.click()
            await type_text_smooth(page, "Emergency hydraulic seals for Bauer rig", delay=0.04)
        except Exception:
            pass

        # Save expense
        print("    Saving Expense...")
        try:
            await move_and_click(page, "button:has-text('Record Expense')", wait_after=2.2)
        except Exception:
            pass

        # Scroll down expense register
        await smooth_scroll_down(page, amount=380)
        await smooth_move(page, 960, 500)
        await asyncio.sleep(1.8)

        # Scroll back up and click "Export Tally XML"
        await smooth_scroll_up(page, amount=380)
        print("    Clicking 'Export Tally XML'...")
        try:
            await move_and_click(page, "button:has-text('Export Tally XML')", wait_after=2.2)
        except Exception:
            pass

        # ==========================================
        # SCENE 5: LABOUR & GEOFENCE ATTENDANCE (/attendance)
        # ==========================================
        print("--> Scene 5: Geofenced Attendance & Gang Muster")
        await navigate_to_module(page, "aside a:has-text('Attendance & Labour')", "Labour & Site Attendance", "http://localhost:3000/attendance")
        await asyncio.sleep(1.8)

        # Acquire GPS location
        print("    Triggering GPS location resolution...")
        try:
            await move_and_click(page, "button:has-text('Acquire GPS')", wait_after=2.5)
        except Exception:
            pass

        # Highlight geofence verification badge
        await smooth_move(page, 960, 320)
        await asyncio.sleep(2.0)

        # Scroll through worker roster
        await smooth_scroll_down(page, amount=400)
        await smooth_move(page, 800, 550)
        await asyncio.sleep(1.8)
        await smooth_scroll_up(page, amount=400)

        # Switch to Subcontractor Gang tab
        print("    Switching to Subcontractor Gang tab...")
        try:
            await move_and_click(page, "button:has-text('Subcontractor Gang')", wait_after=1.5)
        except Exception:
            pass

        # Scroll to view existing gang entries
        await smooth_scroll_down(page, amount=450)
        await smooth_move(page, 960, 600)
        await asyncio.sleep(2.5)
        await smooth_scroll_up(page, amount=450)

        # ==========================================
        # SCENE 6: OFFLINE ARCHITECTURE & HEADER
        # ==========================================
        print("--> Scene 6: Offline-Ready Architecture & Overview")
        # Move up to header and hover over Sync Status Badge
        await smooth_move(page, 1750, 28)
        await asyncio.sleep(2.2)

        # Click ODIPKS OS brand to return to brief
        await navigate_to_module(page, "aside a:has-text('Executive Brief')", "Executive Daily Brief", "http://localhost:3000/brief")
        await smooth_move(page, 960, 500)
        await asyncio.sleep(3.0)

        # Close page & context to finalize video recording
        print("Finalizing video recording...")
        await page.close()
        await context.close()
        await browser.close()
        print("Browser recording completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_walkthrough())
