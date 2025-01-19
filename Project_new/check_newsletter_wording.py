
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
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, timeout=60000)

                # Liste für alle gefundenen Texte
                potential_texts = []

                # Suche Checkboxen und zugehörige Texte
                try:
                    await page.wait_for_selector(self.checkbox_selector, timeout=30000)
                    checkboxes = await page.query_selector_all(self.checkbox_selector)
                    print(f"Found {len(checkboxes)} checkboxes on the page.")

                    for checkbox in checkboxes:
                        # Suche nach Texten in benachbarten Elementen
                        associated_text = await checkbox.evaluate(
                            '''(node) => {
                                let sibling = node.nextElementSibling;
                                while (sibling) {
                                    if (sibling.textContent.trim()) return sibling.textContent.trim();
                                    sibling = sibling.nextElementSibling;
                                }
                                let label = document.querySelector(`label[for='${node.id}']`);
                                if (label && label.textContent.trim()) return label.textContent.trim();
                                return null;
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

                # Filtere Texte basierend auf Wörtern im Template
                filtered_texts = [
                    text for text in potential_texts
                    if any(word.lower() in text.lower() for word in template_text.split())
                ]

                # Führe Ähnlichkeitsprüfung durch
                best_match = None
                highest_similarity = 0
                for text in filtered_texts:
                    similarity = SequenceMatcher(None, template_text, text).ratio() * 100
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match = text

                browser.close()

                # Rückgabe des besten Matches und Ähnlichkeitswerts
                if best_match:
                    return best_match.strip(), highest_similarity
                else:
                    return "No relevant text found after similarity check.", 0
        except Exception as e:
            print(f"Error extracting text after checkbox: {e}")
            return f"Error extracting text after checkbox: {str(e)}", 0

    def show_diff(self, template_text, website_text):
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

                await page.goto(url)
                await page.wait_for_load_state('networkidle')

                # Suche nach Checkbox-Texten
                checkbox_text, similarity = await self.extract_text_after_checkbox(url, template_text)
                if "No relevant elements found" in checkbox_text:
                    # Prüfe alternative Newsletter-Seiten oder Elemente
                    links = await page.query_selector_all('a')
                    keywords = ["newsroom", "press", "enews", "newsletter", "subscribe", "signup"]

                    for link in links:
                        try:
                            href = await link.get_attribute('href')
                            if href:
                                full_url = urljoin(url, href)
                                if any(keyword in full_url.lower() for keyword in keywords):
                                    print(f"Found a relevant link: {full_url}")
                                    await page.goto(full_url)
                                    await page.wait_for_load_state('networkidle')

                                    checkbox_text, similarity = await self.extract_text_after_checkbox(full_url, template_text)
                                    if "No relevant elements found" in checkbox_text:
                                        continue

                                    differences = self.show_diff(template_text, checkbox_text)

                                    # Extrahiere deutsche Wörter und prüfe auf Rechtschreibfehler
                                    website_words = re.findall(r'\b[A-Za-zäöüßÄÖÜ]+\b', checkbox_text)
                                    german_words = [word for word in website_words if re.search(r'[äöüßÄÖÜ]', word) or word.lower() in self.spell_checker]
                                    website_mistakes = [word for word in german_words if word.lower() not in self.spell_checker]

                                    feedback = f"""
                                    <strong>Template Text:</strong><br>
                                    <b>{template_text}</b><br><br>
                                    <strong>Website Text:</strong><br>
                                    <b>{checkbox_text}</b><br><br>
                                    <strong>Similarity:</strong> <b>{similarity:.2f}%</b><br><br>
                                    """
                                    if differences:
                                        feedback += "<strong>Differences:</strong><br>" + "<br>".join(differences) + "<br><br>"
                                    else:
                                        feedback += "<strong>Differences:</strong> No differences found.<br><br>"

                                    if website_mistakes:
                                        feedback += "Spelling mistakes in website text:<br>" + "<br>".join(f"- {word}" for word in website_mistakes)
                                    else:
                                        feedback += "No spelling mistakes found in the website text.<br>"

                                    conformity = similarity == 100 and len(website_mistakes) == 0
                                    return conformity, similarity, feedback
                        except Exception as e:
                            print(f"Error processing link: {e}")
                            continue

                # Falls kein Text gefunden wurde
                if not checkbox_text or "No relevant elements found" in checkbox_text:
                    feedback = f"""
                    <strong>Template Text:</strong><br>
                    <b>{template_text}</b><br><br>
                    <strong>Website Text:</strong><br>
                    <b>No relevant text found on the page.</b><br><br>
                    <strong>Similarity:</strong> <b>0.00%</b><br><br>
                    """
                    conformity = False
                    return conformity, 0, feedback

                differences = self.show_diff(template_text, checkbox_text)

                # Extrahiere deutsche Wörter und prüfe auf Rechtschreibfehler
                website_words = re.findall(r'\b[A-Za-zäöüßÄÖÜ]+\b', checkbox_text)
                german_words = [word for word in website_words if re.search(r'[äöüßÄÖÜ]', word) or word.lower() in self.spell_checker]
                website_mistakes = [word for word in german_words if word.lower() not in self.spell_checker]

                feedback = f"""
                <strong>Template Text:</strong><br>
                <b>{template_text}</b><br><br>
                <strong>Website Text:</strong><br>
                <b>{checkbox_text}</b><br><br>
                <strong>Similarity:</strong> <b>{similarity:.2f}%</b><br><br>
                """
                if differences:
                    feedback += "<strong>Differences:</strong><br>" + "<br>".join(differences) + "<br><br>"
                else:
                    feedback += "<strong>Differences:</strong> No differences found.<br><br>"

                if website_mistakes:
                    feedback += "Spelling mistakes in website text:<br>" + "<br>".join(f"- {word}" for word in website_mistakes)
                else:
                    feedback += "No spelling mistakes found in the website text.<br>"

                conformity = similarity == 100 and len(website_mistakes) == 0
                return checkbox_text, conformity, similarity, feedback

        except Exception as e:
            print(f"Error during newsletter wording check: {e}")
            feedback = f"Error during newsletter wording check: {str(e)}"
            return False, 0, feedback


async def main():
    url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
    template_text = (
        "Ja, hiermit willige ich in die Verarbeitung meiner o.g. Kontaktdaten zu Marketingzwecken im Wege der direkten Kontaktaufnahme durch [Marke] sowie die weiteren Marken der L’Oréal Deutschland GmbH ein."
        "Um individuell auf meine Interessen zugeschnittene Informationen zu erhalten, willige ich außerdem ein, dass diese meine Reaktionen im Rahmen der Marketingaktionen sowie meine Interaktionen bei der Nutzung der Webservices der L’Oréal Deutschland GmbH "
        "und ihrer Marken erhebt und in einem Interessenprofil speichert, nutzt sowie meine E-Mail-Adresse oder meine Telefonnummer (soweit angegeben) in verschlüsselter Form an unsere Werbepartner übermittelt, "
        "sodass mir auch bei der Nutzung der Webservices unserer Werbepartner entsprechende Informationen angezeigt werden."
    )

    checker = NewsletterWording(url)

    result, similarity, feedback = await checker.check_newsletter_wording(url, template_text)

    print("\nResults:")
    print("Conformity:", result)
    print("Similarity:", f"{similarity:.2f}%")
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())
