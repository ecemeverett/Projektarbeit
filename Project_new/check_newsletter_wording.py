import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from difflib import SequenceMatcher, ndiff
from spellchecker import SpellChecker
import re

class NewsletterWording:
    def __init__(self, url=None):
        self.url = url
        self.spell_checker = SpellChecker(language='de')

        # Benutzerdefinierte Wörter für die Rechtschreibprüfung
        self.spell_checker.word_frequency.load_words([
            "Drittunternehmen", "Einwilligungsbedürftige", "Datenschutzerklärung", "Rechtsgrundlagen",
            "Einwilligung", "Zweck", "ID", "Datenschutzinformationen", "zuzuschneiden", "Onlineangeboten",
            "Marketingbemühungen", "Auswertungsmöglichkeiten", "Schaltfläche", "Überwachungszwecken",
            "Rechtsbehelfsmöglichkeiten"
        ])

        self.checkbox_selector = 'input[type="checkbox"]'  # Standard-Selektor für Checkboxen

    async def extract_text_after_checkbox(self, url, template_text):
        """Extrahiert Texte, die mit Checkboxen verknüpft sind."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Gehe zur angegebenen URL
                print(f"Navigating to URL: {url}")
                await page.goto(url, timeout=60000)

                # Liste für alle gefundenen Texte
                potential_texts = []

                try:
                    # Suche alle Checkboxen auf der Seite
                    await page.wait_for_selector(self.checkbox_selector, timeout=30000)
                    checkboxes = await page.query_selector_all(self.checkbox_selector)
                    print(f"Found {len(checkboxes)} checkboxes on the page.")

                    for checkbox in checkboxes:
                        # Suche nach Texten in benachbarten Elementen
                        associated_text = await checkbox.evaluate(
                            '''(node) => {
                                let sibling = node.nextElementSibling;
                                let associatedTexts = [];
                                while (sibling) {
                                    if (sibling.textContent.trim()) associatedTexts.push(sibling.textContent.trim());
                                    sibling = sibling.nextElementSibling;
                                }
                                let label = document.querySelector(label[for='${node.id}']);
                                if (label && label.textContent.trim()) associatedTexts.push(label.textContent.trim());
                                return associatedTexts.join(" ");
                            }'''
                        )
                        if associated_text:
                            potential_texts.append(associated_text.strip())
                except Exception as e:
                    print(f"No checkboxes found or timeout occurred: {e}")

                # Fallback: Suche Texte im gesamten Seiteninhalt
                try:
                    page_text = await page.inner_text('body')
                    potential_texts.extend(page_text.split('\n'))
                except Exception as e:
                    print(f"Error during page fallback: {e}")

                # Debugging: Alle gefundenen Texte ausgeben
                print("Potential texts found:", potential_texts)

                # Filtere Texte basierend auf Wörtern im Template
                filtered_texts = [
                    text for text in potential_texts
                    if any(word.lower() in text.lower() for word in template_text.split())
                ]
                print("Filtered texts based on template:", filtered_texts)

                # Führe Ähnlichkeitsprüfung durch
                best_match = None
                highest_similarity = 0
                for text in filtered_texts:
                    similarity = SequenceMatcher(None, template_text, text).ratio() * 100
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match = text

                await browser.close()

                # Rückgabe des besten Matches und Ähnlichkeitswerts
                if best_match:
                    print(f"Best match: {best_match} with similarity: {highest_similarity:.2f}%")
                    return best_match.strip(), highest_similarity
                else:
                    print("No relevant text found after similarity check.")
                    return "No relevant text found after similarity check.", 0
        except Exception as e:
            print(f"Error extracting text after checkbox: {e}")
            return f"Error extracting text after checkbox: {str(e)}", 0


    def show_diff(self, template_text, website_text):
        """Zeigt Unterschiede zwischen dem Template-Text und dem Website-Text."""
        diff = ndiff(template_text.split(), website_text.split())
        differences = []
        for change in diff:
            if change.startswith('- '):
                differences.append(f"Missing in website: {change[2:]}")
            elif change.startswith('+ '):
                differences.append(f"Extra in website: {change[2:]}")
        return differences

    async def check_newsletter_wording(self, url, template_text):
     try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Spezialbehandlung für "loreal-paris.de"
            if "https://www.loreal-paris.de" in url:
                newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                print(f"Detected 'loreal-paris.de', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                # Direkt die Newsletter-Prüfung auf der Newsletter-Seite durchführen
                checkbox_text, similarity = await self.extract_text_after_checkbox(newsletter_url, template_text)
                if not checkbox_text or "No relevant text found" in checkbox_text:
                    feedback = "No relevant text found on the newsletter page."
                    await browser.close()
                    return False, 0, feedback

                # differences = self.show_diff(template_text, checkbox_text)  # Differences auskommentiert
                feedback = f"""
                <strong>Template Text:</strong> {template_text}<br>
                <strong>Extracted Text:</strong> {checkbox_text}<br>
                <strong>Similarity:</strong> {similarity:.2f}%<br>
                """
                await browser.close()
                return True, similarity, feedback

            # Standardprozess für andere URLs
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state('networkidle')
            except Exception as e:
                feedback = f"Error loading the URL: {url}, Details: {str(e)}"
                await browser.close()
                return False, 0, feedback

            # Prüfen, ob die URL bereits eine Newsletter-Seite ist
            if any(phrase.lower() in url.lower() for phrase in ["newsletter", "subscribe", "email", "signup"]):
                checkbox_text, similarity = await self.extract_text_after_checkbox(url, template_text)
                if not checkbox_text or "No relevant text found" in checkbox_text:
                    feedback = "No relevant text found on the newsletter page."
                    await browser.close()
                    return False, 0, feedback

                # differences = self.show_diff(template_text, checkbox_text)  # Differences auskommentiert
                feedback = f"""
                <strong>Template Text:</strong> {template_text}<br>
                <strong>Extracted Text:</strong> {checkbox_text}<br>
                <strong>Similarity:</strong> {similarity:.2f}%<br>
                """
                await browser.close()
                return True, similarity, feedback

            # Links auf der Seite durchsuchen, um zur Newsletter-Seite zu gelangen
            links = await page.query_selector_all('a')
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    if href:
                        full_url = urljoin(url, href)
                        if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter"]):
                            print(f"Found a relevant link: {full_url}")
                            await page.goto(full_url)
                            await page.wait_for_load_state('networkidle')

                            # Prüfung auf der verlinkten Seite
                            checkbox_text, similarity = await self.extract_text_after_checkbox(full_url, template_text)
                            if not checkbox_text or "No relevant text found" in checkbox_text:
                                continue

                            # differences = self.show_diff(template_text, checkbox_text)  # Differences auskommentiert
                            feedback = f"""
                            <strong>Template Text:</strong> {template_text}<br>
                            <strong>Extracted Text:</strong> {checkbox_text}<br>
                            <strong>Similarity:</strong> {similarity:.2f}%<br>
                            """
                            await browser.close()
                            return True, similarity, feedback
                except Exception:
                    continue

            # Keine relevanten Links gefunden
            feedback = "No newsletter-related links found on the page."
            await browser.close()
            return False, 0, feedback

     except Exception as e:
        print(f"Error during newsletter wording check: {e}")
        return False, 0, f"Error: {str(e)}"




async def main():
    url = "https://www.loreal-paris.de"
    template_text = (
        "Ja, hiermit willige ich in die Verarbeitung meiner o.g. Kontaktdaten zu Marketingzwecken im Wege der direkten Kontaktaufnahme durch [Marke] sowie die weiteren Marken der L’Oréal Deutschland GmbH ein."
        "Um individuell auf meine Interessen zugeschnittene Informationen zu erhalten, willige ich außerdem ein, dass diese meine Reaktionen im Rahmen der Marketingaktionen sowie meine Interaktionen bei der Nutzung der Webservices der L’Oréal Deutschland GmbH "
        "und ihrer Marken erhebt und in einem Interessenprofil speichert, nutzt sowie meine E-Mail-Adresse oder meine Telefonnummer (soweit angegeben) in verschlüsselter Form an unsere Werbepartner übermittelt, "
        "sodass mir auch bei der Nutzung der Webservices unserer Werbepartner entsprechende Informationen angezeigt werden."
    )

    checker = NewsletterWording(url)

    # Erwartet nur 3 Rückgabewerte
    conformity, similarity, feedback = await checker.check_newsletter_wording(url, template_text)

    # Ergebnisse ausgeben
    print("\nResults:")
    print("Conformity:", conformity)
    print("Similarity:", f"{similarity:.2f}%")
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())