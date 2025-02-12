from playwright.async_api import async_playwright, TimeoutError
import asyncio
from langdetect import detect


class CookiePreferenceLinkValidator:
    def __init__(self):
        """
        Initializes the CookiePreferenceLinkValidator class.
        Defines selectors for common cookie banners, preference centers, and relevant links.
        """
        # Common selectors used to detect cookie banners across various websites
        self.common_selectors = [
             # Common cookie banner selectors
            'div.sticky',  # The main sticky container of the cookie banner
            'div.hp__sc-yx4ahb-7',  # Urlaubspiraten main container
            'p.hp__sc-iv4use-0',  # Urlaubspiraten specific paragraph
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div',  # Specific selector for Urlaubspiraten cookie banner
            'div.hp__sc-yx4ahb-7',  # Main container for the cookie banner on Urlaubspiraten
            'p.hp__sc-hk8z4-0',  # Paragraphs containing cookie consent text
            'button.hp__sc-9mw778-1',  # Buttons for actions
            '#cookieboxBackgroundModal > div',  # Spezifischer Selector für den Cookie-Banner von santander
            '[data-testid="uc-default-banner"]', 
            'div.cmp-container', # verivox
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
            '#onetrust-consent-sdk',
            'button.ccm--button-primary',
            'div[data-testid="uc-default-wall"]',
            'div[role="dialog"]', # Schwarzkopf, hochland, Hassia Gruppe
            'div.cc-banner',
            'section.consentDrawer',
            'div[class*="cookie"]', # hansgrohe
            'div[class*="consent"]',
             # 'div[id*="banner"]',
            '#onetrust-banner-sdk > div > div.ot-sdk-container > div', # kao
            'div[class*="cookie-banner"]',
            '//*[@id="page-id-46"]/div[3]/div/div/div',
            'div[class*="cookie-notice"]',
            '[role="dialog"]', # tesa
            '[aria-label*="cookie"]',
            '[data-cookie-banner]',
            'div[style*="bottom"]', # weleda, BMW Group
            'div[style*="fixed"]',
            'div[data-borlabs-cookie-consent-required]',  # Selector for Borlabs Cookie
            'div#BorlabsCookieBox',  # Specific ID for Borlabs Cookie Box
            'div#BorlabsCookieWidget',  # Specific ID for Borlabs Cookie Widget
            'div.elementText',  # Selector for the custom cookie banner text container
            'h3:has-text("Datenschutzhinweis")',  # Check for the header text'
            '#BorlabsCookieEntranceA11YDescription',
            '#onetrust-banner-sdk', # original wagner
        ]

        # Selectors used to detect the preference center, where users can modify their cookie settings
        self.preference_center_selectors = [
            # Identifiers for Preference Center (dynamic handling for various websites)
            'div#onetrust-pc-sdk[aria-label="Preference center"]', # Loreal, kao, henkel, weleda, Schwarzkopf, original-wagner, just spices, royal canin, gardena, husqvarna, weber, saint gobain
            'div[role="dialog"][aria-label*="Preference center"]',
            'div[role="dialog"][aria-label*="Einstellungen"]',
            'div[class*="preference"]',
            'section[aria-label*="Privacy Preferences"]',
            'div[aria-modal="true"]', # Dr. Oetker, tesa, hochland, coa, brandt, weber, kneipp
            '#cookieSettings > div', # vileda
            '#privacy-container', # Danone
            '#hc-panel', # Hassia Gruppe
            'body > div > div > section', # BMW Group, Urlaubspiraten
            'body > div.cookie-layer-advanced.state-visible', # hansgrohe
            'div > div > div', # Santander (cookieboxSettingsModal, griesson)
            'body > div.cmp-container.first-load.second-view', # verivox
            '#cookiescript_injected', # radbag,
            '#onetrust-pc-sdk',
            '#CybotCookiebotDialog', # ivoclar vivadent
        ]

        # Selectors for buttons/links used to open the preference center
        self.preference_selectors = [
            # Selectors for "Cookie-Einstellungen" or "Cookie Settings"
            'a.js-toggle-cookie-details', # Vileda
            "a:has-text('Cookie-Einstellungen')", # hansgrohe
            "button:has-text('Cookie-Einstellungen')", # henkel, weleda, Schwarzkopf, original-wagner, royal canin, gardena
            "a:has-text('Datenschutz-Einstellungen')",
            "button:has-text('Datenschutz-Einstellungen')", # henkel, weleda, Schwarzkopf, original-wagner
            "button:has-text('Einstellungen anpassen')", # henkel, weleda, Schwarzkopf, original-wagner'
            "a:has-text('Details zeigen')", # Franken Brunnen
            "a:has-text('Details')", # brandt
            "#CybotCookiebotDialogBodyLevelDetailsButton:has-text('Details zeigen')", # ivoclar vivadent
            "a:has-text('Cookie Settings')",
            "button:has-text('Cookie Settings')",
            "button:has-text('Anpassen')", # BWM Group, Urlaubspiraten
            "button:has-text('Mehr Informationen')", # coa
            "button:has-text('Einstellungen ändern')", # Santander
            "a:has-text('Personalize my choice')",
            "button:has-text('Personalize my choice')", # Danone
            "button:has-text('Details & Einstellungen')", # Danone
            "a:has-text('Detail-Auswahl')",
            "button:has-text('Detail-Auswahl')", # Dr. Oetker
            "button:has-text('Details zeigen')",
            "[data-testid='cookie-settings-button']",
            "#cookie-settings-link",
            '#cmpbntcustomtxt', # Beiersdorf ('Einstellungen button')
            "a:has-text('Cookie options')",
            "button:has-text('Cookie options')",
            "a:has-text('Einstellungen')",
            "button:has-text('Einstellungen')",
            "a:has-text('Manage Cookies')",
            "button:has-text('Manage Cookies')",
            '#cmpbox > div.cmpboxinner > div.cmpboxbtns',
            '#onetrust-pc-btn-handler', # kao, just spices, saint gobain
            "button:has-text('Ablehnen oder Einstellungen')", 
            "#cookiescript_manage > span:has-text('Cookie Einstellungen')", # radbag
            "#CybotCookiebotDialogNavDetails:has-text('Einstellungen')", # ivoclar vivadent
            "#ccm-widget > div > div.ccm-modal--body > div.ccm-widget--buttons > button:nth-child(2):has-text('Einstellungen')", # kneipp
            "button:has-text('Präferenzen')",
            "a:has-text('Einstellungen verwalten')",
        ]

        # Text variations used to identify Privacy Policy and Imprint links
        self.imprint_texts = ["Impressum", "Imprint"]
        self.privacy_policy_texts = ["Datenschutzinformationen", "Privacy Policy"]

    async def is_visible_cookie_banner(self, page_or_frame):
        """
        Detects visible cookie banners based on predefined selectors.
        Ensures the banner meets basic size criteria.
        """
        for selector in self.common_selectors:
            elements = await page_or_frame.query_selector_all(selector)
            for element in elements:
                if element and await element.is_visible():
                    box = await element.bounding_box()
                    if box and box['width'] > 300 and box['height'] > 50:  # Basic size check
                        return selector # Return the selector if a valid banner is found
        return None # Return None if no valid banner is detected

    async def validate_links(self, element, texts):
        """
        Checks for the presence and functionality of links within an element.
        Verifies if the links are found, clickable, and have a valid URL.
        """
        found = clickable = False
        feedback = ""
        for text in texts:
            link = await element.query_selector(f'a:has-text("{text}")')
            if link:
                found = True
                if await link.is_enabled():
                    clickable = True
                    url = await link.get_attribute("href")
                    if url:
                        # Wrap long URLs to improve readability
                        formatted_url = "<br>".join([url[i:i+80] for i in range(0, len(url), 80)])
                        feedback += f"<strong>{text} URL:</strong> {formatted_url} <strong>clickable:</strong> ✓<br>"
                    else:
                        feedback += f"<strong>{text} link does not have a valid href attribute.</strong><br>"
                else:
                    feedback += f"<strong>{text} link is not clickable.</strong><br>"
            else:
                feedback += f"<strong>{text} link not found.</strong><br>"
        return found, clickable, feedback

    async def check_iframes(self, page, validation_function, *args):
        """
        Checks all iframes for cookie banners or preference centers.
        """
        iframes = await page.query_selector_all('iframe')
        for iframe in iframes:
            iframe_content = await iframe.content_frame()
            if iframe_content:
                result = await validation_function(iframe_content, *args)
                if result:
                    return result
        return None

    async def check_cookie_preference_center(self, page):
        """
        Validates links inside the Cookie Preference Center.
        """
        feedback = ""
        for selector in self.preference_center_selectors:
            preference_center = await page.query_selector(selector)
            if preference_center and await preference_center.is_visible():
                feedback += f"<strong>Cookie Preference Center detected using selector:</strong> {selector}<br>"

                # Detect language
                center_text = await preference_center.inner_text()
                detected_language = detect(center_text)
                privacy_texts = self.privacy_policy_texts if detected_language != "de" else ["Datenschutzinformationen"]
                imprint_texts = self.imprint_texts if detected_language != "de" else ["Impressum"]

                # Validate Privacy Policy links
                privacy_found, privacy_clickable, privacy_feedback = await self.validate_links(preference_center, privacy_texts)
                feedback += privacy_feedback

                # Validate Imprint links
                imprint_found, imprint_clickable, imprint_feedback = await self.validate_links(preference_center, imprint_texts)
                feedback += imprint_feedback

                return (
                    privacy_found and privacy_clickable and imprint_found and imprint_clickable,
                    feedback,
                )
        return False, "<strong>No visible Cookie Preference Center found.</strong>"

    async def check_preference_links(self, url):
        """
        Checks for the presence of a cookie banner and validates Privacy Policy and Imprint links.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537"
            )
            page = await context.new_page()

            try:
                print(f"Visiting URL: {url}")
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state("networkidle")

                # Check for cookie banner on the main page
                cookie_banner_selector = await self.is_visible_cookie_banner(page)
                if not cookie_banner_selector:
                    # Check iframes for cookie banners
                    iframe_result = await self.check_iframes(page, self.is_visible_cookie_banner)
                    if iframe_result:
                        cookie_banner_selector = iframe_result
                    else:
                        return False, "No visible cookie banner found."

                print(f"Cookie banner detected using selector: {cookie_banner_selector}")
                cookie_banner = await page.query_selector(cookie_banner_selector)

                # Detect language of the cookie banner
                banner_text = await cookie_banner.inner_text()

                # Falls der Text leer oder None ist, Standardwert setzen
                if not banner_text or banner_text.strip() == "":
                    detected_language = "de"  # Fallback auf German
                else:
                    try:
                        detected_language = detect(banner_text)
                    except Exception as e:
                        print(f"Language detection failed: {e}")  # Debugging-Info ausgeben
                        detected_language = "de"  # Fallback auf German

                privacy_texts = self.privacy_policy_texts if detected_language != "de" else ["Datenschutzinformationen"]
                imprint_texts = self.imprint_texts if detected_language != "de" else ["Impressum"]

                # Initialize feedback variable
                feedback = ""
                # Click "Cookie-Einstellungen" or "Einstellungen" button if available
                for selector in self.preference_selectors:
                    preference_button = await cookie_banner.query_selector(selector)
                    if preference_button:
                        print(f"Found and clicking preference button: {selector}")
                        await preference_button.click()
                        await page.wait_for_timeout(2000)  # Wait for preference center to load
                        break  # Stop after clicking the first found button
                     # If no preference button was found, return feedback immediately
                if not preference_button:
                    print("No preference button found.")
                    return False, "<strong>No button for the cookie preference center was found.</strong><br>"

                # Check for cookie preference center on the main page or in iframes
                valid, feedback = await self.check_cookie_preference_center(page)
                iframe_result = await self.check_iframes(page, self.check_cookie_preference_center)
                if not valid and iframe_result:
                    valid, feedback = iframe_result
                    
                feedback += feedback  # Append preference center feedback

                # Validate Privacy Policy and Imprint links in the cookie banner
                privacy_found, privacy_clickable, privacy_feedback = await self.validate_links(cookie_banner, privacy_texts)
                imprint_found, imprint_clickable, imprint_feedback = await self.validate_links(cookie_banner, imprint_texts)

                return (
                    privacy_found and privacy_clickable and imprint_found and imprint_clickable,
                    f"{privacy_feedback}{imprint_feedback}",
                )

            except TimeoutError:
                return False, "Page load timed out."
            except Exception as e:
                return False, f"An error occurred: {e}"
            finally:
                await context.close()
                await browser.close()

"""
# Uncomment the following code to test the implementation
async def main():
    validator = CookiePreferenceLinkValidator()
    url = "https://www.medienanstalt-nrw.de/"  # Replace with your target URL
    result, message = await validator.check_preference_links(url)
    print("Result:", result)
    print("Message:", message)


if __name__ == "__main__":
    asyncio.run(main())
"""
