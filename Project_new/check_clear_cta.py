import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright

class ClearCTA:
    def __init__(self, url, newsletter_phrases=None):
        if not url:
            raise ValueError("The URL cannot be empty")

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        self.url = url
        self.newsletter_phrases = newsletter_phrases or [
            # English phrases
            "subscribe now", "join our newsletter", "sign up", "get updates",
            "newsletter signup", "subscribe", "subscribe to our newsletter", 
            "email alerts", "get emails", "sign up for updates",
            # German phrases
            "jetzt anmelden", "newsletter abonnieren", "anmelden", "erhalte updates",
            "newsletter-registrierung", "abonniere", "abonniere unseren newsletter", 
            "e-mail benachrichtigungen", "updates erhalten", "anmeldung", "registrieren",
        ]

    async def check_clear_cta(self):
        criteria_met = False
        feedback = "CTA not found or not recognizable as a clear call-to-action."

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Spezialbehandlung für "loreal.com"
                if "https://www.loreal-paris.de" in self.url:
                    newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                    print(f"Detected 'loreal-pars.de', redirecting to newsletter URL: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle')

                    # Direkt die CTA-Prüfung auf der Newsletter-Seite durchführen
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback
                
                #Spezialfall pg.com
                if "https://www.pg.com" in self.url:
                    newsletter_url = "https://us.pg.com/newsroom/email/"
                    print(f"Detected 'pg.com', redirecting to newsletter URL: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle')

                    # Direkt die CTA-Prüfung auf der Newsletter-Seite durchführen
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback

                # Normale Verarbeitung für andere URLs
                try:
                    await page.goto(self.url, timeout=60000)
                    await page.wait_for_load_state('networkidle')
                except Exception as e:
                    feedback = f"Error loading the URL: {self.url}, Details: {str(e)}"
                    await browser.close()
                    return False, feedback

                # Prüfen, ob die URL bereits eine Newsletter-Seite ist
                if any(phrase.lower() in self.url.lower() for phrase in ["newsletter", "subscribe", "email", "signup"]):
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback

                # Suche nach relevanten Links wie Newsroom oder Newsletter
                links = await page.query_selector_all('a')
                for link in links:
                    try:
                        href = await link.get_attribute('href')
                        if href:
                            full_url = urljoin(self.url, href)
                            if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter"]):
                                await page.goto(full_url)
                                await page.wait_for_load_state('networkidle')
                                criteria_met, feedback = await self.perform_cta_check(page)
                                await browser.close()
                                return criteria_met, feedback
                    except Exception:
                        continue

                # Wenn kein passender Link gefunden wurde, direkt die Homepage prüfen
                criteria_met, feedback = await self.perform_cta_check(page)

            except Exception as e:
                feedback = f"Error navigating to URL {self.url}: {str(e)}"

            await browser.close()
        return criteria_met, feedback

    async def perform_cta_check(self, page):
        # Suche nach allen potenziell relevanten Elementen auf der Seite
        elements_to_check = await page.query_selector_all('a, button, input, div, span')

        for element in elements_to_check:
            try:
                text = await element.inner_text() or ''
                placeholder = await element.get_attribute('placeholder') or ''
                aria_label = await element.get_attribute('aria-label') or ''
                full_text = f"{text} {placeholder} {aria_label}".strip()

                # Aufteilen des Texts und Suche nach passenden Newsletter-Phrasen
                words = full_text.split()
                for word in words:
                    if any(phrase.lower() == word.lower() for phrase in self.newsletter_phrases):
                        return True, f"Found CTA: '{word}'"
            except Exception:
                continue

        # Wenn kein CTA gefunden wurde
        return False, "No clear CTA found"

async def main():
    # Beispiel: Gebe eine Startseite oder direkten Newsletter-Link ein
    url = "https://pg.com"
    checker = ClearCTA(url)
    result, feedback = await checker.check_clear_cta()
    print("Result:", result)
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())
