import asyncio
from playwright.async_api import async_playwright

class MoreDetails:
    def __init__(self, url=None):
        self.url = url

    async def check_newsletter_more_details(self):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Gehe zur angegebenen URL
                await page.goto(self.url)
                await page.wait_for_load_state('networkidle')

                # Suche nach möglichen Texten wie "Weitere Details", "Mehr erfahren", "Weitere Infos"
                more_details_texts = ["Weitere Details", "Mehr erfahren", "Weitere Infos", "Mehr anzeigen", "Show more", "Klicke für mehr Informationen", "More Details"]

                # Prüfe auf das Vorhandensein eines dieser Texte auf der Seite
                found_more_details = False
                for text in more_details_texts:
                    # Suche nach Links oder Buttons, die diesen Text enthalten
                    elements = await page.query_selector_all(f'button:text("{text}"), a:text("{text}")')

                    if elements:
                        found_more_details = True
                        break

                if found_more_details:
                    result = "Option für weitere Details gefunden."
                else:
                    result = "Keine Option für weitere Details gefunden."

                await browser.close()
                return result
        except Exception as e:
            return f"Fehler bei der Überprüfung der weiteren Details: {str(e)}"


# Beispiel für die Verwendung der Klasse
async def main():
    url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"  # Ersetze dies mit der URL der Seite, die du überprüfen möchtest
    checker = MoreDetails(url)
    result = await checker.check_newsletter_more_details()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
