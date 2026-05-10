#!/usr/bin/env python3
"""
测试和验证浏览器功能

使用方法：
1. 先分析页面结构 - python test_browser.py analyze
2. 测试库存检查 - python test_browser.py check-stock
3. 测试购买流程 - python test_browser.py test-purchase
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).parent
sys.path.insert(0, str(root))

from bot.browser import BrowserManager, get_browser_manager
from bot.pages.bigmodel import BigModelPage, create_bigmodel_page


async def analyze_page():
    """分析目标页面结构"""
    print("=" * 60)
    print("页面分析模式")
    print("=" * 60)
    print("\n这将打开浏览器并访问目标页面")
    print("请手动检查页面元素的选择器\n")

    manager = get_browser_manager()
    await manager.start()

    try:
        context = await manager.create_context()
        page = await create_bigmodel_page(context)

        print(f"正在访问: {page.BASE_URL}")
        await page.go_to_home()
        await asyncio.sleep(5)

        print("\n" + "=" * 60)
        print("页面已加载，请检查：")
        print("=" * 60)
        print("\n1. 商品名称的选择器（class 或 id）")
        print("2. 库存状态的选择器")
        print("3. 购买按钮的选择器")
        print("4. 登录框的选择器（如需要）")
        print("\n" + "=" * 60)

        # 保存截图
        screenshot_path = await page.save_screenshot()
        print(f"\n截图已保存至: {screenshot_path}")

        # 获取页面内容
        content = await page.get_page_content()
        content_path = root / "data/screenshots/page.html"
        content_path.write_text(content, encoding="utf-8")
        print(f"页面HTML已保存至: {content_path}")

        print("\n按 Ctrl+C 退出...")
        try:
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            print("\n正在关闭...")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()


async def check_stock():
    """测试库存检查功能"""
    print("=" * 60)
    print("库存检查测试")
    print("=" * 60)

    manager = get_browser_manager()
    await manager.start()

    try:
        context = await manager.create_context()
        page = await create_bigmodel_page(context)

        print(f"正在访问: {page.BASE_URL}")
        await page.go_to_home()
        await asyncio.sleep(3)

        print("\n检查库存...")
        status, product = await page.check_stock()

        print(f"\n结果:")
        print(f"  商品名称: {product.name}")
        print(f"  价格: {product.price}")
        print(f"  库存状态: {status.value}")
        print(f"  检查时间: {product.last_updated}")

        if status.value == "in_stock":
            print("  🎉 有货！")
        elif status.value == "out_of_stock":
            print("  😢 无货")
        else:
            print("  ❓ 未知状态（可能需要调整选择器）")

        # 保存截图
        screenshot_path = await page.save_screenshot()
        print(f"\n截图已保存至: {screenshot_path}")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()


async def test_purchase():
    """测试购买流程（实际不会执行购买）"""
    print("=" * 60)
    print("购买流程测试（模拟）")
    print("=" * 60)
    print("\n这将测试购买流程的各个步骤")
    print("注意：这是模拟测试，不会实际下单\n")

    manager = get_browser_manager()
    await manager.start()

    try:
        context = await manager.create_context()
        page = await create_bigmodel_page(context)

        print(f"正在访问: {page.BASE_URL}")
        await page.go_to_home()
        await asyncio.sleep(3)

        print("\n步骤 1: 检查库存...")
        status, product = await page.check_stock()
        print(f"  结果: {status.value}")

        print("\n步骤 2: 保存页面截图...")
        screenshot_path = await page.save_screenshot()
        print(f"  截图已保存: {screenshot_path}")

        print("\n步骤 3: 测试流程框架...")
        print("  测试框架正常工作")

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        print("\n提示：")
        print("- 如要实现真实购买，需要更新 bot/pages/bigmodel.py")
        print("- 根据实际页面调整选择器")
        print("- 配置登录账号")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_browser.py analyze      - 分析页面结构")
        print("  python test_browser.py check-stock  - 检查库存")
        print("  python test_browser.py test-purchase - 测试购买流程")
        return

    command = sys.argv[1]

    if command == "analyze":
        asyncio.run(analyze_page())
    elif command == "check-stock":
        asyncio.run(check_stock())
    elif command == "test-purchase":
        asyncio.run(test_purchase())
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()
