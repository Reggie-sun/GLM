#!/usr/bin/env python3
"""
Analyze bigmodel.cn page using Chrome
"""
import asyncio
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from playwright.async_api import async_playwright


async def analyze_page():
    print("=" * 70)
    print("Analyzing bigmodel.cn with Chrome")
    print("=" * 70)

    async with async_playwright() as p:
        print("\nLaunching Chrome...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()

        try:
            print("\nNavigating to https://bigmodel.cn...")
            await page.goto('https://bigmodel.cn', wait_until='networkidle', timeout=60000)
            print("✓ Page loaded")

            print("\nWaiting 5 seconds for page to render...")
            await asyncio.sleep(5)

            # Save screenshot
            screenshot_dir = root / "data/screenshots"
            screenshot_dir.mkdir(exist_ok=True)

            screenshot_path = screenshot_dir / "chrome_analysis_home.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"✓ Screenshot saved to: {screenshot_path}")

            # Save HTML
            html_path = screenshot_dir / "chrome_analysis_home.html"
            content = await page.content()
            html_path.write_text(content, encoding="utf-8")
            print(f"✓ HTML saved to: {html_path}")

            # Find all buttons
            print("\nFinding buttons...")
            buttons = await page.query_selector_all('button, [role="button"], [class*="btn"], [class*="button"]')
            print(f"Found {len(buttons)} buttons:")

            for i, btn in enumerate(buttons[:20]):
                try:
                    text = await btn.inner_text()
                    class_attr = await btn.get_attribute('class') or ''
                    btn_id = await btn.get_attribute('id') or ''
                    print(f"  [{i}] text='{text.strip()}' class='{class_attr[:50]}' id='{btn_id}'")
                except:
                    pass

            # Find all links
            print("\nFinding links...")
            links = await page.query_selector_all('a[href]')
            print(f"Found {len(links)} links:")

            for i, link in enumerate(links[:20]):
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute('href') or ''
                    print(f"  [{i}] text='{text.strip()[:30]}' href='{href[:60]}'")
                except:
                    pass

            # Try to find GLM Coding page
            print("\nLooking for GLM Coding related links...")
            glm_links = []
            for link in links:
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute('href') or ''
                    if 'glm' in text.lower() or 'coding' in text.lower() or 'coding' in href.lower():
                        glm_links.append((text, href))
                except:
                    pass

            if glm_links:
                print(f"Found {len(glm_links)} potential GLM Coding links:")
                for text, href in glm_links:
                    print(f"  - {text.strip()}: {href}")

            print("\n" + "=" * 70)
            print("Analysis complete! Browser will stay open.")
            print("Press Ctrl+C to close.")
            print("=" * 70)

            # Keep browser open for manual inspection
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nClosing browser...")

        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_page())
