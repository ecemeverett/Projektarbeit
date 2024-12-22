from flask import Flask, render_template, request, redirect, url_for, session, send_file
import requests
from bs4 import BeautifulSoup
import io
from xhtml2pdf import pisa
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import re
from difflib import SequenceMatcher
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Default templates
DEFAULT_TEMPLATES = {
    'impressum': "Default Impressum text...",
    'datenschutz': "Default Datenschutz text...",
    'cookie_policy': "Default Cookie Policy text...",
    'newsletter' : "Default Newsletter text..."
}

# IMPORTANT !
# In order to check a criteria, you should add the name and the function of the criteria into this dictionary.
# The function, that checks the criteria has to return False or True. Otherwise the dictionary won't get initialized correctly.
CRITERIA = {
    "Cookie Banner Visibility": "Check if the cookie banner is visible.",
    "Ohne Einwilligung Link": "Check for the presence of 'Ohne Einwilligung' link.",
    "Cookie Selection": "Check if all cookie options are available.",
    "Clear CTA": "CTA must be recognizable and has to have a clear wording" ,
    "Age Limitation": "Check if the age limit is 18",
    "Newsletter wording": "Check if the wording of the newsletter is correct"
    """ "Correct Text": "Check if the text in the cookie banner is correct.",
    "Scrollbar": "Check if the banner has a scrollbar if it needs one.",
    "Links to Imprint and Privacy Policy": "Check links to Impressum and Datenschutzinformationen.",
    "Conform Design": "Check if the design conforms to the requirements.",
    "Button Size and Height": "Check if buttons are appropriately sized and aligned.",
    "Font Size": "Check if the font size is readable.",
    "Mobile Compatibility": "Check if the site is mobile-compatible.",
    "More Information Click": "Check for clickable 'More information' links.",
    "Cookie Lifetime": "Check cookie lifetime information.",
    "Clickable Datenschutzinformation": "Check if the Datenschutzinformation link is clickable.",
    "Cookie Description": "Check if every cookie has a description.",
    "No Unknown Cookies": "Check that there are no unknown cookies." 
    "Newsletter Consent Checkbox": Check if there is a consent checkbox in the newsletter",
    "Newsletter functinality": Check if the functionality of the 4 Links in the Newsletter is correct",
    "Newsletter More Details": Check if the more Details Button is correct",
    """
}

# Function to get the templates
def get_templates():
    return session.get('templates', DEFAULT_TEMPLATES)  # This line should retrieve the default if not set

# Function to set new templates
def set_templates(new_templates):
    session['templates'] = new_templates

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        session['url'] = url  # Store the URL in session
        return redirect(url_for('templates'))  # Redirect to templates page
    return render_template('index.html')

@app.route('/templates', methods=['GET', 'POST'])
def templates():
    templates = get_templates()  # Retrieve templates from session
    if request.method == 'POST':
        new_templates = {
            'impressum': request.form['impressum'],
            'datenschutz': request.form['datenschutz'],
            'cookie_policy': request.form['cookie_policy'],
            'newsletter': request.form['newsletter']
        }
        set_templates(new_templates)  # Save updated templates
        return redirect(url_for('check_compliance'))
    return render_template('templates.html', templates=templates)

@app.route('/check_compliance')
def check_compliance():
    url = session.get('url')
    if not url:
        return redirect(url_for('index'))  # Redirect if no URL is set

    # Run the compliance check
    conformity, pdf_content, criteria_results = run_compliance_check(url)

    # Save the criteria results in the session for later access in the results page
    session['criteria_results'] = criteria_results  

    # Save the result to the database
    save_result(url, conformity, pdf_content)

    # Redirect to the results page
    return redirect(url_for('results'))

    
