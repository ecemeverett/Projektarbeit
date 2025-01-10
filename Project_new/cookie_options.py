from playwright.async_api import async_playwright, TimeoutError
import asyncio

class CookieSelectionChecker:
    def __init__(self):
        self.expected_options = [
            "Leistungs-Cookies",
            "Funktionelle Cookies",
            "Werbe-Cookies",
            "Social-Media-Cookies",
        ]
        self.onetrust_banner_selector = "#onetrust-banner-sdk"
        self.cookiebot_banner_selector = "#CybotCookiebotDialog"
        self.settings_button_selector = "button#onetrust-pc-btn-handler"
        self.onetrust_settings_menu_selector = "#onetrust-pc-sdk"
        self.checkbox_selector = (
            "input[type=\"checkbox\"] + label, div.ot-checkbox-label span, div.ot-checkbox-label"
        )
        self.cookiebot_toggle_selector = "div.CybotCookiebotDialogBodyLevelButtonWrapper span"

    async def check_cookie_selection(self, url):
        """
        Checks for specific cookie categories and shows their presence and checked status.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Load the page
                await page.goto(url, timeout=30000)
                print("Page loaded successfully.")

                available_options = {}

                # Check for OneTrust banner
                try:
                    await page.wait_for_selector(self.onetrust_banner_selector, timeout=10000)
                    print("OneTrust cookie banner found.")

                    # Click the settings button to open preferences
                    await page.click(self.settings_button_selector)

                    # Wait for the settings menu to load
                    await page.wait_for_selector(self.onetrust_settings_menu_selector, timeout=10000)

                    # Extract options and their states
                    available_options = await page.evaluate(f"""
                        () => Array.from(document.querySelectorAll('{self.checkbox_selector}'))
                            .map(element => {{
                                const checkbox = element.previousElementSibling || element.querySelector('input[type="checkbox"]'); // Get the associated checkbox
                                return {{
                                    text: element.innerText.trim() || element.textContent.trim(),
                                    checked: checkbox ? checkbox.checked : false // Check if the checkbox is selected
                                }};
                            }}).filter(item => item.text && item.checked !== undefined);
                    """)
                except TimeoutError:
                    print("OneTrust cookie banner not found. Checking for Cookiebot.")

                    # Check for Cookiebot banner
                    await page.wait_for_selector(self.cookiebot_banner_selector, timeout=10000)
                    print("Cookiebot cookie banner found.")

                    # Extract options and their states
                    available_options = await page.evaluate(f"""
                        () => Array.from(document.querySelectorAll('{self.cookiebot_toggle_selector}'))
                            .map(element => {{
                                const toggle = element.closest("div").querySelector('input[type="checkbox"]');
                                return {{
                                    text: element.textContent.trim(),
                                    checked: toggle ? toggle.checked : false
                                }};
                            }}).filter(item => item.text && item.checked !== undefined);
                    """)

                # Create a dictionary of options and their states
                found_options = {option['text']: option['checked'] for option in available_options}

                # Check which required options are found
                found_required_options = {key: found_options.get(key, "Not Found") for key in self.expected_options}

                # Format feedback
                feedback = "<strong>Options Found and Their Checked Status:</strong><br>"
                for option, status in found_required_options.items():
                    if status == "Not Found":
                        feedback += f"- {option}: Not Found<br>"
                    else:
                        checked_status = "Checked" if status else "Unchecked"
                        feedback += f"- {option}: {checked_status}<br>"

                # Check if all required options are found and not preselected
                if all(found_required_options[key] == False for key in self.expected_options):
                    feedback += "<br><strong>All required cookie options are present and not preselected.</strong>"
                    return True, feedback
                else:
                    feedback += "<br><strong>Not all required cookie options are present or some are preselected.</strong>"
                    return False, feedback

            except TimeoutError:
                print("Error: Timeout while waiting for the cookie banner or settings menu.")
                feedback = (
                    "Timeout occurred while waiting for the cookie banner or settings menu.<br>"
                    "The required options ('Leistungs-Cookies', 'Funktionelle Cookies', "
                    "'Werbe-Cookies', 'Social-Media-Cookies') may not be present on this page."
                )
                return False, feedback
            except Exception as e:
                print(f"Error occurred: {e}")
                return False, f"Error occurred during cookie selection check: {e}"
            finally:
                await context.close()
                await browser.close()


# Example usage
async def main():
    url = "https://www.frankenbrunnen.de/"  # Replace with the target URL
    checker = CookieSelectionChecker()
    result, feedback = await checker.check_cookie_selection(url)
    print("Result:", result)
    print("Feedback:", feedback)


if __name__ == "__main__":
    asyncio.run(main())
