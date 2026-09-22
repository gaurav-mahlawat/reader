import asyncio
import re

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.freelancer.in/jobs/web-development/"
        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(4)
        # sample card text
        cards = page.locator('a[href*="/projects/"]')
        for i in range(min(3, await cards.count())):
            link = cards.nth(i)
            href = await link.get_attribute("href")
            # parent card text
            parent = link.locator("xpath=ancestor::*[self::div or self::article][position()<=4][1]")
            text = ""
            if await parent.count():
                text = (await parent.first.inner_text())[:400]
            print("---", href)
            print(text.replace("\n", " | "))
        html = await page.content()
        for pat in [r'"bidCount":\s*(\d+)', r'"time_submitted":\s*(\d+)']:
            m = re.findall(pat, html[:200000])
            print(pat, m[:10])
        await browser.close()


asyncio.run(main())
