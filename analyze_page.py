#!/usr/bin/env python3
"""
Analyze bigmodel.cn page structure
"""
import asyncio
import sys
from pathlib import Path

root = Path(__file__).parent
sys.path.insert(0, str(root))

from bot.browser import BrowserManager


async def analyze_page():
    print("=" * 70)
    print("Analyzing bigmodel.cn")
    print("=" * 70)

    manager = BrowserManager()
    await manager.start()

    try:
        context = await manager.create_context()
        page = await manager.new_page(context)

        print("\n1. Accessing bigmodel.cn...")
        try:
            await page.goto("https://bigmodel.cn", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            print("   ✓ Page loaded")
        except Exception as e:
            print(f"   ✗ Page load issue: {e}")
            print("   Continuing anyway...")

        print("\n2. Getting page title...")
        try:
            title = await page.title()
            print(f"   Title: {title}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

        print("\n3. Getting current URL...")
        try:
            url = page.url
            print(f"   URL: {url}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

        print("\n4. Saving screenshot...")
        try:
            screenshot_dir = root / "data/screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            screenshot_path = screenshot_dir / "bigmodel_analysis.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"   ✓ Saved to: {screenshot_path}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

        print("\n5. Saving HTML source...")
        try:
            html_path = screenshot_dir / "bigmodel_source.html"
            content = await page.content()
            html_path.write_text(content, encoding="utf-8")
            print(f"   ✓ Saved to: {html_path}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

        print("\n6. Finding all buttons...")
        try:
            buttons = await page.query_selector_all("button")
            print(f"   Found {len(buttons)} buttons:")
            for i, btn in enumerate(buttons[:15]):
                try:
                    text = await btn.inner_text()
                    class_attr = await btn.get_attribute("class") or ""
                    btn_id = await btn.get_attribute("id") or ""
                    print(f"   [{i}] text='{text.strip()}' class='{class_attr}' id='{btn_id}'")
                except:
                    pass
        except Exception as e:
            print(f"   ✗ Failed: {e}")

        print("\n7. Finding all links...")
        try:
            links = await page.query_selector_all("a")
            print(f"   Found {len(links)} links:")
            for i, link in enumerate(links[:20]):
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute("href") or ""
                    class_attr = await link.get_attribute("class") or ""
                    print(f"   [{i}] text='{text.strip()}' href='{href}' class='{class_attr}'")
                except:
                    pass
        except Exception as e:
            print(f"   ✗ Failed: {e}")

        print("\n8. Getting page body text...")
        try:
            body = await page.query_selector("body")
            if body:
                body_text = await body.inner_text()
                print(f"   Body text (first 2000 chars):")
                print(body_text[:2000])
        except Exception as e:
            print(f"   ✗ Failed: {e}")

        print("\n" + "=" * 70)
        print("Analysis complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(analyze_page())
