
import asyncio
from playwright.async_api import async_playwright, TimeoutError


class CookieBannerVis:
    def __init__(self):
        self.common_selectors = [
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
            'h3:has-text("Datenschutzhinweis")',  # Check for the header text'
        ]
   
    
    async def check_visibility(self, url):
        """
        Checks if a visible cookie or consent banner is present on the given webpage.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
            )
            page = await context.new_page()

            async def is_visible_cookie_banner(page_or_frame):
                """Check for visible cookie banners in the given page or frame."""
                found_banners = []  # Store found banners for debugging
                for selector in self.common_selectors:
                    elements = await page_or_frame.query_selector_all(selector)
                    for element in elements:
                        if element and await element.is_visible():
                            box = await element.bounding_box()
                            # Check minimum dimensions for the banner
                            if box and box['width'] > 300 and box['height'] > 50:
                                # Get the text content of the element
                                element_text = (await element.evaluate("el => el.textContent")).lower() or ""
                                found_banners.append({
                                    'selector': selector,
                                    'text': element_text,
                                    'bounding_box': box,
                                })

                # Debugging output for detected banners
                for banner in found_banners:
                    print(f"Found banner with selector: '{banner['selector']}'")
                    print(f"Element text: '{banner['text']}'")
                    print(f"Element bounding box: {banner['bounding_box']}")

                # Check for keywords in the page content
                keywords = ["cookie", "consent", "gdpr", "privacy", "tracking", "preferences"]
                for banner in found_banners:
                    if any(keyword in banner['text'] for keyword in keywords):
                        return True, f"Cookie banner detected."

                return False, "No relevant cookie banner detected."

            try:
                # Load the page with retries
                for attempt in range(5):
                    try:
                        print(f"Attempting to load the page (Attempt {attempt + 1})...")
                        await page.goto(url, timeout=60000)
                        await page.wait_for_load_state('networkidle')
                        print("Page loaded successfully.")
                        break
                    except TimeoutError:
                        print(f"Attempt {attempt + 1} failed. Retrying...")
                else:
                    return False, "Page failed to load after multiple attempts."

                # Check for visible cookie banners
                result, message = await is_visible_cookie_banner(page)
                if result:
                    print("Cookie banner found in the main document.")
                    return True, message

                # Check iframes for cookie banners
                iframes = await page.query_selector_all('iframe')
                for iframe in iframes:
                    iframe_content = await iframe.content_frame()
                    if iframe_content:
                        result, message = await is_visible_cookie_banner(iframe_content)
                        if result:
                            print("Cookie banner found in an iframe.")
                            return True, message

                print("No visible cookie banner found.")
                return False, "No visible cookie banner found."

            except Exception as e:
                return False, f"Error during cookie banner check: {e}"

            finally:
                await context.close()
                await browser.close()
async def main():
    url = "https://www.urlaubspiraten.de/"
    checker = CookieBannerVis()
    result, message = await checker.check_visibility(url)
    print("Result:", result)
    print("Message:", message)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
    
