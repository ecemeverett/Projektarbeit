import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from difflib import SequenceMatcher, ndiff


class MoreDetails:
    def __init__(self, url=None):
        self.url = url

    def calculate_similarity(self, expected_text, actual_text):
        """Calculates the similarity between two texts."""
        similarity = SequenceMatcher(None, expected_text, actual_text).ratio() * 100
        return similarity

    def show_differences(self, expected_text, actual_text):
        """Shows the differences between the expected and the actual tex"""
        diff = ndiff(expected_text.split(), actual_text.split())
        differences = [line for line in diff if line.startswith("- ") or line.startswith("+ ")]
        return differences

    async def check_newsletter_more_details(self, expected_text=None):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Special case handling for "loreal-paris.de"
                if "loreal-paris.de" in self.url:
                    newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                    print(f"Special case detected, redirecting to: {newsletter_url}")
                    self.url = newsletter_url


                print(f"Navigating to: {self.url}")
                await page.goto(self.url, timeout=60000)
                await page.wait_for_load_state('networkidle')

                # Special case handling for "hansgrohe.de"
                if "hansgrohe.de" in self.url:
                    newsletter_url = "https://www.hansgrohe.de/#interest-form"
                    print(f"Special case detected, redirecting to: {newsletter_url}")
                    self.url = newsletter_url


                print(f"Navigating to: {self.url}")
                await page.goto(self.url, timeout=60000)
                await page.wait_for_load_state('networkidle')


                 # Special case handling for "tesa.com"
                if "tesa.com" in self.url:
                    newsletter_url = "https://www.tesa.com/de-de/buero-und-zuhause/do-it-yourself-magazin/newsletter"
                    print(f"Special case detected, redirecting to: {newsletter_url}")
                    self.url = newsletter_url


                print(f"Navigating to: {self.url}")
                await page.goto(self.url, timeout=60000)
                await page.wait_for_load_state('networkidle')
                
                # Special handling for krombacher
                if "https://www.krombacher.de" in self.url:
                    newsletter_url = "https://www.krombacher.de/die-brauerei/newsletter-anmeldung"
                    print(f"Detected 'krombacher.de', redirecting to newsletter URL: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle')

                
                    conformity, similarity, feedback = await self.perform_more_details_check(page, expected_text)
                    await browser.close()
                    return conformity, similarity, feedback

                # Check whether the URL is already a newsletter page
                if any(keyword in self.url.lower() for keyword in ["newsletter", "signup", "email"]):
                    print("Direct newsletter page recognized. A check is being carried out.")
                    return await self.perform_more_details_check(page, expected_text)

                # Search for relevant links such as newsroom or newsletter
                links = await page.query_selector_all('a')
                for link in links:
                    try:
                        href = await link.get_attribute('href')
                        if href:
                            full_url = urljoin(self.url, href)
                            # Ignore imprint, data protection and general terms and conditions links
                            ignore_keywords = ["impressum", "datenschutz", "agb", "privacy", "legal"]
                            if any(ignored in full_url.lower() for ignored in ignore_keywords):
                              print(f" Ignoring irrelevant link: {full_url}")
                              continue  
                        
                            if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter"]):
                                print(f"Relevant link found: {full_url}")
                                await page.goto(full_url)
                                await page.wait_for_load_state('networkidle')

                                # Search for a “More details” button on the page 
                                return await self.perform_more_details_check(page, expected_text)
                    except Exception as e:
                        print(f"Error while processing a link: {e}")
                        continue

                # No relevant links found, check the main page directly
                print(" No relevant links found, checking the main page directly.")
                return await self.perform_more_details_check(page, expected_text)

        except Exception as e:
            return False, 0, f"Error while checking further details: {str(e)}"

    async def perform_more_details_check(self, page, expected_text):
        
        button_selector = 'button.further_button_up'
        content_selector = 'div.further_content'

        try:
            print(f"Searching for a button with selector: {button_selector}")
            button = await page.query_selector(button_selector)

            if button:
                print("Button found, it is being made visible. ...")
                # Force the visibility of the button.
                await page.evaluate("(button) => button.style.display = 'block'", button)
                print("Button made visible, click on it....")
                await button.click()

                # Check if the content is displayed dynamically.
                print(f"Waiting for {content_selector} being visible...")
                await page.wait_for_timeout(2000)  

                # Fallback: Manually make the content visible if necessary.
                await page.evaluate("""(contentSelector) => {
                    const content = document.querySelector(contentSelector);
                    if (content) {
                        content.style.display = 'block';  
                    }
                }""", content_selector)

                # Retrieve the text content of the visible area.
                content = await page.query_selector(content_selector)
                if content:
                    actual_text = await content.inner_text()
                    print(f"Found Text: {actual_text[:500]}...")

                    # Calculate the similarity and differences
                    similarity = self.calculate_similarity(expected_text, actual_text)
                    feedback = f"""
                    <strong>Erwarteter Text:</strong><br>{expected_text}<br><br>
                    <strong>Gefundener Text:</strong><br>{actual_text[:500]}...<br><br>
                    <strong>Similarity:</strong> {similarity:.2f}%<br>
                    """

                    return True, similarity, feedback

                else:
                    print("Content did not become visible..")
                    return False, 0, "Content did not become visible.."

            else:
                print("No More Details Button found.")
                return False, 0, "No More Details Button or No Newsletter found."

        except Exception as e:
            print(f"Error processing the More Detail button: {e}")
            return False, 0, f"Error processing the More Detail button.: {e}"



async def main():
    url = "https://www.de.weber"  
    expected_text = "Die Einwilligung umfasst, dass Ihre oben angegebene E-Mailadresse sowie ggf. weitere von Ihnen angegebene Kontaktdaten von der L’Oréal Deutschland GmbH, Johannstraße 1, 40476 Düsseldorf (im Folgenden L'Oréal), gespeichert und genutzt werden, um Sie per E-Mail, Telefon, Telefax, SMS, Briefpost persönlich und relevant über interessante Leistungen, Produkte und Aktionen von [Marke] sowie aus dem Angebot von L'Oréal und deren weiteren Marken zu informieren. Um Ihnen individuell auf Ihre Interessen zugeschnittene Informationen zukommen zu lassen, speichert L’Oréal auch die Daten zu Ihren Reaktionen auf die empfangenen Informationen und die weiteren Daten aus Ihrer Nutzung der Webservices von [Marke] und L'Oréal (insbesondere Daten zu Einkäufen und Gesamtumsatz, angesehenen und gekauften Warengruppen/Produkten, Produkten im Warenkorb und eingelöste Gutscheine sowie zu Ihren sonstigen Interaktionen im Rahmen der Webservices und Ihren Reaktionen auf unsere Kontaktaufnahmen und Angebote, inklusive besonderer Vorteils-Aktionen) und führt diese Daten mit Ihren Kontaktdaten innerhalb eines Interessenprofils zusammen. Diese Daten werden ausschließlich genutzt, um Ihnen Ihren Interessen entsprechende Angebote machen zu können. Um Ihnen auf den Plattformen unserer Werbepartner interessengerechte Informationen / Werbung anzeigen zu können, nutzen wir bestimmte Tools unserer Werbepartner (z.B. Facebook Custom Audiences und Google Customer Match) und übermitteln die von Ihnen bei der Anmeldung angegebene E-Mail-Adresse oder Telefonnummer in verschlüsselter (pseudonymisierter) Form an diese. Hierdurch wird es möglich, Sie beim Besuch der Plattformen unserer Werbepartner als Nutzer der Webservices von L'Oréal zu erkennen, um Ihnen maßgeschneiderte Informationen / Werbung anzuzeigen."
    checker = MoreDetails(url)
    result, similarity, feedback = await checker.check_newsletter_more_details(expected_text)
    print("\nResults:")
    print("Conformity:", result)
    print("Similarity:", f"{similarity:.2f}%")
    print("Feedback:", feedback)


if __name__ == "__main__":
    asyncio.run(main())

