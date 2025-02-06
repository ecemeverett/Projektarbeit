import asyncio
from playwright.async_api import async_playwright, TimeoutError


class CookiePreferenceVis:
    def __init__(self):
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
            '[data-testid="uc-default-banner"]',  # Selector for Zalando cookie banner
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
            'div[id*="banner"]',
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
            '#BorlabsCookieEntranceA11YDescription'
        ]
        self.preference_selectors = [
            # Selectors for "Cookie-Einstellungen" or "Cookie Settings"
            'a.js-toggle-cookie-details', # Vileda
            "a:has-text('Cookie-Einstellungen')", # hansgrohe
            "button:has-text('Cookie-Einstellungen')", # henkel, weleda, Schwarzkopf, original-wagner, royal canin, gardena
            "a:has-text('Datenschutz-Einstellungen')",
            "button:has-text('Datenschutz-Einstellungen')", # henkel, weleda, Schwarzkopf, original-wagner
            "button:has-text('Einstellungen anpassen')", # henkel, weleda, Schwarzkopf, original-wagner'
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
            "a:has-text('Details zeigen')", # Franken Brunnen
            "button:has-text('Details zeigen')",
            "[data-testid='cookie-settings-button']",
            "#cookie-settings-link",
            '#cmpbntcustomtxt', # Beiersdorf ('Einstellungen button')
            "a:has-text('Cookie options')",
            "button:has-text('Cookie options')"
            "a:has-text('Einstellungen')",
            "button:has-text('Einstellungen')"
            "a:has-text('Manage Cookies')",
            "button:has-text('Manage Cookies')",
            '#cmpbox > div.cmpboxinner > div.cmpboxbtns',
            '#onetrust-pc-btn-handler', # kao, just spices, saint gobain
            "button:has-text('Ablehnen oder Einstellungen')", 
            "#cookiescript_manage > span:has-text('Cookie Einstellungen')", # radbag
            "#CybotCookiebotDialogNavDetails:has-text('Einstellungen')", # ivoclar vivadent
            "#ccm-widget > div > div.ccm-modal--body > div.ccm-widget--buttons > button:nth-child(2):has-text('Einstellungen')", # kneipp
            "button:has-text('Präferenzen')",
        ]
        self.preference_center_identifiers = [
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
            'div > div > div', # Santander (cookieboxSettingsModal)
            'body > div.cmp-container.first-load.second-view', # verivox
            '#cookiescript_injected', # radbag,
            '#onetrust-pc-sdk',
            '#CybotCookiebotDialog', # ivoclar vivadent
        ]

    async def check_visibility(self, page_or_frame):
        """
        Check for visible cookie banners in the given page or frame.
        """
        found_banners = []
        for selector in self.common_selectors:
            elements = await page_or_frame.query_selector_all(selector)
            for element in elements:
                if element and await element.is_visible():
                    box = await element.bounding_box()
                    if box and box['width'] > 300 and box['height'] > 50:
                        element_text = (await element.evaluate("el => el.textContent")).lower() or ""
                        found_banners.append({
                            'selector': selector,
                            'text': element_text,
                            'bounding_box': box,
                        })

        for banner in found_banners:
            print(f"Found banner with selector: '{banner['selector']}'")
            print(f"Element text: '{banner['text']}'")
            print(f"Element bounding box: {banner['bounding_box']}")

        keywords = ["cookie", "consent", "gdpr", "privacy", "tracking", "preferences"]
        for banner in found_banners:
            if any(keyword in banner['text'] for keyword in keywords):
                return True, f"Cookie banner detected."

        return False, "No relevant cookie banner detected."

    async def check_preference_center(self, page_or_frame):
        """
        Check if 'Cookie-Einstellungen' or 'Cookie Settings' is clickable and opens the Preference Center.
        """
        for pref_selector in self.preference_selectors:
            preference_button = await page_or_frame.query_selector(pref_selector)
            if preference_button and await preference_button.is_visible():
                print(f"Preference Center button found: {pref_selector}")

                # Click the button
                await preference_button.click()
                await page_or_frame.wait_for_timeout(2000)  # Give time for modal to open

                # ✅ Check if a new element (Preference Center) appeared
                for identifier in self.preference_center_identifiers:
                    preference_center = await page_or_frame.query_selector(identifier)
                    if preference_center and await preference_center.is_visible():
                        print(f"✅ Preference Center detected with selector: {identifier}")
                        
                        # ✅ Debugging - Print inner HTML to verify content
                        inner_html = await preference_center.inner_html()
                        print(f"Preference Center content: {inner_html[:500]}...")  # Limit output for readability

                        return True, "Preference Center is accessible and opened successfully."

                print("❌ Preference Center button was clicked, but the modal did not open.")
                return False, "Preference Center button was clicked, but it did not open."

        print("❌ No 'Cookie-Einstellungen' or Preference Center button found.")
        return False, "No 'Cookie-Einstellungen' or Preference Center button found."

    async def check_visibility_and_preference_center(self, url):
        """
        Combined check for cookie banner visibility and Preference Center accessibility.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
            )
            page = await context.new_page()

            try:
                print(f"Loading URL: {url}")
                for attempt in range(5):
                    try:
                        await page.goto(url, timeout=60000)
                        await page.wait_for_load_state('networkidle')
                        print("Page loaded successfully.")
                        break
                    except TimeoutError:
                        print(f"Attempt {attempt + 1} failed. Retrying...")
                else:
                    return False, "Page failed to load after multiple attempts."

                result, message = await self.check_visibility(page)
                if result:
                    print("Cookie banner detected.")
                    preference_result, preference_message = await self.check_preference_center(page)
                    if preference_result:
                        return True, "Cookie Preference is accessible from the cookie banner."
                    return False, preference_message

                return False, message

            except Exception as e:
                return False, f"Error during check: {e}"

            finally:
                await context.close()
                await browser.close()

"""
async def main():
    url = "https://www.medienanstalt-nrw.de/"  # Replace with your target URL
    checker = CookiePreferenceVis()
    result, message = await checker.check_visibility_and_preference_center(url)
    print(f"URL: {url}")
    print("Result:", result)
    print("Message:", message)


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
"""
