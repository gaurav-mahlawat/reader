import asyncio
import re

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.freelancer.in/projects/web-development/simple-website-12345678"
        # use real project from search
        await page.goto("https://www.freelancer.in/jobs/web-development/", wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(3)
        first = page.locator('a[href*="/projects/"]').first
        href = await first.get_attribute("href")
        project_url = "https://www.freelancer.in" + href if href.startswith("/") else href
        print("Project URL:", project_url)
        await page.goto(project_url, wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(3)
        text = await page.inner_text("body")
        print("--- snippets ---")
        for line in text.split("\n"):
            low = line.lower()
            if any(x in low for x in ["bid", "proposal", "posted", "ago", "day"]):
                if len(line.strip()) < 120:
                    print(line.strip())
        for pat in [
            r"(\d+)\s*bids?",
            r"(\d+)\s*proposals?",
            r"(\d+)\s*entries",
            r"Average bid[^0-9]*(\d+)",
            r"posted\s+(.{0,40})",
            r"(\d+)\s+days?\s+ago",
            r"(\d+)\s+hours?\s+ago",
            r"(\d+)\s+minutes?\s+ago",
        ]:
            m = re.findall(pat, text, re.I)
            print(pat, m[:5])
        html = await page.content()
        for pat in [r'"bid_count":\s*(\d+)', r'"bidCount":\s*(\d+)', r'bid_count["\']?\s*:\s*(\d+)']:
            m = re.findall(pat, html)
            print("json", pat, m[:3])
        await browser.close()


asyncio.run(main())
