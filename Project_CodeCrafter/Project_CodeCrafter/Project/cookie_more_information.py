from playwright.async_api import async_playwright
import re


class CookieInfoChecker:
    # Default selectors for cookie settings buttons and expandable "More Information" buttons
    DEFAULT_SELECTORS = {
        "cookie_settings_button": [
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
            "#cookieSettings > div > div > div > div > div.consent-info.d-flex.align-items-center > p > a.js-toggle-cookie-details",
            "button:has-text('Cookies Settings')", 
            
        ],
        "expand_buttons": [
            # List of CSS selectors for expandable "More Information" buttons in cookie settings
            ".ot-plus-minus",  # General selector for all "+" symbols
            ".CybotCookiebotDialogDetailBodyContentCookieContainerButton", # expand/collapse arrow
            "button[ot-accordion]",  # New selector for accordion-style buttons
            "#hp-app > div.hp__sc-s043ov-0.eTEUOO > div > div.hp__sc-s043ov-6.gqFIYM > div > div:nth-child(3) > div.hp__sc-1ym4vzb-1.jTIJDL", # Urlaubspirateb
            "#ccm-control-panel > div > div.ccm-modal--body > div.ccm-control-panel--purposes > div.ccm-control-panel--purpose", # Merz
            
        ],
    }
    
    def __init__(self, selectors=None):
        """
        Initialize the class with default selectors unless custom ones are provided.
        """
        self.selectors = selectors or self.DEFAULT_SELECTORS

    async def find_more_info_buttons(self, browser, url):
        """
        Detect the number of "More Information" buttons on the cookie settings page.
        """
        feedback = f"<strong>Checking for 'More Information' buttons in the Cookie Preference Center.>"
        buttons_found = 0
        section_names = []

        try:
            # Open a new browser context and page
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)

            # Step 1: Click on "Cookie Einstellungen" (Cookie Settings) button if found
            for selector in self.selectors["cookie_settings_button"]:
                cookie_settings_button = await page.query_selector(selector)
                if cookie_settings_button:
                    # Use JavaScript to click to avoid scroll issues
                    await page.evaluate("(el) => el.click()", cookie_settings_button)
                    await page.wait_for_timeout(3000)  # Wait for the modal to load
                    feedback += "- Successfully clicked 'Cookie Einstellungen'.<br>"
                    break
            else:
                feedback += "<strong>Warning:</strong> Cookie Banner or 'Cookie Einstellungen' does not exist.<br>"
                return buttons_found, feedback

            # Step 2: Locate all "More Information" buttons
            for selector in self.selectors["expand_buttons"]:
                expand_buttons = await page.query_selector_all(selector)
                if expand_buttons:
                    buttons_found = len(expand_buttons)
                    feedback += f"<strong>- Found {buttons_found} 'More Information' buttons.</strong><br>"
                    
                    # Extract section names where these buttons are located
                    for button in expand_buttons:
                        parent_section = await button.evaluate(
                            """(el) => {
                                let section = el.closest('div');
                                while (section && !section.innerText.includes('Unbedingt erforderliche Cookies') && 
                                    !section.innerText.includes('Leistungs-Cookies') && 
                                    !section.innerText.includes('Funktionelle Cookies') &&
                                    !section.innerText.includes('Werbe-Cookies') &&
                                    !section.innerText.includes('Social-Media-Cookies') &&
                                    !section.innerText.includes('Notwendig') &&
                                    !section.innerText.includes('Präferenzen') &&
                                    !section.innerText.includes('Statistiken') &&
                                    !section.innerText.includes('Marketing') &&
                                    !section.innerText.includes('Nicht klassifiziert') &&
                                    !section.innerText.includes('Targeting Cookies') &&
                                    !section.innerText.includes('Preferences') &&
                                    !section.innerText.includes('Statistics') &&
                                    !section.innerText.includes('Unclassified') &&
                                    !section.innerText.includes('Cookies für Marketingzwecke') &&
                                    !section.innerText.includes('Anzeigen / Ads') &&
                                    !section.innerText.includes('Personalisierung') &&
                                    !section.innerText.includes('Analyse / Statistiken') &&
                                    !section.innerText.includes('Sonstiges') &&
                                    !section.innerText.includes('Social Media') &&
                                    !section.innerText.includes('Performance Cookies')) {
                                    section = section.parentElement;
                                }
                                return section ? section.innerText.split('\\n')[0] : 'Unknown Section';
                            }"""
                        )
                        if parent_section:
                            # Clean section name (remove numbers and extra spaces)
                            cleaned_name = re.sub(r"\d+", "", parent_section).strip()
                        
                            # Extract only the **first two words** (avoiding long descriptions)
                            cleaned_name = " ".join(cleaned_name.split()[:2]) # Keep first two words

                            section_names.append(cleaned_name)
                    break
            else:
                feedback += "<strong>Warning:</strong> No 'More Information' buttons found.<br>"
            
            if section_names:
                formatted_sections = ", ".join(set(section_names))  # Use set() to remove duplicates
                feedback += f"<strong>More Information found for:</strong> {formatted_sections}.<br>"

        except Exception as e:
             return 0, f"Error while checking 'More Information' buttons: {e}"

        return buttons_found, feedback

# Main function to test the CookieInfoChecker class
"""
async def main():
    url = "https://www.medienanstalt-nrw.de/" # Example URL

    async with async_playwright() as p:
        # Launch browser (headless=False opens a visible browser window)
        browser = await p.chromium.launch(headless=False)
        checker = CookieInfoChecker()

        # Run the checker function
        buttons_found, feedback = await checker.find_more_info_buttons(browser, url)
        print("Buttons Found:", buttons_found)
        print("Feedback:", feedback)

        # Close the browser
        await browser.close()

# Run the async main function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""
