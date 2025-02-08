from playwright.async_api import async_playwright, TimeoutError
import asyncio


class ScrollbarChecker:
    def __init__(self):
        self.common_selectors = [
            # 🔹 Allgemeine Cookie-Banner Selektoren (höchste Priorität für breite Abdeckung)
            'div[class*="cookie"]', # Santander, Gemeinde Wasserburg, VDZ
            'div[class*="consent"]', # Veri veri verivox :), 1&1 , Kneip
            'div[class*="cookie-banner"]',
            'div.cc-banner',
            'section.consentDrawer', # BMW Group
            
            # 🔹 OneTrust und ähnliche Frameworks
            'div.ot-cat-lst',  # Scrollbare Liste innerhalb des OneTrust Banners (Loreal)
            'div.ot-scrollbar',  # Scrollbare Bereiche in OneTrust
            '#onetrust-banner-sdk',  # Hauptcontainer OneTrust (Loreal, Henkel, Kao, Weleda, Schwarzkopf, Wagner, just spices, royal canin, Gardena, Husqvarna, Kärcher, Saint-Gobain, aldi, aldi süd)
            '#onetrust-banner-sdk > div > div.ot-sdk-container.ot-scrollbar',
            
            # 🔹 Webseite-spezifische Selektoren (niedrigere Priorität)
            '#cmpboxcontent',  # Beiersdorf, tesa, Huber Burda Media
            '#CybotCookiebotDialog',  # Franken Brunnen, brandt-zwieback, weber, tetesept, ivoclar vivadent, Landesanstalt für Medien nrw
            '#page-id-46 > div.l-module.p-privacy-settings.t-ui-light.is-visible > div > div > div',  # Griesson
            '#uc-main-dialog', # Dr. Oetker
            '[data-testid="uc-default-banner"]',  # Hochland, coa
            '#popin_tc_privacy', # danone
            '#privacydialog\\:desc',   # Hassia scrollbar
            'body > div.cookie-layer-advanced.state-visible', # Hansgrohe
            '#uc-center-container', # blanco
            '#cookie-law-info-bar', # Vendis capital
            '#cookiescript_injected', # radbag (it has hidden checkboxs)
            '#ccm-widget > div', # Merz, ding 
            'div.brlbs-cmpnt-container', # Ehiner-Energie
            'h3:has-text("Datenschutzhinweis")', # SWHN
            'body > div > div > div.om-cookie-panel.active', # CAU
           
            # 🔹 Urlaubspiraten spezifische Selektoren
            'div.hp__sc-yx4ahb-7',
            'p.hp__sc-iv4use-0',
            '#hp-app > div.hp__sc-s043ov-0.eTEUOO > div', # Urlaubspiraten
            'p.hp__sc-hk8z4-0',
            'button.hp__sc-9mw778-1'
        ]

    async def is_scrollable(self, page, element):
        """
        Check if the given element is scrollable and whether its scrollbar is visible.
        """
        try:
            if not element:
                return False, "Element not found."

            # Get computed styles
            visibility = await page.evaluate("(el) => window.getComputedStyle(el).visibility", element)
            display = await page.evaluate("(el) => window.getComputedStyle(el).display", element)
            overflow_y = await page.evaluate("(el) => window.getComputedStyle(el).overflowY", element)

            # If the element is hidden, skip it
            if visibility == "hidden" or display == "none":
                return False, "Element is hidden, skipping."

            # Evaluate scrollability more accurately
            scroll_height = await page.evaluate("(el) => el.scrollHeight", element)
            client_height = await page.evaluate("(el) => el.clientHeight", element)
            offset_height = await page.evaluate("(el) => el.offsetHeight", element)

            is_scrollable = scroll_height > client_height and overflow_y in ["scroll", "auto"]

            # Check if the scrollbar is intentionally hidden via CSS
            scrollbar_hidden = await page.evaluate("""
                (el) => {
                    const computedStyle = window.getComputedStyle(el, '::-webkit-scrollbar');
                    return computedStyle && computedStyle.display === 'none';
                }
            """, element)

            debug_info = (
                f"Scrollable: {is_scrollable}, OverflowY: {overflow_y}, "
                f"scrollHeight: {scroll_height}, clientHeight: {client_height}, offsetHeight: {offset_height}, "
                f"Scrollbar Hidden: {scrollbar_hidden}"
            )

            if is_scrollable and scrollbar_hidden:
                return False, f"Not Conform: Scrollbar is required but hidden via CSS. {debug_info}"

            return is_scrollable, debug_info

        except Exception as e:
            return False, f"Error during scrollbar check: {str(e)}"

    async def check_overflow(self, page, element):
        """
        Check if any child elements inside the cookie banner overflow.
        """
        try:
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

            return children_overflow, f"Child elements overflow: {children_overflow}"
        except Exception as e:
            return False, f"Error checking overflow: {str(e)}"

    async def check_cookie_banner_with_scrollbar(self, url):
        """
        Check if the cookie banner has overflowing elements and whether it has a scrollbar.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                print(f"Navigating to {url}...")
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle")

                for selector in self.common_selectors:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        print(f"Cookie banner detected with selector: {selector}")

                        # Check if any elements inside the banner overflow
                        children_overflow, overflow_feedback = await self.check_overflow(page, element)

                        # Check if the parent has a scrollbar
                        parent_scrollable, parent_feedback = await self.is_scrollable(page, element)

                        # Debugging output
                        print(f"🔍 Overflow Check: {overflow_feedback}")
                        print(f"🔍 Parent Scrollbar Check: {parent_feedback}")

                        # **Rules for Conformity**
                        if children_overflow and not parent_scrollable:
                            return False, f"Not Conform: Overflow detected but no scrollbar available. {parent_feedback}"
                        elif children_overflow and parent_scrollable:
                            return True, f"Conform: Overflow detected and scrollbar is present."
                        elif not children_overflow and parent_scrollable:
                            return False, f"Not Conform: No overflow, but scrollbar is unnecessarily present. {parent_feedback}"
                        else:
                            return True, "Conform: No overflow, no scrollbar needed."

                return False, "No visible cookie banner found."
            except TimeoutError:
                return False, "Page load timeout."
            except Exception as e:
                return False, f"Error: {str(e)}"
            finally:
                await browser.close()

"""
# Example Usage
async def main():
    url = "https://www.medienanstalt-nrw.de/"
    checker = ScrollbarChecker()
    is_conform, feedback = await checker.check_cookie_banner_with_scrollbar(url)
    print("Conform:", is_conform)
    print("Feedback:", feedback)


if __name__ == "__main__":
    asyncio.run(main())
"""