def run_compliance_check(url, template_text=None):
    try:
        # Initialize the results dictionaries
        criteria_results = {criterion: False for criterion in CRITERIA}  # Initialize results
        feedback_results = {criterion: "No feedback available." for criterion in CRITERIA}  # Initialize feedback
        
        # Use ThreadPoolExecutor for concurrent execution
        with ThreadPoolExecutor() as executor:
            future_to_criteria = {
                executor.submit(check_cookie_banner_with_playwright, url): "Cookie Banner Visibility",
                executor.submit(check_ohne_einwilligung_link, url): "Ohne Einwilligung Link",
                executor.submit(check_cookie_selection, url): "Cookie Selection",
                executor.submit(check_clear_cta, url): "Clear CTA",
                executor.submit(check_age_limitation, url): "Age Limitation",  
                executor.submit(check_newsletter_wording, url, template_text): "Newsletter wording"  # Add this line
            }

            # Process the results as the checks complete
            for future in as_completed(future_to_criteria):
                criterion_name = future_to_criteria[future]
                try:
                    result, feedback = future.result()  # Get result from the check
                    criteria_results[criterion_name] = result
                    feedback_results[criterion_name] = feedback  # Store feedback for each criterion
                except Exception as e:
                    print(f"Error while running {criterion_name}: {e}")
        
        # Determine conformity (compliance status)
        issues = [name for name, met in criteria_results.items() if not met]
        conformity = "Yes" if not issues else "No"

         # Get current date and time
        date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        
        # Generate the PDF
        pdf_content = generate_pdf(url, conformity, criteria_results, feedback_results, date_time)

        return conformity, pdf_content, criteria_results

    except Exception as e:
        print(f"Error during compliance check: {e}")
        pdf_content = generate_pdf(url, "No", {}, {}, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return "No", pdf_content, {}




# Automatic pop-up
def check_cookie_banner_with_playwright(url):
    """
    Checks if a visible cookie or consent banner is present on the given webpage,
    including checks for iframes and specific selectors.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Launch browser in headless mode

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
        )
        page = context.new_page()

        # Common selectors for cookie banners
        common_selectors = [
            'div.sticky',  # The main sticky container of the cookie banner
            'div.hp__sc-yx4ahb-7',  # The main container of the cookie banner
            'p.hp__sc-hk8z4-0',  # Paragraphs containing cookie consent text
            'button.hp__sc-9mw778-1',  # Buttons for actions
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
            'div[data-borlabs-cookie-consent-required]',  # Selector for Borlabs Cookie
            'div#BorlabsCookieBox',  # Specific ID for Borlabs Cookie Box
            'div#BorlabsCookieWidget',  # Specific ID for Borlabs Cookie Widget
            'div.elementText',  # Selector for the custom cookie banner text container
            'h3:has-text("Datenschutzhinweis")',  # Check for the header text
        ]

        def is_visible_cookie_banner(page_or_frame):
            """Check for visible cookie banners in the given page or frame."""
            found_banners = []  # Store found banners for debugging
            for selector in common_selectors:
                elements = page_or_frame.query_selector_all(selector)
                for element in elements:
                    if element and element.is_visible():
                        box = element.bounding_box()
                        if box and box['width'] > 300 and box['height'] > 50:  # Minimum dimensions for a banner
                            # Get the text content of the element
                            element_text = element.evaluate("el => el.textContent").lower() or ""
                            found_banners.append({
                                'selector': selector,
                                'text': element_text,
                                'bounding_box': box
                            })

            # Debugging output for detected banners
            for banner in found_banners:
                print(f"Found banner with selector: '{banner['selector']}'")
                print(f"Element text: '{banner['text']}'")
                print(f"Element bounding box: {banner['bounding_box']}")

            # Check for keywords in the page content
            for banner in found_banners:
                keywords = ["cookie", "consent", "gdpr", "privacy", "tracking", "preferences"]
                if any(keyword in banner['text'] for keyword in keywords):
                    return True

            return False

        def check_cookieconsent_options(page):
            """Check if cookie consent options are present in the page context."""
            try:
                # Check if window.cookieconsent_options exists
                cookie_consent = page.evaluate("window.cookieconsent_options !== undefined")
                if cookie_consent:
                    print("Cookie consent options found.")

                    return True, "Cookie consent options found."
            except Exception as e:
                print(f"Error checking cookie consent options: {e}")
                return False, f"Error checking cookie consent options: {e}"
            return False, "No cookie consent options found."

        def check_script_inclusions(page):
            """Check if the specific Borlabs Cookie scripts are included."""
            try:
                scripts = page.query_selector_all("script[type='module']")
                for script in scripts:
                    script_src = script.get_attribute('src')
                    if 'borlabs-cookie' in script_src:
                        print("Borlabs Cookie script found: ", script_src)
                        
                        return True, f"Borlabs Cookie script found: {script_src}"
            except Exception as e:
                print(f"Error checking for Borlabs Cookie scripts: {e}")
                return False, f"Error checking for Borlabs Cookie scripts: {e}"
            return False, "No Borlabs Cookie scripts found."


        try:
            # Attempt to load the page with retries
            for attempt in range(5):
                try:
                    print(f"Attempting to load the page (Attempt {attempt + 1})...")
                    page.goto(url, timeout=60000)  # Set timeout for page loading
                    page.wait_for_load_state('networkidle')  # Wait until the network is idle
                    print("Page loaded successfully.")
                    break
                except TimeoutError:
                    print(f"Attempt {attempt + 1} failed. Retrying after 5 seconds...")
                    page.wait_for_timeout(5000)  # Wait before retrying
            else:
                print("Page failed to load after multiple attempts.")
                
                return False, "Page failed to load after multiple attempts."


            # Allow extra time for dynamic content (like cookie banners)
            page.wait_for_timeout(30000)  # Increased timeout for dynamic content


            # Check the main document for cookie banners
            if is_visible_cookie_banner(page):
                print("Cookie banner found in the main document.")
                return True, "Cookie banner found."
            
            # Check for consent options or specific scripts
            cookieconsent_result, cookieconsent_feedback = check_cookieconsent_options(page)
            if cookieconsent_result:
                return cookieconsent_result, cookieconsent_feedback

            script_inclusion_result, script_inclusion_feedback = check_script_inclusions(page)
            if script_inclusion_result:
                return script_inclusion_result, script_inclusion_feedback

            # Check for cookie banner in iframes, specifically excluding the hidden ad iframe
            iframes = page.query_selector_all('iframe')
            for iframe in iframes:
                # Checking if the iframe is hidden or not
                iframe_src = iframe.get_attribute('src')
                if iframe_src and "doubleclick" not in iframe_src:
                    iframe_content = iframe.content_frame()
                    if iframe_content and is_visible_cookie_banner(iframe_content):
                        print("Cookie banner found in an iframe.")
                        return True, "Cookie banner found in an iframe."


            # Debugging output: log page content if no banners were found
            content = page.content().lower()
            print("Page content (for debugging):")
            print(content[:2000])  # Print first 2000 characters for debugging

            # Check for keywords in the page content
            keywords = ["cookie", "consent", "onetrust", "gdpr", "privacy", "banner", "tracking", "preferences"]
            exclude_keywords = ["recaptcha", "g-recaptcha", "captcha", "not a robot", "login", "signup"]

            if any(word in content for word in keywords) and not any(ex_kw in content for ex_kw in exclude_keywords):
                print("Cookie-related content found on the page, but no visible banner detected.")
                return False, "Cookie-related content found, but no visible banner detected."

            print("No visible cookie banner found.")
            return False, "No visible cookie banner found."

        except Exception as e:
            print(f"Error: {e}")
            return False, f"Error during cookie banner check: {e}"

        finally:
            page.close()  # Always close the page
            browser.close()  # Always close the browser
        
# Link "Ohne Einwilligung"
def check_ohne_einwilligung_link(url):
    """
    Checks if a cookie banner is present on the given webpage
    and whether the link or button "Ohne Einwilligung" or "Ohne Einwilligung fortfahren" can be clicked.
    """
    keywords = ["Ohne Einwilligung", "Ohne Einwilligung fortfahren"]  # Keywords for search
    selectors = [
        'button:has-text("Ohne Einwilligung")',
        'a:has-text("Ohne Einwilligung")',
        'button:has-text("Ohne Einwilligung fortfahren")',
        'a:has-text("Ohne Einwilligung fortfahren")'
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set to False for debugging
        page = browser.new_page()

        try:
            # Load the page and wait for the cookie banner
            page.goto(url, timeout=30000)  # Wait for the page to fully load
            print("Page loaded successfully.")

            # Use a single wait for the cookie banner to be present
            page.wait_for_selector('div[id^="onetrust-banner"], div[class*="cookie-banner"]', timeout=10000)
            print("Cookie banner loaded.")

            # Check for the presence of the 'Ohne Einwilligung' button/link
            for selector in selectors:
                element = page.query_selector(selector)
                if element and element.is_visible() and element.is_enabled():
                    location = element.evaluate("el => el.getBoundingClientRect()")  # Get the position of the element
                    feedback = (
                        f"'Ohne Einwilligung' link found and clickable. "
                        f"Location in cookie banner: top={location['top']}, left={location['left']}, "
                        f"width={location['width']}, height={location['height']}."
                    )
                    return True, feedback

            print("No clickable 'Ohne Einwilligung' link or button found.")
            return False, "No clickable 'Ohne Einwilligung' link or button found."

        except TimeoutError:
            print("Error: Timeout while loading the page.")
            return False, "Timed out while waiting for the 'Ohne Einwilligung fortfahren' button."
        except Exception as e:
            print(f"General error: {e}")
            return False, f"General error occurred: {e}"
          
        finally:
            browser.close()  # Ensure the browser is closed

# Check 4 Cookie Options and if they're preselected
def check_cookie_selection(url):
    """
    Check if the OneTrust cookie banner on the provided URL contains 
    the required four German cookie categories as toggle options, 
    and verifies that they are not preselected.
    """
    # Expected German cookie categories
    expected_options = [
        "Leistungs-Cookies", 
        "Funktionelle Cookies", 
        "Werbe-Cookies", 
        "Social-Media-Cookies"
    ]

    # Set up Selenium with ChromeDriver in headless mode
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
        # Execute the script to get options and their checked status
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



def check_clear_cta(url):

    # Ensure the URL starts with http or https; add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    criteria_met = False
    feedback = "CTA not found or not recognizable as a clear call-to-action."
    newsletter_phrases = ["subscribe now", "join our newsletter", "sign up", "get updates", "newsletter signup", "subscribe", "subscribe to our newsletter"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print(f"Checking URL: {url}")  # Debugging print

            page.goto(url)  # Page.goto expects a full URL (including http:// or https://)

            # Find CTA elements
            cta_elements = page.query_selector_all('a, button, input')
            for element in cta_elements:
                text = element.inner_text().strip()  # Extract the text of the element
                if any(phrase.lower() in text.lower() for phrase in newsletter_phrases):
                    criteria_met = True
                    feedback = f"Found CTA: '{text}'"
                    break

            if not criteria_met:
                feedback = "No CTA found matching the expected phrases."

        except Exception as e:
            feedback = f"Error navigating to URL {url}: {str(e)}"
            print(feedback)

        browser.close()

    return criteria_met, feedback



from playwright.sync_api import sync_playwright

def check_age_limitation(url):

    # Ensure the URL starts with http or https; add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # List of common phrases that indicate an age limitation (18+)
    age_restriction_phrases = [
        "You must be 18 or older",
        "18+",
        "You must be over 18",
        "Age verification",
        "Enter your birthdate",
        "Please confirm your age",
        "Restricted to users 18 and older",
        "DOB",
        "Date of Birth"
    ]
    
    # Default value for age limitation check (assume no age restriction)
    age_limitation_met = False
    feedback = "No age limitation found."

    try:
        # Fetch the HTML content of the page using Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            page_content = page.content()
            browser.close()

        # Parse the page content
        soup = BeautifulSoup(page_content, 'html.parser')

        # Search for age limitation-related phrases in text elements
        age_verification_elements = soup.find_all(string=True)
        for element in age_verification_elements:
            text = element.strip().lower()  # Convert to lowercase for easier matching
            for phrase in age_restriction_phrases:
                if phrase.lower() in text:
                    age_limitation_met = True
                    feedback = f"Age limitation found: '{text}'"
                    break
            if age_limitation_met:
                break  # No need to continue once an age limitation is found

    except Exception as e:
        print(f"Error loading the page: {e}")
        feedback = f"Error during age limitation check: {str(e)}"

    return age_limitation_met, feedback



def extract_brand_from_url(url):
    """Extract brand name from URL (e.g., 'loreal' from 'loreal.com')."""
    domain = urlparse(url).netloc  # Get domain name from URL (e.g., 'loreal.com')
    brand_name = domain.split('.')[0]  # Extract the first part of the domain (e.g., 'loreal')
    brand_name = brand_name.capitalize()  # Capitalize the brand name
    return brand_name

def check_newsletter_wording(url, template_text=None):
    """Check if the newsletter wording matches the expected template."""

    # Default mustertext to use if no template is provided
    default_mustertext = """By checking this box, I consent to the processing of my aforementioned contact details for marketing purposes by [Brand Name] and its affiliated companies. To receive information tailored to my interests, I also consent to the collection and storage of my interactions during marketing activities, as well as my use of [Brand Name]'s online services. Additionally, I agree that my email address or phone number (if provided) may be transmitted in encrypted form to third-party marketing partners, allowing relevant information to be displayed to me while using the online services of [Brand Name] and its partners."""

    if not template_text:
        template_text = default_mustertext

    # Ensure the URL starts with http or https; add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Extract brand name from the URL
    brand_name = extract_brand_from_url(url)

    # Replace [Brand Name] with the actual brand name in the mustertext
    template_text = template_text.replace("[Brand Name]", brand_name)

    try:
        # Using Playwright for a better solution to handle dynamic content
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # Set headless=False to see what's happening

            page = browser.new_page()

            # Increase the timeout for waiting for the page to load
            page.goto(url, timeout=60000, wait_until="domcontentloaded")  # 60 seconds timeout, waits until DOM is loaded

            # Wait for the newsletter button or a similar element to appear
            page.wait_for_selector('a[href*="newsletter"], a[href*="subscribe"], button, input[type="submit"]', timeout=60000)

            # Scrape all links from the homepage
            links = page.query_selector_all('a')  # Collect all links
            relevant_links = []

            # Look for any link that mentions 'newsletter', 'subscribe', 'join', etc.
            for link in links:
                href = link.get_attribute('href')
                if href and any(keyword in href.lower() for keyword in ["newsletter", "subscribe", "sign up", "join", "receive updates"]):
                    relevant_links.append(href)

            if not relevant_links:
                # If no links were found, we need to search within the page content
                print("No direct newsletter links found. Searching for newsletter-related content on the page...")

                # Search within the page content for keywords like 'newsletter', 'subscribe', etc.
                page_content = page.content()
                if any(keyword in page_content.lower() for keyword in ["newsletter", "subscribe", "sign up", "join", "receive updates"]):
                    relevant_links.append(url)  # Fallback to checking the homepage or starting page

            # Check the relevant pages for consent wording
            for relevant_link in relevant_links:
                # Make sure the link is complete (starts with http:// or https://)
                if not relevant_link.startswith(('http://', 'https://')):
                    relevant_link = url + relevant_link  # Ensure it's a full URL

                # Go to the found relevant link (newsletter or subscribe page)
                page.goto(relevant_link, wait_until="load")
                page_content = page.content()  # Get the full page content after rendering

                # Use BeautifulSoup to parse the page content
                soup = BeautifulSoup(page_content, 'html.parser')

                # Get all visible text from the page and convert it to lowercase for easier matching
                page_text = ' '.join([element.get_text() for element in soup.find_all(['p', 'span', 'label'])])  # Check relevant elements
                page_text = page_text.lower()  # Convert all text to lowercase for easier matching

                # Debugging: Print a snippet of the extracted text
                print(f"Extracted text from page: {page_text[:1000]}...")  # Print first 1000 chars

                # Define consent-related keywords and phrases
                consent_keywords = [
                    r"\bconsent\b",
                    r"\bagree\b",
                    r"\baccept\b",
                    r"\bgive permission\b",
                    r"\bcheck this box\b",
                    r"\bsubscribe\b",
                    r"\bmarketing\b",
                    r"\bprocessing\b",
                    r"\bprivacy policy\b",  # Added privacy related terms to capture more cases
                    r"\bterms and conditions\b"
                ]

                # Check if any of the consent keywords are in the extracted text
                if any(re.search(keyword, page_text) for keyword in consent_keywords):
                    browser.close()
                    return True, f"Newsletter wording matches the template on {relevant_link}."

            # If no consent-related text is found
            browser.close()
            return False, "Newsletter wording does not match the expected template or cannot find a relevant page."

    except Exception as e:
        browser.close()
        return False, f"Error during check: {e}"



def check_consent_checkbox(url):

     # Ensure the URL starts with http or https; add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    consent_phrases = [
        "I agree to the terms and conditions",
        "I consent to the use of my data",
        "I accept the privacy policy",
        "I am over 18 years old"
    ]

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        checkboxes = soup.find_all('input', {'type': 'checkbox'})
        for checkbox in checkboxes:
            label = checkbox.find_next('label')
            if label and any(phrase.lower() in label.get_text().lower() for phrase in consent_phrases):
                return True, "Consent checkbox found with appropriate consent wording."
        
        return False, "Consent checkbox with proper wording not found."
    except Exception as e:
        return False, f"Error during check: {e}"


