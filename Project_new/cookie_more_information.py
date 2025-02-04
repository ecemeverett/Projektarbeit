from playwright.async_api import async_playwright


class CookieInfoChecker:
    DEFAULT_SELECTORS = {
        "cookie_settings_button": [
            "#onetrust-pc-btn-handler",  # Selector for "Cookie Einstellungen"
            "a:has-text('Cookie-Einstellungen')",
            "button:has-text('Cookie Einstellungen')"
        ],
        "expand_buttons": [
            ".ot-plus-minus",  # General selector for all "+" symbols
        ],
    }

    def __init__(self, selectors=None):
        self.selectors = selectors or self.DEFAULT_SELECTORS

    async def find_more_info_buttons(self, browser, url):
        """
        Detect the number of "More Information" buttons on the cookie settings page.
        """
        feedback = f"<strong>Checking for 'More Information' buttons on {url}:</strong><br>"
        buttons_found = 0

        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)

            # Step 1: Click on "Cookie Einstellungen"
            for selector in self.selectors["cookie_settings_button"]:
                cookie_settings_button = await page.query_selector(selector)
                if cookie_settings_button:
                    # Use JavaScript to click to avoid scroll issues
                    await page.evaluate("(el) => el.click()", cookie_settings_button)
                    await page.wait_for_timeout(3000)  # Wait for the modal to load
                    feedback += "- Successfully clicked 'Cookie Einstellungen'.<br>"
                    break
            else:
                feedback += "<strong>Warning:</strong> 'Cookie Einstellungen' button not found.<br>"
                return buttons_found, feedback

            # Step 2: Locate all "More Information" buttons
            for selector in self.selectors["expand_buttons"]:
                expand_buttons = await page.query_selector_all(selector)
                if expand_buttons:
                    buttons_found = len(expand_buttons)
                    feedback += f"<strong>- Found {buttons_found} 'More Information' buttons.</strong><br>"
                    break
            else:
                feedback += "<strong>Warning:</strong> No 'More Information' buttons found.<br>"

        except Exception as e:
             return 0, f"Error while checking 'More Information' buttons: {e}"

        return buttons_found, feedback

"""
async def main():
    url = "https://www.loreal-paris.de/?gad_source=1&gclid=CjwKCAiAtNK8BhBBEiwA8wVt98yf4soIaCPMjDVDML61IlCPL90l_G8Cu3iesEMS9a6Wo_g7cT8ADRoC-I0QAvD_BwE&gclsrc=aw.ds"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        checker = CookieInfoChecker()

        buttons_found, feedback = await checker.find_more_info_buttons(browser, url)
        print("Buttons Found:", buttons_found)
        print("Feedback:", feedback)

        await browser.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""
