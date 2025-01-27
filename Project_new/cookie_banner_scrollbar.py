from playwright.async_api import async_playwright, TimeoutError
import asyncio


class ScrollbarChecker:
    def __init__(self):
        self.common_selectors = [
            'div.sticky',  # The main sticky container of the cookie banner
            #'div#onetrust-banner-sdk',  # Main cookie banner container
            'div.ot-cat-lst',  # Scrollable category list inside the cookie banner
            'div.ot-scrollbar',  # Specific class for scrollable areas
            'div.hp__sc-yx4ahb-7',  # Urlaubspiraten main container
            'p.hp__sc-iv4use-0',  # Urlaubspiraten specific paragraph
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div',  # Specific selector for Urlaubspiraten cookie banner
            'div.hp__sc-yx4ahb-7',  # Main container for the cookie banner on Urlaubspiraten
            'p.hp__sc-hk8z4-0',  # Paragraphs containing cookie consent text
            'button.hp__sc-9mw778-1',  # Buttons for actions
            '#cookieboxBackgroundModal > div',  # Specific selector for the cookie banner on Santander
            '[data-testid="uc-default-banner"]',  # Selector for Zalando cookie banner
            '#onetrust-banner-sdk > div > div.ot-sdk-container.ot-scrollbar',  # Selector for OneTrust banner
            # Additional common selectors
            'div.cc-banner',
            'section.consentDrawer',
            'div[class*="cookie"]',
            'div[class*="consent"]',
            'div[id*="banner"]',
            'div[class*="cookie-banner"]',
        ]

    async def is_scrollable(self, page, element):
        """
        Check if the given element is scrollable and if its child elements overflow.
        """
        try:
            if not element:
                return False, "Element not found."

            # Evaluate the scrollability and scrollbar visibility
            scroll_height = await page.evaluate("(el) => el.scrollHeight", element)
            client_height = await page.evaluate("(el) => el.clientHeight", element)
            overflow_y = await page.evaluate("(el) => window.getComputedStyle(el).overflowY", element)

            is_scrollable = scroll_height > client_height and overflow_y in ["scroll", "auto"]

            # Check if any child elements overflow
            children_overflow = await page.evaluate("""
                (el) => {
                    const children = el.querySelectorAll("*");
                    for (const child of children) {
                        const childRect = child.getBoundingClientRect();
                        const parentRect = el.getBoundingClientRect();
                        if (
                            childRect.bottom > parentRect.bottom ||
                            childRect.right > parentRect.right
                        ) {
                            return true;
                        }
                    }
                    return false;
                }
            """, element)

            # Determine conformity
            if children_overflow and is_scrollable:
                feedback = "Conform: Overflow detected and scrollbar is present."
            elif not children_overflow:
                feedback = "Conform: No overflow, no scrollbar needed."
            elif children_overflow and not is_scrollable:
                feedback = "Not Conform: Overflow detected but no scrollbar."
            else:
                feedback = "Not Conform: Scrollbar present unnecessarily."

            return is_scrollable or children_overflow, feedback
        except Exception as e:
            return False, f"Error during scrollbar check: {str(e)}"

    async def check_cookie_banner_with_scrollbar(self, url):
        """
        Check for a visible cookie banner and evaluate if it or its nested sections are scrollable.

        Args:
            url: URL of the webpage to check.

        Returns:
            A tuple (is_conform, feedback) where:
                - is_conform (bool): True if the banner is conform, False otherwise.
                - feedback (str): Feedback message for reporting.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                print(f"Navigating to {url}...")
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state("networkidle")

                for selector in self.common_selectors:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        print(f"Cookie banner detected with selector: {selector}")

                        # Check the parent cookie banner for scrollability and overflow
                        parent_scrollable, parent_feedback = await self.is_scrollable(page, element)
                        if parent_scrollable:
                            return True, parent_feedback  # Parent handles all overflow (Conform)

                        # If parent is not scrollable, check nested sections for overflow and scrollability
                        nested_elements = await element.query_selector_all("*")
                        for idx, nested in enumerate(nested_elements):
                            nested_scrollable, nested_feedback = await self.is_scrollable(page, nested)
                            if not nested_scrollable:
                                return False, f"Not Conform: Overflow in nested element at index {idx}. {nested_feedback}"

                        # If all nested elements are handled properly
                        return True, "Conform: All overflow handled with scrollbars."

                return False, "No visible cookie banner found."
            except TimeoutError:
                return False, "Page load timeout."
            except Exception as e:
                return False, f"Error: {str(e)}"
            finally:
                await browser.close()


# Example Usage
async def main():
    url = "https://www.loreal-paris.de/"
    checker = ScrollbarChecker()
    is_conform, feedback = await checker.check_cookie_banner_with_scrollbar(url)
    print("Conform:", is_conform)
    print("Feedback:", feedback)


if __name__ == "__main__":
    asyncio.run(main())