"""

def check_newsletter_functionality(soup):
    # Check the functinality of all 4 links and if they have the correct text
    # Widerrufsrecht, Impressumslink, Datenschutzinformationen, Werbepartner

def check_newsletter_more_details (soup):
    # Check if there's a plus for more details on data privacy policy information
    #whole text is correct and link to the advertising partners

"""

def generate_pdf(url, conformity, criteria_results, feedback_results,date_time):
    html_content = f'''
    <h1>Compliance Report</h1>
    <p><strong>Date and Time:</strong> {date_time}</p>
    <p><strong>URL:</strong> {url}</p>
    <p><strong>Conformity:</strong> {conformity}</p>
    <h2>Criteria Results</h2>
    <table border="1" style="width: 100%; border-collapse: collapse;">
        <tr>
            <th style="padding: 10px;">Criterion</th>
            <th style="padding: 10px;">Status</th>
            <th style="padding: 10px;">Feedback</th>
        </tr>
    '''
    
    # Iterate over the criteria_results and feedback_results to generate rows for the PDF table
    for criterion in criteria_results.keys():
        met = criteria_results.get(criterion, False)  # Get the status safely
        status = "✔️" if met else "❌"  # Use checkmark for True, cross for False
        feedback = feedback_results.get(criterion, "No feedback available.")  # Get feedback, default if not available
        
        html_content += f'''
        <tr>
            <td style="padding: 10px;">{criterion}</td>
            <td style="padding: 10px;">{status}</td>
            <td style="padding: 10px;">{feedback}</td>
        </tr>
        '''
    
    html_content += '''
    </table>
    '''
    
    # Create a BytesIO buffer to hold the PDF
    pdf_buffer = io.BytesIO()
    
    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer)
    
    # Check for errors during PDF generation
    if pisa_status.err:
        print("Error generating PDF")
        return None

    # Return the PDF content as bytes
    pdf_buffer.seek(0)  # Reset buffer position to the beginning
    return pdf_buffer.read()


