import asyncio

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.freelancer.in/login", wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(5)
        print("URL:", page.url)
        inputs = await page.locator("input").evaluate_all(
            """els => els.map(e => ({
                name: e.name, type: e.type, id: e.id,
                placeholder: e.placeholder,
                visible: e.offsetParent !== null
            }))"""
        )
        for i in inputs:
            if i.get("visible"):
                print("INPUT:", i)
        buttons = await page.locator("button").evaluate_all(
            """els => els.map(e => ({
                text: (e.innerText || '').trim().slice(0, 50),
                type: e.type, id: e.id, visible: e.offsetParent !== null
            }))"""
        )
        for b in buttons:
            if b.get("visible"):
                print("BTN:", b)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
