import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from difflib import SequenceMatcher, ndiff


class MoreDetails:
    def __init__(self, url=None):
        self.url = url

    def calculate_similarity(self, expected_text, actual_text):
        """Berechnet die Ähnlichkeit zwischen zwei Texten."""
        similarity = SequenceMatcher(None, expected_text, actual_text).ratio() * 100
        return similarity

    def show_differences(self, expected_text, actual_text):
        """Zeigt die Unterschiede zwischen dem erwarteten und dem tatsächlichen Text."""
        diff = ndiff(expected_text.split(), actual_text.split())
        differences = [line for line in diff if line.startswith("- ") or line.startswith("+ ")]
        return differences

    async def check_newsletter_more_details(self, expected_text=None):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Sonderfall: Weiterleitung für loreal-paris.de
                if "loreal-paris.de" in self.url:
                    newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                    print(f"Sonderfall erkannt, Weiterleitung zu: {newsletter_url}")
                    self.url = newsletter_url

                # Gehe zur aktualisierten URL
                print(f"Navigating to: {self.url}")
                await page.goto(self.url, timeout=60000)
                await page.wait_for_load_state('networkidle')

                # Prüfen, ob die URL bereits eine Newsletter-Seite ist
                if any(keyword in self.url.lower() for keyword in ["newsletter", "signup", "email"]):
                    print("Direkte Newsletter-Seite erkannt. Überprüfung wird durchgeführt.")
                    return await self.perform_more_details_check(page, expected_text)

                # Suche nach relevanten Links wie Newsroom oder Newsletter
                links = await page.query_selector_all('a')
                for link in links:
                    try:
                        href = await link.get_attribute('href')
                        if href:
                            full_url = urljoin(self.url, href)
                            if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter"]):
                                print(f"Relevanter Link gefunden: {full_url}")
                                await page.goto(full_url)
                                await page.wait_for_load_state('networkidle')

                                # Suche auf der gefundenen Seite nach einem "Mehr Details"-Button
                                return await self.perform_cta_check(page, expected_text)
                    except Exception as e:
                        print(f"Fehler bei der Verarbeitung eines Links: {e}")
                        continue

                # Keine relevanten Links gefunden, überprüfe direkt die Hauptseite
                print("Keine spezifischen Links gefunden. Überprüfe die Hauptseite.")
                return await self.perform_cta_check(page, expected_text)

        except Exception as e:
            return False, 0, f"Fehler bei der Überprüfung der weiteren Details: {str(e)}"

    async def perform_more_details_check(self, page, expected_text):
        
        button_selector = 'button.further_button_up'
        content_selector = 'div.further_content'

        try:
            print(f"Suche nach Button mit Selektor: {button_selector}")
            button = await page.query_selector(button_selector)

            if button:
                print("Button gefunden, mache ihn sichtbar...")
                # Sichtbarkeit des Buttons erzwingen
                await page.evaluate("(button) => button.style.display = 'block'", button)
                print("Button sichtbar gemacht, klicke darauf...")
                await button.click()

                # Überprüfe, ob der Inhalt dynamisch angezeigt wird
                print(f"Warte darauf, dass {content_selector} sichtbar wird...")
                await page.wait_for_timeout(2000)  # Warte auf DOM-Updates

                # Fallback: Inhalt manuell sichtbar machen, falls erforderlich
                await page.evaluate("""(contentSelector) => {
                    const content = document.querySelector(contentSelector);
                    if (content) {
                        content.style.display = 'block';  // Sichtbarkeit des Inhalts erzwingen
                    }
                }""", content_selector)

                # Textinhalt des sichtbaren Bereichs abrufen
                content = await page.query_selector(content_selector)
                if content:
                    actual_text = await content.inner_text()
                    print(f"Gefundener dynamischer Text: {actual_text[:500]}...")

                    # Berechne die Ähnlichkeit und Unterschiede
                    similarity = self.calculate_similarity(expected_text, actual_text)
                    feedback = f"""
                    <strong>Erwarteter Text:</strong><br>{expected_text}<br><br>
                    <strong>Gefundener Text:</strong><br>{actual_text[:500]}...<br><br>
                    <strong>Similarity:</strong> {similarity:.2f}%<br>
                    """

                    return True, similarity, feedback

                else:
                    print("Inhalt wurde nicht sichtbar.")
                    return False, 0, "Inhalt wurde nicht sichtbar."

            else:
                print("Button nicht gefunden.")
                return False, 0, "Button nicht gefunden."

        except Exception as e:
            print(f"Fehler bei der Verarbeitung des More Detail Buttons: {e}")
            return False, 0, f"Fehler bei der Verarbeitung des More Detail Buttons: {e}"


# Beispiel für die Verwendung der Klasse
async def main():
    url = "https://www.loreal-paris.de"  # URL der Seite, die überprüft werden soll
    expected_text = "Die Einwilligung umfasst, dass Ihre oben angegebene E-Mailadresse sowie ggf. weitere von Ihnen angegebene Kontaktdaten von der L’Oréal Deutschland GmbH, Johannstraße 1, 40476 Düsseldorf (im Folgenden L'Oréal), gespeichert und genutzt werden, um Sie per E-Mail, Telefon, Telefax, SMS, Briefpost persönlich und relevant über interessante Leistungen, Produkte und Aktionen von [Marke] sowie aus dem Angebot von L'Oréal und deren weiteren Marken zu informieren. Um Ihnen individuell auf Ihre Interessen zugeschnittene Informationen zukommen zu lassen, speichert L’Oréal auch die Daten zu Ihren Reaktionen auf die empfangenen Informationen und die weiteren Daten aus Ihrer Nutzung der Webservices von [Marke] und L'Oréal (insbesondere Daten zu Einkäufen und Gesamtumsatz, angesehenen und gekauften Warengruppen/Produkten, Produkten im Warenkorb und eingelöste Gutscheine sowie zu Ihren sonstigen Interaktionen im Rahmen der Webservices und Ihren Reaktionen auf unsere Kontaktaufnahmen und Angebote, inklusive besonderer Vorteils-Aktionen) und führt diese Daten mit Ihren Kontaktdaten innerhalb eines Interessenprofils zusammen. Diese Daten werden ausschließlich genutzt, um Ihnen Ihren Interessen entsprechende Angebote machen zu können. Um Ihnen auf den Plattformen unserer Werbepartner interessengerechte Informationen / Werbung anzeigen zu können, nutzen wir bestimmte Tools unserer Werbepartner (z.B. Facebook Custom Audiences und Google Customer Match) und übermitteln die von Ihnen bei der Anmeldung angegebene E-Mail-Adresse oder Telefonnummer in verschlüsselter (pseudonymisierter) Form an diese. Hierdurch wird es möglich, Sie beim Besuch der Plattformen unserer Werbepartner als Nutzer der Webservices von L'Oréal zu erkennen, um Ihnen maßgeschneiderte Informationen / Werbung anzuzeigen."
    checker = MoreDetails(url)
    result, similarity, feedback = await checker.check_newsletter_more_details(expected_text)
    print("\nResults:")
    print("Conformity:", result)
    print("Similarity:", f"{similarity:.2f}%")
    print("Feedback:", feedback)


if __name__ == "__main__":
    asyncio.run(main())

