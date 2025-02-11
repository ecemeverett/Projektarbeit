from playwright.async_api import async_playwright
import asyncio

class ConformDesignChecker:
    # Default selectors for various cookie-related elements
    DEFAULT_SELECTORS = {
        "cookie_settings": [
            # List of CSS selectors for "Cookie Settings" buttons across different websites
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
        ],
        "cookie_options": [
            # List of selectors for cookie options
            "#onetrust-group-container > div.ot-cat-lst.ot-scrollbar",
            "#onetrust-pc-sdk",
            "li.ot-cat-item.ot-cat-bdr",  # L'Oréal Paris cookie categories
            ".cookie-option",  # Generic selector
            # Additional selectors for English websites
            'div.cookie-options-container',
            'ul.cookie-options-list',
            '[data-testid="cookie-option"]',
            'div.sticky',  # The main sticky container of the cookie banne
            'div.hp__sc-yx4ahb-7',  # Urlaubspiraten main container
            'p.hp__sc-iv4use-0',  # Urlaubspiraten specific paragraph
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div',  # Specific selector for Urlaubspiraten cookie banner
            'div.hp__sc-yx4ahb-7',  # Main container for the cookie banner on Urlaubspiraten
            'p.hp__sc-hk8z4-0',  # Paragraphs containing cookie consent text
            'button.hp__sc-9mw778-1',  # Buttons for actions
            '#cookieboxBackgroundModal > div',  # Spezifischer Selector für den Cookie-Banner von santander
            '[data-testid="uc-default-banner"]',  # Selector for Zalando cookie banner
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
            '//*[@id="page-id-46"]/div[3]/div/div/div',
            'div[class*="cookie-notice"]',
            '[role="dialog"]',
            '[aria-label*="cookie"]',
            '[data-cookie-banner]',
            'div[style*="bottom"]',
            'div[style*="fixed"]',
            'div[data-borlabs-cookie-consent-required]',  # Selector for Borlabs Cookie
            'div#BorlabsCookieBox',  # Specific ID for Borlabs Cookie Box
            'div#BorlabsCookieWidget',  # Specific ID for Borlabs Cookie Widget
            'div.elementText',  # Selector for the custom cookie banner text container
        ],
       "accept_button": [
            # List of selectors for accept buttons
            "span#cmpbnyestxt:has-text('Alle akzeptieren')",
            "a.cmpboxbtn.cmpboxbtnyes.cmpxt_btn_yes",
            "a[role='button']:has-text('Alle akzeptieren')",
            "a[role='button'].cmpboxbtnyes",
            "a:has(span#cmpbnyestxt)",  # Select the <a> tag containing the <span> with text
            "a.cmpboxbtn.cmpboxbtnyes",
            "button:has-text('Alle akzeptieren')",  # 🇩🇪 German websites
            "button:has-text('Akzeptieren')",  # Some banners use only "Akzeptieren"
            "button:has-text('Einwilligen')",  # Some consent banners use "Einwilligen"
            "button:has-text('Accept All')",  # 🇺🇸 English websites
            "button:has-text('Accept')",  # Some sites use just "Accept"
            "button:has-text('Agree')",  # Alternative term
            "button:has-text('I Accept')",  # Alternative term
            "button:has-text('I Agree')",  # Alternative term
            "button:has-text('OK')",  # Some banners use "OK"
            "button:has-text('Got It')",  # Alternative button text
            "button:has-text('Consent')",  # Less common, but used
            "button:has-text('Allow All')",  # Alternative wording
            "button:has-text('Agree & Proceed')",  # Alternative text
            "button:has-text('Accept Cookies')",  # Explicit accept message
            "button:has-text('Ja, akzeptieren')",  # Some German sites
            "button:has-text('Zustimmen')",  # Alternative German term
            "button:has-text('Erlauben')",  # Some websites use "Erlauben"
            "button:has-text('Ich stimme zu')",  # Another alternative in German
            "button:has-text('Alles zulassen')",  # Some banners use this in German
            "button:has-text('Continue with cookies')",  # Used on some UK sites
            "[id*='accept']",  # Matches IDs containing "accept"
            "[class*='accept']",  # Matches classes containing "accept"
            "[data-testid*='accept']",  # Matches test attributes used in some banners
            "[aria-label*='accept']",  # Matches aria-label attributes for accessibility
            "[role='button']:has-text('Alle akzeptieren')",  # More generic role-based selector
            "[role='button']:has-text('Accept All')",  # Generic English role-based
            "a[role='button']:has-text('Einwilligen')",  # German alternative
            "#cmpbnyestxt",  # Direct span ID inside the accept button
            "a.cmpboxbtn.cmpboxbtnyes.cmptxt_btn_yes",  # Full class selector for <a> button
            "#cmpwelcomebtnyes a",  # Parent selector for settings button in cmpbox
            ".btn-accept",  # Generic class selector
            ".cookie-consent-accept",  # Used by some banners
            ".consent-accept",  # Common CSS class
            "button[onclick*='accept']",  # Buttons triggering accept action
            "span#cmpbnyestxt:has-text('Alle akzeptieren')",
            "a.cmpboxbtn.cmpboxbtnyes.cmpxt_btn_yes",
            "#cmpwelcomebtnyes a[role='button']",
        ],
        "save_button": [
            # List of selectors for save preference buttons
            "button:has-text('Auswahl speichern')",  # 🇩🇪 German websites
            "button:has-text('Einstellungen speichern')",  # Alternative German text
            "button:has-text('Speichern')",  # Shorter version of "Save"
            "button:has-text('Save Preferences')",  # 🇺🇸 English websites
            "button:has-text('Save Settings')",  # Alternative English text
            "button:has-text('Save & Continue')",  # Used by some sites
            "button:has-text('Save my choices')",  # Another variation
            "button:has-text('Confirm Choices')",  # Some consent banners
            "button:has-text('Apply Settings')",  # Alternative wording
            "button:has-text('Confirm')",  # Some sites use just "Confirm"
            "button:has-text('Accept Selection')",  # Another alternative
            "button:has-text('Save & Accept')",  # Used in some privacy popups
            "button:has-text('Keep Settings')",  # Alternative text
            "button:has-text('Continue with Selected')",  # Alternative wording
            "button:has-text('Accept and Continue')",  # Variation found on some sites
            "button:has-text('Bestätigen')",  # German: Confirm selection
            "button:has-text('Einstellungen bestätigen')",  # Another German phrase
            "[id*='save']",  # Matches IDs containing "save"
            "[class*='save']",  # Matches classes containing "save"
            "[data-testid*='save']",  # Test attribute
            "[aria-label*='save']",  # Matches aria-label attributes for accessibility
            "[role='button']:has-text('Auswahl speichern')",  # More generic role-based selector
            "[role='button']:has-text('Save Preferences')",  # Generic English role-based
            ".btn-save",  # Generic class selector
            ".cookie-consent-save",  # Common CSS class
            ".consent-save",  # Another common class
            "button[onclick*='save']",  # Buttons triggering save action
        ],
        "cookie_banner": [
            # List of selectors for detecting cookie banners
            'div.sticky',  # The main sticky container of the cookie banne
            'div.hp__sc-yx4ahb-7',  # Urlaubspiraten main container
            'p.hp__sc-iv4use-0',  # Urlaubspiraten specific paragraph
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div',  # Specific selector for Urlaubspiraten cookie banner
            'div.hp__sc-yx4ahb-7',  # Main container for the cookie banner on Urlaubspiraten
            'p.hp__sc-hk8z4-0',  # Paragraphs containing cookie consent text
            'button.hp__sc-9mw778-1',  # Buttons for actions
            '#cookieboxBackgroundModal > div',  # Spezifischer Selector für den Cookie-Banner von santander
            '[data-testid="uc-default-banner"]',  # Selector for Zalando cookie banner
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
            '//*[@id="page-id-46"]/div[3]/div/div/div',
            'div[class*="cookie-notice"]',
            'div.cookie-banner',        # English-specific cookie banner selector
            'div.cookie-consent',       # English-specific cookie banner selector
            'div.consent-banner',       # English-specific cookie banner selector
            'section.cookie-banner',    # English-specific cookie banner selector
            '[role="dialog"]',
            '[aria-label*="cookie"]',
            '[data-cookie-banner]',
            'div[style*="bottom"]',
            'div[style*="fixed"]',
            'div[data-borlabs-cookie-consent-required]',  # Selector for Borlabs Cookie
            'div#BorlabsCookieBox',  # Specific ID for Borlabs Cookie Box
            'div#BorlabsCookieWidget',  # Specific ID for Borlabs Cookie Widget
            'div.elementText',  # Selector for the custom cookie banner text container
            'h3:has-text("Datenschutzhinweis")',  # Check for the header text'
        ],
    }

    def __init__(self, selectors=None):
        """
        Initialize the checker with custom selectors if provided.
        """
        self.selectors = selectors or self.DEFAULT_SELECTORS

    async def check_all_conformity(self, browser, url):
        """
        Perform all checks for conformity in one function:
        1. Check if 'Cookie Settings' is at the bottom-left.
        2. Check if cookie options are stacked vertically.
        3. Check if buttons 'Alle akzeptieren' and 'Auswahl speichern' are the same size and aligned.
        4. Ensure readable font size for cookie banner elements.
        5. Test responsiveness across multiple devices.
        """
        feedback = f"<strong>Conform Design for {url}:</strong><br>"
        design_conform = True

        try:
            # Create a page and navigate to the URL
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            feedback += f"<strong>Checking URL:</strong> {url}<br>"

            # 1. Check if "Cookie-Einstellungen" is at the bottom-left
            cookie_settings = None
            for selector in self.selectors["cookie_settings"]:
                cookie_settings = await page.query_selector(selector)
                if cookie_settings:
                    break
            if cookie_settings:
                bounding_box = await cookie_settings.bounding_box()
                viewport = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
                if bounding_box and bounding_box['y'] > viewport['height'] - 200:  # Near the bottom
                    feedback += f"<strong>- 'Cookie Settings' is correctly positioned at the bottom-left.</strong><br>"
                else:
                    design_conform = False
                    feedback += "<strong>Warning:</strong> 'Cookie Settings' is not at the bottom-left.<br>"
            else:
                design_conform = False
                feedback += "<strong>Warning:</strong> 'Cookie Settings' link is missing.<br>"

            # 2. Check if cookie options are stacked vertically
            all_cookie_options = []

            # Loop through all possible selectors for cookie options
            for selector in self.selectors["cookie_options"]:
                cookie_options = await page.query_selector_all(selector)
                if cookie_options:
                    all_cookie_options.extend(cookie_options)

            if all_cookie_options:
                unique_boxes = set()
                valid_boxes = []

                for option in all_cookie_options:
                    box = await page.evaluate("(el) => el.getBoundingClientRect()", option)
                    # Filter out invalid boxes and ensure uniqueness
                    if box["height"] > 0 and box["y"] > 0:
                        box_tuple = (box["x"], box["y"], box["width"], box["height"])
                        if box_tuple not in unique_boxes:
                            unique_boxes.add(box_tuple)
                            # Exclude elements that are significantly taller than others (e.g., parent containers)
                            if box["height"] < 100:  # Arbitrary threshold to exclude large containers
                                valid_boxes.append(box)

                # Log bounding boxes for debugging
                feedback += f"<strong>- Found {len(valid_boxes)} valid cookie options across all selectors.</strong><br>"
                for i, box in enumerate(valid_boxes):
                    feedback += f"<strong>Option {i + 1} - Y: {box['y']}, Height: {box['height']}</strong><br>"

                # Check if valid elements are vertically stacked
                tolerance = 2  # Allow slight overlap or gap (in pixels)
                vertically_stacked = True
                for i in range(len(valid_boxes) - 1):
                    current_bottom = valid_boxes[i]["y"] + valid_boxes[i]["height"]
                    next_top = valid_boxes[i + 1]["y"]
                    if next_top - current_bottom > tolerance:
                        vertically_stacked = False
                        break

                if vertically_stacked:
                    feedback += "<strong>- Cookie options are stacked vertically.</strong><br>"
                else:
                    design_conform = False
                    feedback += "<strong><strong>Warning:</strong> Cookie options are not stacked vertically.</strong><br>"
            else:
                design_conform = False
                feedback += "<strong>Warning:</strong> No valid cookie options found.<br>"

           # 3. Check if buttons 'Alle akzeptieren' and 'Auswahl speichern' are the same size and aligned
            accept_button = None
            save_button = None

            # Track missing buttons for feedback
            missing_buttons = []

            # Find first matching 'Accept all' button
            for selector in self.selectors["accept_button"]:
                accept_button = await page.query_selector(selector)
                if accept_button:
                    break  # Stop searching after finding the first valid button
            if not accept_button:
                missing_buttons.append("'Accept all' button")

            # Find first matching 'Save preferences' button
            for selector in self.selectors["save_button"]:
                save_button = await page.query_selector(selector)
                if save_button:
                    break  # Stop searching after finding the first valid button
            if not save_button:
                missing_buttons.append("'Save preferences' button")

            # If both buttons are found, check size & alignment
            if accept_button and save_button:
                accept_box = await accept_button.bounding_box()
                save_box = await save_button.bounding_box()

                if accept_box and save_box:
                    if (
                        abs(accept_box["width"] - save_box["width"]) < 5
                        and abs(accept_box["height"] - save_box["height"]) < 5
                        and abs(accept_box["y"] - save_box["y"]) < 5
                    ):
                        feedback += "<strong>- Buttons 'Accept all' and 'Save preferences' are the same size and aligned.</strong><br>"
                    else:
                        design_conform = False
                        feedback += "<strong>Warning:</strong> Buttons are not aligned or of the same size.<br>"

            # If one or both buttons are missing, add a detailed feedback message
            if missing_buttons:
                design_conform = False
                feedback += f"<strong>Warning:</strong> {', '.join(missing_buttons)} is missing.<br>"

            # 4. Check font size for all elements in the cookie banner
            cookie_banner = None
            for selector in self.selectors["cookie_banner"]:
                cookie_banner = await page.query_selector(selector)
                if cookie_banner:
                    break
            if cookie_banner:
                elements = await cookie_banner.query_selector_all("*")
                small_font_found = False
                for element in elements:
                    font_size = await page.evaluate(
                        "(el) => parseFloat(window.getComputedStyle(el).fontSize)", element
                    )
                    if font_size < 11:  # Minimum readable font size
                        small_font_found = True
                        feedback += f"<strong>Warning:</strong> Element with font size {font_size}px is too small.<br>"
                        break
                if not small_font_found:
                      feedback += "<strong>- All elements have a readable font size.</strong><br>"

            # 5. Test responsiveness across devices
            devices = [
                {"name": "iPhone 12", "viewport": {"width": 390, "height": 844}, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"},
                {"name": "iPad Mini", "viewport": {"width": 768, "height": 1024}, "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"},
                {"name": "Galaxy S21", "viewport": {"width": 360, "height": 800}, "user_agent": "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"},
            ]

            for device in devices:
                try:
                    # Create a context for the specific device
                    context = await browser.new_context(
                        viewport=device["viewport"],
                        user_agent=device["user_agent"]
                    )
                    page = await context.new_page()
                    await page.goto(url, wait_until="load")

                    # Check for cookie banner visibility
                    cookie_banner = None
                    for selector in self.selectors["cookie_banner"]:
                        cookie_banner = await page.query_selector(selector)
                        if cookie_banner:
                            break

                    if cookie_banner:
                        feedback += f"<strong>- Cookie banner is functional on {device['name']}.</strong><br>"
                    else:
                        design_conform = False
                        feedback += f"<strong><strong>Warning:</strong> Cookie banner is not visible on {device['name']}.</strong><br>"

                    await context.close()
                except Exception as e:
                    feedback += f"<strong>Error:</strong> Device check failed for {device['name']} with error: {str(e)}.<br>"

        except Exception as e:
            design_conform = False
            feedback += f"<strong>Error:</strong> {str(e)}<br>"

        return design_conform, feedback

"""
async def main():
    url_list = [
        "https://www.frankenbrunnen.de/"
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        checker = ConformDesignChecker()

        for url in url_list:
            design_conform, feedback = await checker.check_all_conformity(browser, url)
            print("Is Design Conformant:", design_conform)
            print("Feedback:", feedback)

        await browser.close()


asyncio.run(main())
"""
