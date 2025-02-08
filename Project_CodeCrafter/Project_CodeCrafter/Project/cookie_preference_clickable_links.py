from playwright.async_api import async_playwright, TimeoutError
import asyncio
from langdetect import detect


class CookiePreferenceLinkValidator:
    def __init__(self):
        # Comprehensive list of cookie banner selectors
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
            '#uc-main-dialog',  # Specific selector for Dr. Oetker cookie banner
        ]

        # Comprehensive list of preference center selectors
        self.preference_center_selectors = [
            'div[class*="preference-center"]',
            'div[class*="consent-manager"]',
            '[role="dialog"]',
        ]

        # Button texts for opening the preference center
        self.preference_button_texts = ["Cookie-Einstellungen", "Cookie Options", "Manage Cookies", "Einstellungen"]

        # Privacy and Imprint link text
        self.imprint_texts = ["Impressum", "Imprint"]
        self.privacy_policy_texts = ["Datenschutzinformationen", "Privacy Policy"]

    async def is_visible_cookie_banner(self, page_or_frame):
        """Detect visible cookie banners with size checks."""
        for selector in self.common_selectors:
            elements = await page_or_frame.query_selector_all(selector)
            for element in elements:
                if element and await element.is_visible():
                    box = await element.bounding_box()
                    if box and box['width'] > 300 and box['height'] > 50:  # Basic size check
                        return selector
        return None

    async def validate_links(self, element, texts):
        """Helper function to validate links for specific texts."""
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
                        feedback += f"<strong>{text} URL:</strong> {url} <strong>clickable:</strong> ✓<br>"
                    else:
                        feedback += f"<strong>{text} link does not have a valid href attribute.</strong><br>"
                else:
                    feedback += f"<strong>{text} link is not clickable.</strong><br>"
            else:
                feedback += f"<strong>{text} link not found.</strong><br>"
        return found, clickable, feedback

    async def check_iframes(self, page, validation_function, *args):
        """Check all iframes for the presence of banners or preference centers."""
        iframes = await page.query_selector_all('iframe')
        for iframe in iframes:
            iframe_content = await iframe.content_frame()
            if iframe_content:
                result = await validation_function(iframe_content, *args)
                if result:
                    return result
        return None

    async def check_cookie_preference_center(self, page):
        """Validate links in the Cookie Preference Center."""
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
        """Checks for the presence of a cookie banner and validates Privacy Policy and Imprint links."""
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
                detected_language = detect(banner_text)
                privacy_texts = self.privacy_policy_texts if detected_language != "de" else ["Datenschutzinformationen"]
                imprint_texts = self.imprint_texts if detected_language != "de" else ["Impressum"]

                # Click "Cookie-Einstellungen" or "Cookie Options" button if available
                preference_button = await cookie_banner.query_selector(
                    f'button:has-text("{self.preference_button_texts[0]}"), button:has-text("{self.preference_button_texts[1]}")'
                )
                if preference_button:
                    await preference_button.click()
                    await page.wait_for_timeout(2000)  # Wait for preference center to load

                    # Check for cookie preference center on the main page or in iframes
                    valid, feedback = await self.check_cookie_preference_center(page)
                    iframe_result = await self.check_iframes(page, self.check_cookie_preference_center)
                    if not valid and iframe_result:
                        valid, feedback = iframe_result

                    if valid:
                        return True, f"<strong>Validation passed:</strong><br>{feedback}"
                    else:
                        return False, f"<strong>Validation failed:</strong><br>{feedback}"

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
# Example usage
async def main():
    validator = CookiePreferenceLinkValidator()
    url = "https://www.loreal-paris.de/"  # Replace with your target URL
    result, message = await validator.check_preference_links(url)
    print("Result:", result)
    print("Message:", message)


if __name__ == "__main__":
    asyncio.run(main())
"""