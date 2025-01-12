from playwright.async_api import async_playwright, TimeoutError
import asyncio


class CookieBannerLinkValidator:
    def __init__(self):
        self.common_selectors = [
            'div.sticky',
            'div.hp__sc-yx4ahb-7',
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div',  # Specific selector for Urlaubspiraten cookie banner
            'p.hp__sc-hk8z4-0',
            'button.hp__sc-9mw778-1',
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
            'div[data-borlabs-cookie-consent-required]',
            'div#BorlabsCookieBox',
            'div#BorlabsCookieWidget',
            'div.elementText',
            'h3:has-text("Datenschutzhinweis")',
            '#imprintLinkb',  # Added selector for Imprint link
        ]
        self.privacy_policy_text = "Datenschutzinformationen"
        self.imprint_text = "Impressum"
        self.global_imprint_selector = '#imprintLinkb' # for 1&1
        self.global_privacy_selector = '#privacyPolicyLinkb' # for 1&1

    async def is_visible_cookie_banner(self, page_or_frame):
        """Detect visible cookie banners with size checks."""
        for selector in self.common_selectors:
            elements = await page_or_frame.query_selector_all(selector)
            for element in elements:
                if element and await element.is_visible():
                    box = await element.bounding_box()
                    if box and box['width'] > 300 and box['height'] > 50:
                        return selector
        return None

    async def check_banner_and_links(self, url):
        """Checks for the presence of a cookie banner and validates Privacy Policy and Imprint links."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
            )
            page = await context.new_page()

            try:
                print(f"Visiting URL: {url}")
                # Retry mechanism for page load
                for attempt in range(5):
                    try:
                        await page.goto(url, timeout=60000)
                        await page.wait_for_load_state("networkidle")
                        break
                    except TimeoutError:
                        print(f"Attempt {attempt + 1} failed. Retrying...")
                else:
                    return False, "Page failed to load after multiple attempts."

                # Check for visible cookie banners
                cookie_banner_selector = await self.is_visible_cookie_banner(page)
                if not cookie_banner_selector:
                    # Check iframes for cookie banners
                    iframes = await page.query_selector_all('iframe')
                    for iframe in iframes:
                        iframe_content = await iframe.content_frame()
                        if iframe_content:
                            cookie_banner_selector = await self.is_visible_cookie_banner(iframe_content)
                            if cookie_banner_selector:
                                break

                if not cookie_banner_selector:
                    return False, "No visible cookie banner found."

                print(f"Cookie banner detected using selector: {cookie_banner_selector}")
                cookie_banner = await page.query_selector(cookie_banner_selector)

                # Validate Privacy Policy link inside the cookie banner
                privacy_link = await cookie_banner.query_selector(f'a:has-text("{self.privacy_policy_text}")')
                privacy_found = privacy_clickable = False
                privacy_feedback = ""
                if privacy_link:
                    privacy_found = True
                    if await privacy_link.is_enabled():
                        privacy_clickable = True
                        privacy_url = await privacy_link.get_attribute("href")
                        if privacy_url:
                            privacy_feedback = f"<strong>Privacy Policy URL:</strong> {privacy_url} <strong>clickable:</strong> ✓<br>"
                        else:
                            privacy_feedback = "<strong>Privacy Policy link does not have a valid href attribute.</strong><br>"
                    else:
                        privacy_feedback = "<strong>Privacy Policy link is not clickable.</strong><br>"
                else:
                    privacy_feedback = f"<strong>Privacy Policy link with text '{self.privacy_policy_text}' not found in the cookie banner.</strong><br>"

                # Validate Imprint link inside the cookie banner
                imprint_link = await cookie_banner.query_selector(f'a:has-text("{self.imprint_text}")')
                imprint_found = imprint_clickable = False
                imprint_feedback = ""
                if imprint_link:
                    imprint_found = True
                    if await imprint_link.is_enabled():
                        imprint_clickable = True
                        imprint_url = await imprint_link.get_attribute("href")
                        if imprint_url:
                            imprint_feedback = f"<strong>Imprint URL:</strong> {imprint_url} <strong>clickable:</strong> ✓<br>"
                        else:
                            imprint_feedback = "<strong>Imprint link does not have a valid href attribute.</strong><br>"
                    else:
                        imprint_feedback = "<strong>Imprint link is not clickable.</strong><br>"
                else:
                    imprint_feedback = f"<strong>Imprint link with text '{self.imprint_text}' not found in the cookie banner.</strong><br>"

                # Final validation
                if privacy_found and privacy_clickable and imprint_found and imprint_clickable:
                    return True, f"<strong>Imprint and Privacy Policy links have been found in the cookie banner.</strong><br>{privacy_feedback}{imprint_feedback}"
                else:
                    return False, f"<strong>Validation failed:</strong><br>{privacy_feedback}{imprint_feedback}"

            except TimeoutError:
                return False, "Page load timed out."
            except Exception as e:
                return False, f"An error occurred: {e}"
            finally:
                await context.close()
                await browser.close()


# Example Usage
async def main():
    validator = CookieBannerLinkValidator()
    url = "https://www.urlaubspiraten.de/"  # Replace with the target URL
    result, message = await validator.check_banner_and_links(url)
    print("Result:", result)
    print("Message:", message)


if __name__ == "__main__":
    asyncio.run(main())