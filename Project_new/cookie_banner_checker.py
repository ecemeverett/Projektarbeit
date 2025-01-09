from playwright.sync_api import sync_playwright, TimeoutError
from difflib import SequenceMatcher
from spellchecker import SpellChecker
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from playwright.async_api import async_playwright


class CookieBannerChecker:
    def __init__(self):
        self.common_selectors = [
            'div.sticky',
            'div.hp__sc-yx4ahb-7',
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
        ]
        # Initialize SpellChecker for German
        self.spell_checker = SpellChecker(language='de')
    
    def check_spelling(self, text):
        """
        Check spelling for the given text and return a list of misspelled words with suggestions.
        """
        words = text.split()
        errors = {}

        for word in words:
        # Check if the word is misspelled
            if word not in self.spell_checker:
                # Get suggestions for the misspelled word
                suggestions = list(self.spell_checker.candidates(word))
                errors[word] = suggestions
        
        return errors

    async def check_cookie_banner_visibility(self, url):
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
                try:
                    for selector in self.common_selectors:
                        elements = await page_or_frame.query_selector_all(selector)

                        for element in elements:
                            if element and await element.is_visible():
                                return True, "Cookie banner is visible."
                    return False, f"Error during cookie banner visibility check: {e}"
                except Exception as e:
                    print(f"Error checking visibility in frame: {e}")
                    return False, f"Error during cookie banner visibility check: {e}"     

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
                if await is_visible_cookie_banner(page):
                    print("Cookie banner found in the main document.")
                    return True, "Cookie banner found."

                # Check iframes for cookie banners
                iframes = await page.query_selector_all('iframe')
                for iframe in iframes:
                    iframe_content = await iframe.content_frame()
                    if iframe_content and await is_visible_cookie_banner(iframe_content):
                        print("Cookie banner found in an iframe.")
                        return True, "Cookie banner found in an iframe."

                print("No visible cookie banner found.")
                return False, "No visible cookie banner found."

            except Exception as e:
                return False, f"Error during cookie banner check: {e}"

            finally:
                await context.close()
                await browser.close()
    async def check_ohne_einwilligung_link(self, url):
        """
        Checks for the presence of an 'Ohne Einwilligung' link or button on the given webpage.
        Resolves strict mode violations by handling multiple elements.
        """
        selectors = [
            'button:has-text("Ohne Einwilligung")',
            'a:has-text("Ohne Einwilligung")',
            'button:has-text("Ohne Einwilligung fortfahren")',
            'a:has-text("Ohne Einwilligung fortfahren")'
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Load the page and wait for the cookie banner
                await page.goto(url, timeout=30000)
                print("Page loaded successfully.")

                # Wait for the cookie banner to appear
                cookie_banner_selector = 'div[id^="onetrust-banner"], div[class*="cookie-banner"]'
                await page.wait_for_selector(cookie_banner_selector, timeout=10000)
                print("Cookie banner detected.")

                # Iterate through selectors to find the "Ohne Einwilligung" button/link
                for selector in selectors:
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
                return False, "Timeout while waiting for the 'Ohne Einwilligung' button."
            except Exception as e:
                print(f"General error occurred: {e}")
                return False, f"Error during check: {e}"
            finally:
                await context.close()
                await browser.close()
    
    async def check_cookie_selection(self, url):
        """
        Asynchronously checks for required cookie categories in the OneTrust banner
        and verifies that they are not preselected.
        """
        expected_options = [
            "Leistungs-Cookies",
            "Funktionelle Cookies",
            "Werbe-Cookies",
            "Social-Media-Cookies",
        ]

        async with async_playwright() as p:
            browser =  await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page =  await browser.new_page()

            try:
                # Load the page and wait for the OneTrust banner to appear
                await page.goto(url, timeout=30000)
                print("Page loaded successfully.")

                banner_selector = "#onetrust-banner-sdk"
                await page.wait_for_selector(banner_selector, timeout=20000)
                print("OneTrust cookie banner found.")

                # Click the settings button to open preferences
                settings_button_selector = "button#onetrust-pc-btn-handler"
                await page.click(settings_button_selector)

                # Wait for the settings menu to load
                settings_menu_selector = "#onetrust-pc-sdk"
                await page.wait_for_selector(settings_menu_selector, timeout=10000)

                # Use JavaScript to extract all visible label text and check if toggles are selected
                available_options =  await page.evaluate("""
                    () => Array.from(document.querySelectorAll(
                        'input[type="checkbox"] + label, div.ot-checkbox-label span, div.ot-checkbox-label'
                    )).map(element => {
                        const checkbox = element.previousElementSibling; // Get the associated checkbox
                        return {
                            text: element.innerText || element.textContent,
                            checked: checkbox ? checkbox.checked : false // Check if the checkbox is selected
                        };
                    }).filter(item => item.text.trim() && item.checked !== undefined);
                """)

                # Create a dictionary for easy access
                option_status = {option['text'].strip(): option['checked'] for option in available_options}

                # Filter options based on expected categories
                filtered_options = {key: option_status[key] for key in expected_options if key in option_status}

                print("Available options with checked status:", filtered_options)

                # Check if all required options are present and not preselected
                if len(filtered_options) == len(expected_options) and all(
                    not filtered_options[option] for option in expected_options
                ):
                    print("All required cookie options are present and none are preselected.")
                    return True, "All required cookie options are present and none are preselected."
                else:
                    print("Some required cookie options are missing or some are preselected.")
                    return False, "Some required cookie options are missing or some are preselected."

            except TimeoutError:
                print("Error: Timeout while waiting for the cookie banner or settings menu.")
                return False, "Timeout while waiting for the cookie banner or settings menu."
            except Exception as e:
                print(f"Error occurred: {e}")
                return False, f"Error occurred during cookie selection check: {e}"
            finally:
                await context.close()
                await browser.close()
    
    async def extract_cookie_banner_text(self, url):
        """
        Extracts the text content of the cookie banner on the given webpage.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(url, timeout=30000)
                print("Page loaded successfully.")

                for selector in self.common_selectors:
                    try:
                        elements =  page.locator(selector)
                        count = await elements.count()
                        
                        if count == 0:
                            continue
                        
                        # Iterate over all matching elements
                        for i in range(count):
                            element = elements.nth(i)
                            if await element.is_visible():
                                full_text = await element.inner_text()
                                print(f"Text extracted from selector {selector}, Element {i+1}: {full_text[:200]}...")
                                # Define start and end phrases for extracting the main text
                                start_phrase = "Auf unserer Webseite verwenden wir Cookies"
                                end_phrase = "Weitere Informationen enthalten unsere Datenschutzinformationen."

                                # Use regex to extract the main text
                                pattern = re.escape(start_phrase) + r"(.*?)" + re.escape(end_phrase)
                                match = re.search(pattern, full_text, re.DOTALL)

                                if match:
                                    main_text = match.group(0).strip()  # Extract only the desired part
                                    print(f"Full extracted text: {main_text}")  # Debugging print
                                    return main_text
                    except Exception as e:
                        print(f"Error with selector {selector}: {e}")
                        continue
                return "Cookie banner not found using any common selectors."
            except Exception as e:
                return f"Error extracting cookie banner text: {str(e)}"
            finally:
                await context.close()
                await browser.close()
    
    # Since this method is not interacting with any external asynchronous components,
    # it doesn't need to be changed to an async method.
    def compare_cookie_banner_text(self, website_text, template_text):
        """
        Compares the cookie banner text from the website to a given template.
        """
       # Calculate similarity
        similarity = SequenceMatcher(None, template_text, website_text).ratio() * 100


        # Spell-check the website text
        spelling_errors = self.check_spelling(website_text)

        # Prepare feedback with bold formatting
        feedback = f"""
        <strong>Template Text:</strong><br>
        <b>{template_text}</b><br><br>
        <strong>Website Text:</strong><br>
        <b>{website_text}</b><br><br>
        <strong>Similarity:</strong><br>
        <b>{similarity:.2f}%</b><br><br>
        """
        if spelling_errors:
            feedback += "<strong>Spelling mistakes in website text:</strong><br>"
            for word, suggestions in spelling_errors.items():
                feedback += f"- <b>{word}</b>: Suggestions: {', '.join(suggestions)}<br>"


        is_conformant = similarity == 100 and not spelling_errors
        return is_conformant, similarity, feedback
    
    async def check_cookie_banner(self, url, template_text):
        """
        Extract cookie banner text from a website and compare it with the template text.
        :param url: URL of the website to check.
        :param template_text: Template text to compare against.
        :return: A tuple containing conformity, similarity, and feedback.
        """
        try:
            website_text = await self.extract_cookie_banner_text(url)
            if not website_text or "Error" in website_text:
                return False, 0, "Error or no cookie banner text found on the website."

            # Compare texts
            is_conformant, similarity, feedback = self.compare_cookie_banner_text(website_text, template_text)

            return is_conformant, similarity, feedback

        except Exception as e:
            return False, 0, f"Error during cookie banner text check: {str(e)}"