def save_result(url, conformity, pdf_content):
    try:
        conn = sqlite3.connect('compliance.db')
        cursor = conn.cursor()
        
        # Create the table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATETIME DEFAULT (datetime('now', 'localtime')),
                url TEXT NOT NULL,
                conformity TEXT NOT NULL,
                conformity_details BLOB NOT NULL
            )
        ''')  # Ensure the PDF content can be stored as a BLOB
        
        # Insert the new result into the database
        cursor.execute('''
            INSERT INTO compliance (url, conformity, conformity_details)
            VALUES (?, ?, ?)
        ''', (url, conformity, pdf_content))
        
        conn.commit()  # Commit the transaction
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")  # Log the error for debugging
    finally:
        conn.close()  # Ensure the database connection is closed

@app.route('/results')
def results():
    conn = sqlite3.connect('compliance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, date, url, conformity FROM compliance ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        result = {
            'id': row[0],
            'date':row[1],
            'url': row[2],
            'conformity': row[3],
        }
    else:
        result = {}

    return render_template('results.html', result=result)

@app.route('/download/<int:id>')
def download(id):
    conn = sqlite3.connect('compliance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT conformity_details FROM compliance WHERE id = ?', (id,))
    pdf_content = cursor.fetchone()
    
    # Check if pdf_content is retrieved
    if pdf_content is None:
        return "No PDF found.", 404  # Handle the case where no PDF exists for the ID
    
    pdf_content = pdf_content[0]  # Get the actual bytes from the tuple
    conn.close()

    return send_file(
        io.BytesIO(pdf_content),
        download_name='compliance_report.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

def execute_query(query, params=()):
    conn = sqlite3.connect('compliance.db') 
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

@app.route('/database', methods=['GET'])
def database():
    page = request.args.get('page', 1, type=int)
    selected_url = request.args.get('url', 'all', type=str)
    per_page = 10
    offset = (page - 1) * per_page
    
    # Kunden-URLs abrufen für das Dropdown
    customers_query = "SELECT DISTINCT url FROM compliance"
    customers = execute_query(customers_query)

    if selected_url == 'all':
        query = "SELECT * FROM compliance ORDER BY id DESC LIMIT ? OFFSET ?"
        params = (per_page, offset)
    else:
        query = "SELECT * FROM compliance WHERE url = ? ORDER BY id DESC LIMIT ? OFFSET ?"
        params = (selected_url, per_page, offset)

    compliance = execute_query(query, params)

    total_records_query = "SELECT COUNT(*) FROM compliance"
    total_records = execute_query(total_records_query)[0][0]

    total_pages = (total_records + per_page - 1) // per_page

    return render_template('database.html', records=compliance, page=page, total_pages=total_pages, customers=customers, selected_url=selected_url)

if __name__ == '__main__':
    app.run(debug=True)
