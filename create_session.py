import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")

        input("Log in manually in the browser, then press Enter here...")

        # Save cookies + localStorage to a session file
        await context.storage_state(path="session.json")
        await browser.close()

asyncio.run(main())
