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

    def check_cookie_banner_visibility(self, url):
        """
        Checks if a visible cookie or consent banner is present on the given webpage.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(url, timeout=30000)
                print("Page loaded successfully.")

                for selector in self.common_selectors:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        print(f"Cookie banner found using selector: {selector}")
                        return True, f"Cookie banner found with selector: {selector}"

                return False, "No visible cookie banner found."

            except TimeoutError:
                return False, "Page load timeout."
            except Exception as e:
                return False, f"Error during cookie banner visibility check: {e}"
            finally:
                browser.close()
    def check_ohne_einwilligung_link(self, url):
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

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                # Load the page and wait for the cookie banner
                page.goto(url, timeout=30000)
                print("Page loaded successfully.")

                # Wait for the cookie banner to appear
                cookie_banner_selector = 'div[id^="onetrust-banner"], div[class*="cookie-banner"]'
                page.wait_for_selector(cookie_banner_selector, timeout=10000)
                print("Cookie banner detected.")

                # Iterate through selectors to find the "Ohne Einwilligung" button/link
                for selector in selectors:
                    elements = page.locator(selector)
                    count = elements.count()

                    if count == 0:
                        continue  # No elements for this selector, move to the next

                    for i in range(count):
                        element = elements.nth(i)
                        if element.is_visible() and element.is_enabled():
                            location = element.evaluate(
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
                browser.close()  # Ensure the browser is closed
    def check_cookie_selection(self, url):
        """
        Checks for required cookie categories in the OneTrust banner and verifies that they are not preselected.
        """
        expected_options = [
        "Leistungs-Cookies",
        "Funktionelle Cookies",
        "Werbe-Cookies",
        "Social-Media-Cookies",
        ]

        options = Options()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')  # Bypass OS security model
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        try:
            driver.get(url)

            # Wait for the OneTrust banner to appear
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "onetrust-banner-sdk"))
            )
            print("OneTrust cookie banner found.")

            # Click the settings button to open preferences
            settings_button = driver.find_element(By.CSS_SELECTOR, 'button#onetrust-pc-btn-handler')
            settings_button.click()

            # Wait for the settings menu to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "onetrust-pc-sdk"))
            )

            # Use JavaScript to extract all visible label text and check if toggles are selected
            script = """
                return Array.from(document.querySelectorAll(
                    'input[type="checkbox"] + label, div.ot-checkbox-label span, div.ot-checkbox-label'
                )).map(element => {
                    const checkbox = element.previousElementSibling; // Get the associated checkbox
                    return {
                        text: element.innerText || element.textContent,
                        checked: checkbox ? checkbox.checked : false // Check if the checkbox is selected
                    };
                }).filter(item => item.text.trim() && item.checked !== undefined);
            """
            available_options = driver.execute_script(script)

            # Create a dictionary for easy access
            option_status = {option['text'].strip(): option['checked'] for option in available_options}

            # Filter options based on expected categories
            available_options = {key: option_status[key] for key in expected_options if key in option_status}

            print("Available options with checked status:", available_options)

            # Check if all required options are present and not preselected
            if len(available_options) == 4 and all(not available_options[option] for option in expected_options):
                print("All required cookie options are present and none are preselected.")
                return True, "All required cookie options are present and none are preselected."
            else:
                print("Some required cookie options are missing or some are preselected.")
                return False, "Some required cookie options are missing or some are preselected."

        except Exception as e:
            print(f"Error: {e}")
            return False, f"Error occurred during cookie selection check: {e}"

        finally:
            driver.quit()  # Ensure the browser is closed

    def extract_cookie_banner_text(self, url):
        """
        Extracts the text content of the cookie banner on the given webpage.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(url, timeout=30000)

                for selector in self.common_selectors:
                    try:
                        element = page.locator(selector)
                        if element.is_visible():
                            full_text = element.inner_text().strip()

                        # Define start and end phrases for extracting the main text
                        start_phrase = "Auf unserer Webseite verwenden wir Cookies"
                        end_phrase = "Weitere Informationen enthalten unsere Datenschutzinformationen."

                        # Use regex to extract the main text
                        pattern = re.escape(start_phrase) + r"(.*?)" + re.escape(end_phrase)
                        match = re.search(pattern, full_text, re.DOTALL)

                        if match:
                            main_text = match.group(0).strip()  # Extract only the desired part
                            return main_text
                    except Exception:
                        # Continue to the next selector if an error occurs
                        continue
                return "Cookie banner not found using any common selectors."
            except Exception as e:
                return f"Error extracting cookie banner text: {str(e)}"

            finally:
                browser.close()
    

    def compare_cookie_banner_text(self, website_text, template_text):
        """
        Compares the cookie banner text from the website to a given template.
        """
        similarity = SequenceMatcher(None, template_text, website_text).ratio() * 100

        spell_checker = SpellChecker()
        website_words = set(website_text.split())
        template_words = set(template_text.split())
        spelling_mistakes = spell_checker.unknown(website_words - template_words)

         # Prepare feedback with bold formatting
        feedback = f"""
        <strong>Template Text:</strong><br>
        <b>{template_text}</b><br><br>
        <strong>Website Text:</strong><br>
        <b>{website_text}</b><br><br>
        <strong>Similarity:</strong><br>
        <b>{similarity:.2f}%</b><br><br>
        """
        if spelling_mistakes:
            feedback += "Spelling mistakes in website text:\n" + "\n".join(f"- {word}" for word in spelling_mistakes)

        is_conformant = similarity == 100 and not spelling_mistakes
        return is_conformant, similarity, feedback