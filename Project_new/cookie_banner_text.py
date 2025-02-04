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
            "Widerrufsmöglichkeit",
            'Verarbeitungsvorgänge',
            'Überwachungsprogrammen',
            'Klagemöglichkeit',
            'Endgeräteinformationen'
        ])
        
        self.spell_checker_en.word_frequency.load_words([
            
        ])
        self.usercentrics_banner_selector = "div[data-testid='uc-default-banner']"
        self.usercentrics_message_selector = "div[data-testid='uc-message-container']"
         # 🔹 **Common Selectors First** (Most Commonly Used Cookie Banners)
        self.common_selectors = [
            #'div[class*="cookie"]',  # Most generic, covers a wide range of cookie banners (Santander)
            'div[class*="cookie-banner"]',  # Very common phrasing in cookie banners
            'div[class*="cookie-notice"]',  # Frequently used for cookie consent notifications
            #'div[class*="consent"]',  # Used for general consent dialogs, including cookies
            '[aria-label*="cookie"]',  # Accessibility attribute, common in cookie banners
            '[data-cookie-banner]',  # Websites often use this structured attribute for cookie banners
            #'div[style*="bottom"]',  # Sticky banners at the bottom of the page
            #'div[style*="fixed"]',  # Fixed-position banners appearing anywhere on the screen (vendis capital)

            # 🔹 Framework-Specific (Ordered by Popularity)
            '#onetrust-policy-text > div', # OneTrust – specific child element (e.g., L'Oréal)
            '#onetrust-banner-sdk',  # OneTrust framework (very widely used) (gardena, husqvarna, kärcher, saint gobain, aldi süd, hoyavision)
            '#onetrust-policy-text',  # OneTrust framework – text container
            '#onetrust-banner-sdk > div',
            '#uc-show-more', # coa , hochland, aldi-onlineshop
            'div[data-testid="uc-default-banner"]',  # Usercentrics framework
            'div[data-borlabs-cookie-consent-required]',  # Borlabs framework
            'div#BorlabsCookieBox',  # Borlabs specific ID
            'div#BorlabsCookieWidget',  # Borlabs widget
            '#CybotCookiebotDialogBodyContentText > p:nth-child(1)', # tetesept
            '#CybotCookiebotDialogBodyContentText',  # Cybot framework (weber), Landesanstalt für Medien nrw
        ]
        
         # 🔹 **Less Common Selectors** (Website-Specific)
        self.specific_selectors = [
            '#cmpboxcontent > div > div.cmpboxtxt.cmptxt_txt',  # Beiersdorf, Hubert Burda Media
            '#page-id-46 > div.l-module.p-privacy-settings.t-ui-light.is-visible > div > div > div > div.p-privacy-settings__message-button-wrapper > div', # Griesson
            '#uc-privacy-description', # Dr. Oetker
            '#popin_tc_privacy_text', # Danone
            'body > div > div > section > div.content > p',  # BMW Group
            '#cookieboxStartDescription', # Santander
            'div.desktop-view > p',  # Verivox 
            '#consent-wall > div.layout-row.consentDescription', # 1&1
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div > div.hp__sc-s043ov-6.gqFIYM > div',  # Urlaubspiraten
            '#privacydialog\\:desc',  #  
            '#cookiescript_description',  # radbag
            'div#onetrust-policy-text',
            '#ccm-widget > div > div.ccm-modal--body > div.ccm-widget--text.cover-scrollbar > div > div.ccm-widget--introduction > div', #Merz
            'div#CybotCookiebotDialogBodyContentText',  #
            '.cookie-layer-advanced__content-text',  # hansgrohe
            '#modal-cookie > div > div > form > div.modal-body > div.modal-text.wysiwyg-content', #Gemeinde Wasserburg
            'body > div.bwr-cookie.bwr-cookie-new.js-cookie.bwr-active > div > div > form > div.bwr-cookie__info > div.bwr-cookie__info-text', # beuth (dinmedia)
            '#BorlabsCookieEntranceA11YDescription', # Ehinger Energie
            '#cookieNoticeInner > div > div.elementSection.elementSection_var0.elementSectionPadding_var10.elementSectionMargin_var0.elementSectionInnerWidth_var100.elementSectionBackgroundColor_var0 > div > div.elementText.elementText_var0.elementTextListStyle_var0 > p', # SWHN
            'body > div > div > div.om-cookie-panel.active > div.cookie-panel__description > p:nth-child(1)', # CAU
            'div[class*="cookie"]',
            '//*[@id="onetrust-policy-text"]/div',  # 
        ]
        self.excluded_selectors = [
            'button',  # Exclude all buttons
            'input',  # Exclude input fields
            'select',  # Exclude dropdowns
            'textarea',  # Exclude textareas
            '[role="button"]',  # Exclude anything with button role
            '[role="link"]',  # Exclude anything with link role
            '[class*="btn"]',  # Any elements with "btn" class (common for buttons)
            '[class*="button"]',  # Any elements with "button" in class
            '[class*="modal-actions"]',  # Footer buttons container
            '#cookieSettings > div > div > div > div > div.modal-actions.text-center.text-sm-right',  # Vileda action buttons
           # '#onetrust-group-container > div.ot-cat-lst.ot-scrollbar',
            '#onetrust-policy-title',
            '#onetrust-policy-text > a.ot-imprint-link',
            '#onetrust-policy-text > a.ot-cookie-policy-link',
            '#onetrust-policy-text > a:nth-child(2)',
            '#onetrust-policy-text > a:nth-child(3)', 
            '#cookieboxBackgroundModal > div > div > div.cookieboxStartWrap > div.cookieboxStartFooter',
            'div[class*="language"]',  # Exclude language selector divs
            'div[class*="lang"]',  # Catch other possible class names
            'ul[class*="languages"]',  # Exclude list elements containing language options
            'li[class*="lang"]',  # Exclude list items with language options
            'span[class*="language"]',  # Exclude span elements with language text
            'a[href*="/en"]',  # Exclude direct language links
            'a[href*="/fr"]',  # Exclude direct language links
            # 🔹 **Newsletter Exclusions**
            'div.mod-newsletter-trigger',  # Exclude newsletter trigger
            'div.newsletterbar-inner',  # Exclude newsletter bar container
            'section#newsletter-form',  # Exclude newsletter modal
            'div.newsletterbar-content'  # Exclude newsletter content
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
                    
                    # ✅ **Wait for the page to fully load**
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_selector("body", timeout=15000)  # Ensure DOM is ready
                    await asyncio.sleep(2)  # Small delay to allow elements to fully render

                    print("✅ Page loaded successfully.")
                    
                    # Fallback to other selectors
                    for selector in self.common_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                full_text = await element.inner_text()
                                 # Remove unwanted elements
                                for exclude_selector in self.excluded_selectors:
                                    unwanted_elements = await element.query_selector_all(exclude_selector)
                                    for unwanted in unwanted_elements:
                                        await unwanted.evaluate("(el) => el.remove()")

                                # Get clean text after removing unwanted elements
                                clean_text = await element.inner_text()
                                
                                print(f"✅ Cookie banner found with selector: {selector}")
                                print(f"📜 Extracted Clean Text: {clean_text[:500]}...")  # Limiting output length
                                return clean_text.strip()
                            
                        except Exception as e:
                            print(f"Error with selector {selector}: {e}")
                            continue
                    
                    # 🔹 **Check Less Common (Website-Specific) Selectors**
                    for selector in self.specific_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                banner_text = await element.inner_text()
                                # Remove unwanted elements
                                for exclude_selector in self.excluded_selectors:
                                    unwanted_elements = await element.query_selector_all(exclude_selector)
                                    for unwanted in unwanted_elements:
                                        await unwanted.evaluate("(el) => el.remove()")

                                # Get clean text after removing unwanted elements
                                clean_text = await element.inner_text()

                                print(f"✅ Cookie banner found with specific selector: {selector}")
                                return clean_text.strip()
                        except Exception as e:
                            print(f"⚠️ Error using selector {selector}: {e}")
                            continue

                    
                   
                finally:
                    await browser.close()

        except Exception as e:
            print(f"❌ Error extracting cookie banner text: {str(e)}")
            

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

"""
async def main():
    checker = CookieBannerText()
    url = "https://www.medienanstalt-nrw.de/"
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
"""
