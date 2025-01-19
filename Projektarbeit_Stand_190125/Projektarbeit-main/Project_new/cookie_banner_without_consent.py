from playwright.async_api import async_playwright, TimeoutError
import asyncio

class WithoutConsentChecker:
    def __init__(self):
        self.selectors = [
            'button:has-text("Ohne Einwilligung")',
            'a:has-text("Ohne Einwilligung")',
            'button:has-text("Ohne Einwilligung fortfahren")',
            'a:has-text("Ohne Einwilligung fortfahren")'
        ]
        self.cookie_banner_selector = ', '.join([
            'div.sticky',
            'div.hp__sc-yx4ahb-7',
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div',  # Specific selector for Urlaubspiraten cookie banner
            'p.hp__sc-hk8z4-0',
            'button.hp__sc-9mw778-1',
            'div.cmp-container',
            'div.ccm-modal-inner',
            '#cookiescript_injected',  # redbag cookie banner
            "#cookiescript_injected > div.cookiescript_pre_header", # redbag
            "button:has-text('Ohne Einwilligung')",
            "a:has-text('Ohne Einwilligung')",
            "div[class*='cookie'] button",
            "div[class*='consent'] button",
            "div[class*='cookie-banner'] button",
            "div[class*='cookie'] a",
            "div[class*='cookie-banner'] a",
            "button#onetrust-reject-all-handler",
            "button[data-cookiebanner='reject']",
            "div[style*='position: absolute'][style*='right'] button:has-text('Ohne Einwilligung')",
            "div[style*='position: absolute'][style*='right'] a:has-text('Ohne Einwilligung')",
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
        ])
    async def check_ohne_einwilligung_link(self, url):
        """
        Checks for the presence of an 'Ohne Einwilligung' link or button on the given webpage.
        Resolves strict mode violations by handling multiple elements.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Load the page and wait for the cookie banner
                await page.goto(url, timeout=30000)
                print("Page loaded successfully.")

                # Wait for the cookie banner to appear
                await page.wait_for_selector(self.cookie_banner_selector, timeout=10000)
                print("Cookie banner detected.")

                # Iterate through selectors to find the "Ohne Einwilligung" button/link
                for selector in self.selectors:
                    elements = page.locator(selector)
                    count = await elements.count()

                    if count == 0:
                        continue  # No elements for this selector, move to the next

                    for i in range(count):
                        element = elements.nth(i)
                        if await element.is_visible() and await element.is_enabled():
                            location = await element.evaluate(
                                """el => ({
                                    top: el.getBoundingClientRect().top,
                                    left: el.getBoundingClientRect().left,
                                    width: el.getBoundingClientRect().width,
                                    height: el.getBoundingClientRect().height
                                })"""
                            )
                            feedback = (
                                f"'Ohne Einwilligung' link found and clickable. "
                                f"Location: top={location['top']}, left={location['left']}, "
                                f"width={location['width']}, height={location['height']}."
                            )
                            print(feedback)
                            return True, feedback

                        # Log multiple matches if none were usable
                        print(f"Multiple elements found for selector: {selector}, but none were clickable.")

                # If no matching element is found
                print("No clickable 'Ohne Einwilligung' link or button found.")
                return False, "No clickable 'Ohne Einwilligung' link or button found."

            except TimeoutError:
                print("Error: Timeout while loading the page.")
                return False, "Timeout while waiting for the 'Ohne Einwilligung' button. It is likely that the expected 'Ohne Einwilligung' button are not present on this page."

            except Exception as e:
                print(f"General error occurred: {e}")
                return False, f"Error during check: {e}"
            finally:
                await context.close()
                await browser.close()


# Example usage
async def main():
    url = "https://www.radbag.de/geschenkideen?gad_source=1&gclid=CjwKCAiA7Y28BhAnEiwAAdOJUIMPS-nQfDYq4DEyL8NUiy40hAQAwuqU6eDvKu4BI5CCtBJ7lnkg5BoCgR8QAvD_BwE"
    checker = WithoutConsentChecker()
    result, feedback = await checker.check_ohne_einwilligung_link(url)
    print("Result:", result)
    print("Feedback:", feedback)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
    
