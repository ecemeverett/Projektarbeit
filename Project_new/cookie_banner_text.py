from playwright.async_api import async_playwright
from difflib import SequenceMatcher
from spellchecker import SpellChecker
import re
import asyncio
from langdetect import detect


class CookieBannerText:
    def __init__(self):
        # Initialize PySpellChecker with the German language
        self.spell_checker = SpellChecker(language='de')
        self.spell_checker_en = SpellChecker(language='en')
        self.spell_checker.word_frequency.load_words([
            "Drittunternehmen",
            "Einwilligungsbedürftige",
            "Datenschutzerklärung",
            "Rechtsgrundlagen",
            "Einwilligung",
            "Zweck", "z",  # Abbreviation for 'z.B.'
            "ID",  # As part of 'Nutzer-ID'
            "Datenschutzinformationen",
            "zuzuschneiden",
            "Onlineangeboten",
            "Marketingbemühungen",
            "Auswertungsmöglichkeiten",
            "Schaltfläche",
            "Überwachungszwecken",
            "Rechtsbehelfsmöglichkeiten",
            "Widerrufsmöglichkeit"
        ])
        
        self.spell_checker_en.word_frequency.load_words([
            
        ])
        self.usercentrics_banner_selector = "div[data-testid='uc-default-banner']"
        self.usercentrics_message_selector = "div[data-testid='uc-message-container']"
        self.common_selectors = [
            '.cookie-layer-advanced__content-text',  # Selector for the Griesson-DeBeukelaer cookie banner
            '#privacydialog\:desc', # Selector for Hassia Gruppe
            '#cmpboxcontent > div > div',  # Selector for Tesa
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div > div.hp__sc-s043ov-6.gqFIYM > div',  # Specific selector for Urlaubspiraten cookie banner text
            'div#popin_tc_privacy_text > div:first-of-type', # Specific selector for Danone
            'div#onetrust-policy-text',  # Specific selector for Onetrust policy text
            'div#CybotCookiebotDialogBodyContentText',  # Cybot specific selector
            'div.desktop-view > p',  # Selector for Verivox cookie banner paragraph
            '#consent-wall > div.layout-row.consentDescription > p',  # Specific selector for 1&1
            'div[id="uc-show-more"][data-testid="uc-message-container"]',  # Cookie banner text from https://biersdorfamsee.de/
            'body > div > div > section > div.content > p',  # Specific selector for bmw
            'div.hp__sc-yx4ahb-7',
            '#cookiescript_description', # redbag
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
            '//*[@id="onetrust-policy-text"]',
            '#usercentrics-root',
            'div[data-testid="uc-app-container"]',
            'button[data-testid="uc-privacy-button"]',
            'div[data-testid="uc-default-banner"]',
            '//*[@id="onetrust-policy-text"]/div'  # Specific XPath
            
        ]

    @staticmethod
    def clean_string(text):
        """Clean and normalize a string for comparison."""
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
     
    def detect_language(self, text):
        """Detect the language of the text."""
        try:
            return detect(text)
        except Exception:
            return "unknown"
        
    def get_spell_checker(self, language):
        """Return the appropriate spell checker based on the detected language."""
        if language == "de":
            return self.spell_checker_de
        elif language == "en":
            return self.spell_checker_en
        else:
            return None

    async def extract_cookie_banner_text(self, url):
        """Extract the cookie banner text from the website using Playwright."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    print(f"Visiting URL: {url}")
                    await page.goto(url, timeout=60000)
                    
                    # Attempt specific XPath extraction
                    try:
                        await page.wait_for_selector('//*[@id="onetrust-policy-text"]/div', timeout=10000)
                        print("Specific XPath matched for cookie banner text.")
                        element = await page.query_selector('//*[@id="onetrust-policy-text"]/div')
                        if element:
                            banner_text = await element.inner_text()
                            return banner_text.strip()
                    except Exception as e:
                        print(f"Failed to match specific XPath: {e}")
                    
                    # Target specific selector for text extraction
                    try:
                        await page.wait_for_selector("#cookieboxStartDescription", timeout=10000)
                        element = await page.query_selector("#cookieboxStartDescription")
                        if element:
                            # Extract plain text without nested links/buttons
                            banner_text = await element.inner_text()
                            return banner_text.strip()
                    except Exception as e:
                        print(f"Specific selector not found: {e}")
                    

                    # Attempt Usercentrics banner extraction
                    try:
                        message_container = await page.query_selector(self.usercentrics_message_selector)
                        if message_container:
                            banner_text = await message_container.inner_text()
                            print("Extracted Usercentrics banner text:")
                            print(banner_text)
                            return banner_text.strip()
                    except Exception as e:
                        print(f"Usercentrics banner not found: {e}")

                    # First, attempt to extract text using the specific XPath selector
                    try:
                        await page.wait_for_selector("#onetrust-policy-text", timeout=10000)
                        element = await page.query_selector("#onetrust-policy-text")
                        if element:
                            # Use JavaScript to extract only the visible text
                            banner_text = await element.evaluate("(el) => el.textContent.trim()")
                            return banner_text.strip()
                    except Exception as e:
                        print(f"Specific selector #onetrust-policy-text not found: {e}")

                    # Fallback to other selectors
                    for selector in self.common_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                full_text = await element.inner_text()
                                print(f"Extracted text from selector {selector}:")
                                return full_text.strip()
                        except Exception as e:
                            print(f"Error with selector {selector}: {e}")
                            continue

                    return "Cookie banner not found using any common selectors."
                finally:
                    await browser.close()
        except Exception as e:
            return f"Error extracting cookie banner text: {str(e)}"

    def compare_cookie_banner_text(self, website_text, template_text):
        """Compare website cookie banner text with the template."""
        website_text_c = self.clean_string(website_text)
        template_text_c = self.clean_string(template_text)

        similarity = SequenceMatcher(None, template_text_c, website_text_c).ratio() * 100

        

        # Extract words and filter only likely German words
        website_words = re.findall(r'\b[A-Za-zäöüßÄÖÜ]+\b', website_text)  # Extract German-like words
        german_words = [word for word in website_words if re.search(r'[äöüßÄÖÜ]', word) or word.lower() in self.spell_checker]
        
        # Check spelling mistakes
        website_mistakes = [word for word in german_words if word.lower() not in self.spell_checker]


        feedback = f"""
        <strong>Template Text:</strong><br>
        <b>{template_text}</b><br><br>
        <strong>Website Text:</strong><br>
        <b>{website_text}</b><br><br>
        <strong>Similarity:</strong><br>
        <b>{similarity:.2f}%</b><br><br>
        """
        if website_mistakes:
            feedback += "Spelling mistakes in website text:<br>" + "<br>".join(f"- {word}" for word in website_mistakes)
        else:
            feedback += "No spelling mistakes found in the website text.<br>"

        is_conformant = similarity == 100 and len(website_mistakes) == 0
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
            # If no cookie banner text is found, return immediately without checking spelling mistakes
            if not website_text:
                return False, 0, "No cookie banner text found on the website."

            is_conformant, similarity, feedback = self.compare_cookie_banner_text(website_text, template_text)
            return is_conformant, similarity, feedback
        except Exception as e:
            return False, 0, f"Error during cookie banner text check: {str(e)}"


async def main():
    checker = CookieBannerText()
    url = "https://www.radbag.de/geschenkideen?gad_source=1&gclid=CjwKCAiA7Y28BhAnEiwAAdOJUIMPS-nQfDYq4DEyL8NUiy40hAQAwuqU6eDvKu4BI5CCtBJ7lnkg5BoCgR8QAvD_BwE"
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
    result, similarity, feedback = await checker.check_cookie_banner_text(url, template_text)
    print("Result:", result)
    print("Similarity:", similarity)
    print("Feedback:", feedback)


if __name__ == "__main__":
    asyncio.run(main())