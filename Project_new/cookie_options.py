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
        self.banner_selector = "#onetrust-banner-sdk"
        self.settings_button_selector = "button#onetrust-pc-btn-handler"
        self.settings_menu_selector = "#onetrust-pc-sdk"
        self.checkbox_selector = (
            "input[type=\"checkbox\"] + label, div.ot-checkbox-label span, div.ot-checkbox-label"
        )

    async def check_cookie_selection(self, url):
        """
        Checks for required cookie categories in the OneTrust banner
        and verifies that they are not preselected.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Load the page and wait for the OneTrust banner to appear
                await page.goto(url, timeout=30000)
                print("Page loaded successfully.")

                await page.wait_for_selector(self.banner_selector, timeout=20000)
                print("OneTrust cookie banner found.")

                # Click the settings button to open preferences
                await page.click(self.settings_button_selector)

                # Wait for the settings menu to load
                await page.wait_for_selector(self.settings_menu_selector, timeout=10000)

                # Extract all visible label text and check if toggles are selected
                available_options = await page.evaluate(f"""
                    () => Array.from(document.querySelectorAll('{self.checkbox_selector}'))
                        .map(element => {{
                            const checkbox = element.previousElementSibling; // Get the associated checkbox
                            return {{
                                text: element.innerText || element.textContent,
                                checked: checkbox ? checkbox.checked : false // Check if the checkbox is selected
                            }};
                        }})
                        .filter(item => item.text.trim() && item.checked !== undefined);
                """)

                # Create a dictionary for easy access
                option_status = {option['text'].strip(): option['checked'] for option in available_options}

                # Filter options based on expected categories
                filtered_options = {key: option_status.get(key, None) for key in self.expected_options}

                # Format feedback
                feedback = "<strong>Available options with checked status:</strong><br>"
                for option, checked in filtered_options.items():
                    status = "Checked" if checked else "Unchecked"
                    feedback += f"- {option}: {status}<br>"


                # Check if all required options are present and not preselected
                if len(filtered_options) == len(self.expected_options) and all(
                    not checked for checked in filtered_options.values()
                ):
                    feedback += "<br><strong>All required cookie options are present and none are preselected.</strong>"
                    return True, feedback
                
                else:
                    feedback += "<br><strong>Some required cookie options are missing or some are preselected.</strong>"
                    return False, feedback

            except TimeoutError:
                print("Error: Timeout while waiting for the cookie banner or settings menu.")
                return False, "Timeout while waiting for the cookie banner or settings menu."
            except Exception as e:
                print(f"Error occurred: {e}")
                return False, f"Error occurred during cookie selection check: {e}"
            finally:
                await context.close()
                await browser.close()


# Example usage
async def main():
    url = "https://www.loreal-paris.de/"
    checker = CookieSelectionChecker()
    result, feedback = await checker.check_cookie_selection(url)
    print("Result:", result)
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())
