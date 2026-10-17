
import asyncio
from getpass import getpass
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # STEP 1: LinkedIn login
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")

        input(
            "Log in to LinkedIn manually, "
            "then press Enter here..."
        )

        # Save LinkedIn authentication session
        await context.storage_state(path="session.json")
        print("LinkedIn session saved.")

        # STEP 2: Gemini API key setup
        gemini_page = await context.new_page()
        await gemini_page.goto(
            "https://aistudio.google.com/app/apikey"
        )

        print("\nGoogle AI Studio opened.")
        print("1. Log into your Google account.")
        print("2. Create or select a Gemini API key.")
        print("3. Copy the API key.")

        # Explicitly request the user's API key
        gemini_key = getpass(
            "\nPaste your Gemini API key: "
        ).strip()

        if not gemini_key:
            raise ValueError("Gemini API key is required.")

        # Save separately from browser authentication
        Path(".env").write_text(
            f"GEMINI_API_KEY={gemini_key}\n",
            encoding="utf-8"
        )

        print("Gemini API key saved locally.")

        await browser.close()


asyncio.run(main())
