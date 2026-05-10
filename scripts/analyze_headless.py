#!/usr/bin/env python3
"""
Analyze bigmodel.cn page in headless mode
"""
import asyncio
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from playwright.async_api import async_playwright


async def analyze_page():
    print("=" * 70)
    print("Analyzing bigmodel.cn (Headless)")
    print("=" * 70)

    async with async_playwright() as p:
        print("\nLaunching browser...")
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = await context.new_page()

        try:
            print("\nNavigating to https://bigmodel.cn...")
            response = await page.goto('https://bigmodel.cn', wait_until='commit', timeout=60000)
            print(f"✓ Navigation committed, status: {response.status if response else 'unknown'}")

            print("\nWaiting 8 seconds for page to render...")
            await asyncio.sleep(8)

            screenshot_dir = root / "data/screenshots"
            screenshot_dir.mkdir(exist_ok=True)

            html_path = screenshot_dir / "bigmodel_home_full.html"
            content = await page.content()
            html_path.write_text(content, encoding="utf-8")
            print(f"✓ HTML saved: {html_path}")

            try:
                screenshot_path = screenshot_dir / "bigmodel_home_full.png"
                await page.screenshot(path=str(screenshot_path), full_page=False, timeout=15000)
                print(f"✓ Screenshot saved: {screenshot_path}")
            except Exception as e:
                print(f"⚠ Screenshot skipped: {e}")

            print("\n" + "=" * 70)
            print("Analyzing page content...")
            print("=" * 70)

            print("\n--- Page Title ---")
            title = await page.title()
            print(title)

            print("\n--- All Buttons (first 30) ---")
            buttons = await page.query_selector_all('button, [role="button"], [class*="btn"], [class*="button"], [class*="Button"]')
            print(f"Found {len(buttons)} button-like elements")
            for i, btn in enumerate(buttons[:30]):
                try:
                    text = (await btn.inner_text()).strip()
                    class_attr = await btn.get_attribute('class') or ''
                    btn_id = await btn.get_attribute('id') or ''
                    print(f"  [{i}] text='{text[:40]}' class='{class_attr[:50]}' id='{btn_id}'")
                except Exception as e:
                    pass

            print("\n--- All Links (first 40) ---")
            links = await page.query_selector_all('a[href]')
            print(f"Found {len(links)} links")
            glm_links = []
            for i, link in enumerate(links[:40]):
                try:
                    text = (await link.inner_text()).strip()
                    href = await link.get_attribute('href') or ''
                    class_attr = await link.get_attribute('class') or ''
                    print(f"  [{i}] text='{text[:40]}' href='{href[:60]}'")
                    if 'glm' in text.lower() or 'coding' in text.lower() or 'coding' in href.lower():
                        glm_links.append((text, href))
                except Exception as e:
                    pass

            if glm_links:
                print(f"\n--- Found {len(glm_links)} GLM-related links ---")
                for text, href in glm_links:
                    print(f"  - {text}: {href}")

            print("\n--- Looking for keywords ---")
            body_text = await page.inner_text('body')
            keywords = ['购买', 'buy', '预约', 'subscribe', '价格', 'price', '立即', '库存', 'stock']
            for kw in keywords:
                if kw in body_text:
                    print(f"  ✓ Found keyword: '{kw}'")

            print("\n--- Looking for input elements ---")
            inputs = await page.query_selector_all('input, textarea')
            print(f"Found {len(inputs)} input elements")
            for i, inp in enumerate(inputs[:15]):
                try:
                    inp_type = await inp.get_attribute('type') or 'text'
                    inp_name = await inp.get_attribute('name') or ''
                    inp_id = await inp.get_attribute('id') or ''
                    inp_class = await inp.get_attribute('class') or ''
                    placeholder = await inp.get_attribute('placeholder') or ''
                    print(f"  [{i}] type='{inp_type}' name='{inp_name}' id='{inp_id}' placeholder='{placeholder}'")
                except Exception as e:
                    pass

            if glm_links:
                glm_href = glm_links[0][1]
                if glm_href:
                    if glm_href.startswith('/'):
                        glm_href = 'https://bigmodel.cn' + glm_href
                    if glm_href.startswith('http'):
                        print(f"\n\n{'=' * 70}")
                        print(f"Now navigating to GLM Coding page: {glm_href}")
                        print('=' * 70)

                        try:
                            await page.goto(glm_href, wait_until='commit', timeout=60000)
                            await asyncio.sleep(8)

                            glm_html = screenshot_dir / "bigmodel_glm_coding_full.html"
                            glm_content = await page.content()
                            glm_html.write_text(glm_content, encoding="utf-8")
                            print(f"✓ GLM page HTML saved: {glm_html}")

                            try:
                                glm_screenshot = screenshot_dir / "bigmodel_glm_coding_full.png"
                                await page.screenshot(path=str(glm_screenshot), full_page=False, timeout=15000)
                                print(f"✓ GLM page screenshot saved: {glm_screenshot}")
                            except Exception as e:
                                print(f"⚠ GLM screenshot skipped: {e}")

                            print("\n--- GLM Page Buttons ---")
                            glm_buttons = await page.query_selector_all('button, [role="button"], [class*="btn"], [class*="button"], [class*="Button"]')
                            print(f"Found {len(glm_buttons)} buttons on GLM page")
                            for i, btn in enumerate(glm_buttons[:40]):
                                try:
                                    text = (await btn.inner_text()).strip()
                                    class_attr = await btn.get_attribute('class') or ''
                                    btn_id = await btn.get_attribute('id') or ''
                                    print(f"  [{i}] text='{text[:60]}' class='{class_attr[:80]}' id='{btn_id}'")
                                except Exception as e:
                                    pass

                            print("\n--- GLM Page Body Text (first 3000 chars) ---")
                            glm_body_text = await page.inner_text('body')
                            print(glm_body_text[:3000])

                        except Exception as e:
                            print(f"Could not navigate to GLM page: {e}")
                            import traceback
                            traceback.print_exc()

            print("\n" + "=" * 70)
            print("Analysis complete!")
            print(f"Check screenshots in: {screenshot_dir}")
            print("=" * 70)

        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_page())
