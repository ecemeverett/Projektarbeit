import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright

class AgeLimitation:
    def __init__(self, url):
        if not url:
            raise ValueError("The URL cannot be empty")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        self.url = url
        self.age_restriction_phrases = [
            # English Phrases
            "You must be 18 or older", "18+", "You must be over 18", "Age verification",
            "Enter your birthdate", "Please confirm your age", "Restricted to users 18 and older",
            "DOB", "Date of Birth", "Birth date",

            # German Phrases
            "Sie müssen 18 Jahre oder älter sein", "18+", "Sie müssen über 18 Jahre alt sein",
            "Altersverifikation", "Geben Sie Ihr Geburtsdatum ein", "Bitte bestätigen Sie Ihr Alter",
            "Beschränkt auf Benutzer ab 18 Jahren", "Geburtsdatum", "Geburtstag",
        ]

    async def check_age_limitation(self):
     async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Spezialbehandlung für "loreal.com"
            if "https://www.loreal-paris.de" in self.url:
                newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                print(f"Detected 'loreal-paris.de', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                # Altersbeschränkung direkt auf der Newsletter-Seite prüfen
                result, feedback = await self.perform_age_limitation_check(page)
                await browser.close()
                return result, feedback

            # Normale Verarbeitung für andere URLs
            await page.goto(self.url, timeout=60000)
            await page.wait_for_load_state('networkidle')

            # Hauptseite auf Altersbeschränkungen überprüfen
            result, feedback = await self.perform_age_limitation_check(page)
            if result:
                await browser.close()
                return result, feedback

            # Suche nach relevanten Links wie Newsroom oder Newsletter
            links = await page.query_selector_all('a')
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    full_url = urljoin(self.url, href)
                    if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter"]):
                        print(f"Found a relevant link: {full_url}")
                        await page.goto(full_url)
                        await page.wait_for_load_state('networkidle')

                        # Verlinkte Seite auf Altersbeschränkungen prüfen
                        result, feedback = await self.perform_age_limitation_check(page)
                        if result:
                            await browser.close()
                            return result, feedback

            # Standard-Feedback, wenn nichts gefunden wird
            feedback = "No Age Limitation or relevant Newsletter link found."
            result = False

        except Exception as e:
            result = False
            feedback = f"Error navigating to URL {self.url}: {str(e)}"

        await browser.close()
        return result, feedback


    async def perform_age_limitation_check(self, page):
        elements_to_check = await page.query_selector_all('a, button, input, div, span')

        for element in elements_to_check:
            try:
                # Extract text and relevant attributes
                text = await element.inner_text() or ''
                aria_label = await element.get_attribute('aria-label') or ''
                placeholder = await element.get_attribute('placeholder') or ''
                full_text = f"{text} {aria_label} {placeholder}".strip()

                # Check for matches in age restriction phrases
                for phrase in self.age_restriction_phrases:
                    if phrase.lower() in full_text.lower():
                        return True, f"Age Limitation found: '{phrase}'"
            except Exception:
                continue

        # If no Age Limitation is found
        return False, "No Age Limitation found"

    async def check_for_sign_up(self, page):
        # Look for all potential Sign-Up related elements
        elements_to_check = await page.query_selector_all('a, button')

        for element in elements_to_check:
            try:
                text = await element.inner_text() or ''
                aria_label = await element.get_attribute('aria-label') or ''
                placeholder = await element.get_attribute('placeholder') or ''
                full_text = f"{text} {aria_label} {placeholder}".strip()

                # Check if the text matches Sign-Up related phrases
                if any(phrase in full_text.lower() for phrase in ["sign up", "subscribe", "join"]):
                    href = await element.get_attribute('href')
                    if href:
                        sign_up_url = urljoin(page.url, href)
                        print(f"Found Sign-Up link: {sign_up_url}")
                        await page.goto(sign_up_url)
                        await page.wait_for_load_state('networkidle')
                        # Perform Age Limitation check on the redirected page
                        return await self.perform_age_limitation_check(page)
            except Exception:
                continue

        return False, "No Sign-Up button or link found"

async def main():
    url = "lorealparis.de"  # Replace with the URL you want to check
    checker = AgeLimitation(url)
    result, feedback = await checker.check_age_limitation()
    print("Result:", result)
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())


