from playwright.async_api import async_playwright
from difflib import SequenceMatcher
from spellchecker import SpellChecker
import re
import asyncio


class CookieBannerText:
    def __init__(self):
        self.common_selectors = [
            'div.sticky',
            'div.hp__sc-yx4ahb-7',
            'p.hp__sc-hk8z4-0',
            'button.hp__sc-9mw778-1',
            'div.cmp-container',
            'div.ccm-modal-inner',
            'div.ccm-modal--header',
            'div.ccm-modal--body',
            'div.ccm-widget--buttons',
            'button.ccm--decline-cookies',
            'button.ccm--save-settings',
            'button[data-ccm-modal="ccm-control-panel"]',
            'div.ccm-powered-by',
            'div.ccm-link-container',
            'div.ccm-modal',
            'div[class*="ccm-settings-summoner"]',
            'div[class*="ccm-control-panel"]',
            'div[class*="ccm-modal--footer"]',
            'button.ccm--button-primary',
            'div[data-testid="uc-default-wall"]',
            'div[role="dialog"]',
            'div.cc-banner',
            'section.consentDrawer',
            'div[class*="cookie"]',
            'div[class*="consent"]',
            'div[id*="banner"]',
            'div[class*="cookie-banner"]',
            'div[class*="cookie-notice"]',
            '[role="dialog"]',
            '[aria-label*="cookie"]',
            '[data-cookie-banner]',
            'div[style*="bottom"]',
            'div[style*="fixed"]',
            'div[data-borlabs-cookie-consent-required]',
            'div#BorlabsCookieBox',
            'div#BorlabsCookieWidget',
            'div.elementText',
            'h3:has-text("Datenschutzhinweis")',
        ]
        self.spell_checker = SpellChecker(language='de')
    @staticmethod
    def clean_string(text):
        """Clean and normalize a string for comparison."""
        text = text.lower()  # Convert to lowercase
        text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
        text = text.strip()  # Remove leading and trailing spaces
        return text

    async def extract_cookie_banner_text(self, url):
        """Extract the cookie banner text from the website using Playwright."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    await page.goto(url, timeout=60000)

                    for selector in self.common_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                full_text = await element.inner_text()

                                # Define the start and end phrases
                                start_phrase = "Auf unserer Webseite verwenden wir Cookies"
                                end_phrase = "Weitere Informationen enthalten unsere Datenschutzinformationen."

                                # Use regex to extract the main text
                                pattern = re.escape(start_phrase) + r"(.*?)" + re.escape(end_phrase)
                                match = re.search(pattern, full_text, re.DOTALL)

                                if match:
                                    return match.group(0).strip()

                        except Exception:
                            continue

                    return "Cookie banner not found using any common selectors."
                finally:
                    await browser.close()
        except Exception as e:
            return f"Error extracting cookie banner text: {str(e)}"

    def compare_cookie_banner_text(self, website_text, template_text):
        """Compare website cookie banner text with the template."""
        # Clean both texts
        website_text_c = self.clean_string(website_text)
        template_text_c = self.clean_string(template_text)
        
        # Calculate similarity
        similarity = SequenceMatcher(None, template_text_c, website_text_c).ratio() * 100

        # Find spelling mistakes
        website_words = set(website_text.split())
        website_mistakes = self.spell_checker.unknown(website_words)

        # Prepare feedback
        feedback = f"""
        <strong>Template Text:</strong><br>
        <b>{template_text}</b><br><br>
        <strong>Website Text:</strong><br>
        <b>{website_text}</b><br><br>
        <strong>Similarity:</strong><br>
        <b>{similarity:.2f}%</b><br><br>
        """
        # Only check for mistakes if similarity is less than 100%
        if similarity < 100:
            website_words = set(website_text.split())
            website_mistakes = self.spell_checker.unknown(website_words)
            if website_mistakes:
                feedback += "Spelling mistakes in website text:<br>" + "<br>".join(f"- {word}" for word in website_mistakes)

        is_conformant = similarity == 100
        return is_conformant, similarity, feedback

    async def check_cookie_banner_text(self, url, template_text):
        """
        Extract cookie banner text from a website and compare it with the template text.
        :param url: URL of the website to check.
        :param template_text: Template text to compare against.
        :return: A tuple containing conformity, similarity, and feedback.
        """
        try:
            website_text = await self.extract_cookie_banner_text(url)
            if not website_text or "Error" in website_text:
                return False, 0, "Error or no cookie banner text found on the website."

            # Compare texts
            is_conformant, similarity, feedback = self.compare_cookie_banner_text(website_text, template_text)

            return is_conformant, similarity, feedback
        except Exception as e:
            return False, 0, f"Error during cookie banner text check: {str(e)}"

async def main():
    checker = CookieBannerText()
    url = "https://www.loreal-paris.de/"
    template_text = (
        "Auf unserer Webseite verwenden wir Cookies und ähnliche Technologien, um Informationen auf Ihrem Gerät "
        "(z.B. IP-Adresse, Nutzer-ID, Browser-Informationen) zu speichern und/oder abzurufen. Einige von ihnen sind "
        "für den Betrieb der Webseite unbedingt erforderlich. Andere verwenden wir nur mit Ihrer Einwilligung, z.B. "
        "um unser Angebot zu verbessern, ihre Nutzung zu analysieren, Inhalte auf Ihre Interessen zuzuschneiden oder "
        "Ihren Browser/Ihr Gerät zu identifizieren, um ein Profil Ihrer Interessen zu erstellen und Ihnen relevante "
        "Werbung auf anderen Onlineangeboten zu zeigen. Sie können nicht erforderliche Cookies akzeptieren (\"Alle "
        "akzeptieren\"), ablehnen (\"Ohne Einwilligung fortfahren\") oder die Einstellungen individuell anpassen und "
        "Ihre Auswahl speichern (\"Auswahl speichern\"). Zudem können Sie Ihre Einstellungen (unter dem Link "
        "\"Cookie-Einstellungen\") jederzeit aufrufen und nachträglich anpassen. Weitere Informationen enthalten "
        "unsere Datenschutzinformationen."
    )
    # Run the async `check_cookie_banner_text` function
    result, similarity, feedback = await checker.check_cookie_banner_text(url, template_text)
    print("Result:", result)
    print("Similarity:", similarity)
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())